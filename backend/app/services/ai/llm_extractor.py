"""
Optional LLM-assisted extraction.

Works with any OpenAI-compatible chat-completions endpoint.  The prompt is
strictly schema-bound and the response is validated with Pydantic, so a
hallucinated value fails loudly instead of silently corrupting a report.
The built-in parser remains the fallback whenever no endpoint is configured.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date

import httpx
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.errors import AppError
from app.schemas.ai import ExtractedReport

logger = logging.getLogger("scholar.ai.llm")

SYSTEM_PROMPT = """You convert daily student enrollment messages (Khmer or English) into JSON.

Return ONLY a JSON object, no markdown, with this exact shape:
{
  "date": "YYYY-MM-DD" or null,
  "categories": [
    {
      "category": "current_year" | "before_current_year" | "other_province",
      "grades": [
        {"grade": "A"|"B"|"C"|"D"|"E", "total": int, "female": int, "pp": int, "kp": int}
      ],
      "total": int, "female": int, "pp": int, "kp": int
    }
  ],
  "warnings": ["..."]
}

Rules:
- category codes: "បានទទួលពាក្យបាក់ឌុបឆ្នាំ..." -> current_year,
  "...មុនឆ្នាំ..." -> before_current_year, "...ខេត្តផ្សេង" -> other_province.
- Grade lines are TODAY'S GAIN. The "សរុបរួមចំនួន" line is CUMULATIVE; do not
  use it as a grade value.
- Keep female/PP/KP as 0 when the text does not state them.
- Never invent numbers that are not present in the message.
"""


STUDENT_SYSTEM_PROMPT = """You extract student scholarship application form fields from Cambodian documents (Khmer/English).

Return ONLY a JSON object with this exact shape:
{
  "full_name": string or null,
  "gender": "M" or "F" or null,
  "grade": "A" | "B" | "C" | "D" | "E" | null,
  "score_rank": int or null,
  "high_school": string or null,
  "stream": "science" | "social_science" | null,
  "university": string or null,
  "major": string or null,
  "phone": string or null,
  "warnings": ["..."]
}

Rules:
- For gender: "ប្រុស" / male -> "M", "ស្រី" / female -> "F".
- For grade: The printed grade letter (A, B, C, D, or E).
- For stream: "វិទ្យាសាស្ត្រ" / "វិទ្យាសាស្ត្រពិត" -> "science", "វិទ្យាសាស្ត្រសង្គម" / "សង្គម" -> "social_science".
- For score_rank: A positive integer rank/order if present.
- Never invent or hallucinate data that is not present in the document.
"""


class LlmExtractor:
    """OpenAI-compatible chat-completions client."""

    name = "llm"

    @property
    def configured(self) -> bool:
        return bool(settings.AI_LLM_BASE_URL and settings.AI_LLM_API_KEY)

    def extract(
        self,
        text: str,
        *,
        default_date: date | None = None,
        current_year: int | None = None,
        ocr_text: str | None = None,
        images: list[str] | None = None,
    ) -> ExtractedReport:
        if not self.configured:
            raise AppError(
                "No LLM endpoint is configured (AI_LLM_BASE_URL / AI_LLM_API_KEY).",
                status_code=503,
                code="llm_not_configured",
            )

        payload = self._request(text, ocr_text, images=images)
        parsed = self._parse(payload)
        parsed.current_year = parsed.current_year or current_year
        if parsed.date is None:
            parsed.date = default_date
        return parsed

    def extract_student(
        self,
        text: str,
        *,
        images: list[str] | None = None,
    ) -> dict[str, object]:
        if not self.configured:
            return {}

        raw_json = self._request(
            text,
            ocr_text=text,
            images=images,
            system_prompt=STUDENT_SYSTEM_PROMPT,
        )
        try:
            return safe_json_loads(raw_json)
        except Exception as exc:
            logger.warning("Failed to parse student LLM JSON: %s", exc)
            return {}

    def _request(
        self,
        text: str,
        ocr_text: str | None,
        *,
        images: list[str] | None = None,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> str:
        content = f"<ocr_text>\n{ocr_text}\n</ocr_text>\n<message>\n{text}\n</message>"
        user_content: str | list[dict[str, object]]
        if images:
            user_content = [{"type": "text", "text": content}]
            for img in images[:4]:
                url = img if img.startswith("data:") else f"data:image/jpeg;base64,{img}"
                user_content.append({"type": "image_url", "image_url": {"url": url}})
        else:
            user_content = content

        body = {
            "model": settings.AI_LLM_MODEL,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {settings.AI_LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        base = str(settings.AI_LLM_BASE_URL).rstrip("/")
        with httpx.Client(timeout=settings.AI_LLM_TIMEOUT_SECONDS) as client:
            response = client.post(f"{base}/chat/completions", json=body, headers=headers)
        if response.status_code >= 400:
            logger.warning("LLM request failed: HTTP %s %s", response.status_code, response.text[:400])
            raise AppError(
                f"The AI provider returned HTTP {response.status_code}.",
                status_code=502,
                code="llm_error",
            )
        return response.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _parse(raw: str) -> ExtractedReport:
        try:
            return ExtractedReport.model_validate_json(raw)
        except PydanticValidationError as exc:
            logger.warning("LLM returned an invalid payload: %s", exc)
            raise AppError(
                "The AI provider returned a response that does not match the expected schema.",
                status_code=502,
                code="llm_invalid_response",
            ) from exc
        except (KeyError, IndexError, TypeError) as exc:
            raise AppError("Unexpected response from the AI provider.", status_code=502) from exc


def strip_code_fence(raw: str) -> str:
    """Remove ```json fences some models still emit."""
    return re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()


def safe_json_loads(raw: str) -> dict:
    return json.loads(strip_code_fence(raw))
