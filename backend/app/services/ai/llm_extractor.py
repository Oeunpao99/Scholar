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
    ) -> ExtractedReport:
        if not self.configured:
            raise AppError(
                "No LLM endpoint is configured (AI_LLM_BASE_URL / AI_LLM_API_KEY).",
                status_code=503,
                code="llm_not_configured",
            )

        payload = self._request(text, ocr_text)
        parsed = self._parse(payload)
        parsed.current_year = parsed.current_year or current_year
        if parsed.date is None:
            parsed.date = default_date
        return parsed

    def _request(self, text: str, ocr_text: str | None) -> str:
        content = f"<ocr_text>\n{ocr_text}\n</ocr_text>\n<message>\n{text}\n</message>"
        body = {
            "model": settings.AI_LLM_MODEL,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
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
