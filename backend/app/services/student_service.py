"""Student list service."""

from __future__ import annotations

import base64
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.errors import NotFoundError, ValidationError
from app.db.base import utcnow
from app.models.enums import AuditAction
from app.models.student import Student, StudentPhoto
from app.models.user import User
from app.repositories.student_repo import StudentRepository
from app.schemas.common import Page, PageMeta
from app.schemas.student import StudentCreate, StudentExtraction, StudentRead, StudentUpdate
from app.services.ai.documents import load_document
from app.services.ai.ocr import OcrService
from app.services.ai.photo import extract_student_photo, normalize_uploaded_photo
from app.services.ai.student_extractor import extract_student_fields
from app.services.audit_service import AuditService
from app.services.settings_service import SettingsService


class StudentService:
    def __init__(self, session: AsyncSession, actor: User | None = None) -> None:
        self.session = session
        self.actor = actor
        self.repo = StudentRepository(session)
        self.audit = AuditService(session)
        self.settings = SettingsService(session)

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 50,
        academic_year: int | None = None,
        q: str | None = None,
        gender: str | None = None,
        grade: str | None = None,
        stream: str | None = None,
    ) -> Page[Student]:
        items, total = await self.repo.search(
            academic_year=academic_year,
            q=q,
            gender=gender,
            grade=grade,
            stream=stream,
            limit=size,
            offset=(page - 1) * size,
        )
        return Page(
            items=items,
            meta=PageMeta(
                page=page,
                size=size,
                total=total,
                total_pages=(total + size - 1) // size,
                has_next=page * size < total,
                has_prev=page > 1,
            ),
        )

    async def extract_from_file(self, data: bytes, filename: str | None = None) -> StudentExtraction:
        """OCR an application form and read the student fields out of it."""
        ocr = OcrService()
        if not ocr.available:
            raise ValidationError(
                "OCR is not available on this server (install tesseract with the Khmer language pack)."
            )
        # Tesseract and PDF rendering are CPU-bound; keep them off the event loop.
        document = await run_in_threadpool(load_document, data)
        text = await run_in_threadpool(ocr.extract_text_from_images, document.text_pages)
        photo = await run_in_threadpool(extract_student_photo, document.photo_pages)
        fields = extract_student_fields(text, filename=filename)
        if not fields.values.get("grade") and document.text_pages:
            try:
                from app.services.ai.form_template import read_grade_box

                box_grade = await run_in_threadpool(read_grade_box, document.text_pages[0])
                if box_grade:
                    fields.values["grade"] = box_grade
                    fields.warnings = [w for w in fields.warnings if "និទ្ទេស" not in w]
            except Exception:
                pass

        # Multimodal Vision AI Enhancement: if LLM endpoint is configured, send page images
        from app.services.ai.llm_extractor import LlmExtractor

        llm = LlmExtractor()
        if llm.configured and document.text_pages:
            try:
                import io

                images = []
                for page in document.text_pages[:2]:
                    buf = io.BytesIO()
                    page.convert("RGB").save(buf, format="JPEG", quality=85)
                    images.append(base64.b64encode(buf.getvalue()).decode())

                llm_values = await run_in_threadpool(llm.extract_student, text, images=images)
                for k in ("full_name", "gender", "grade", "score_rank", "high_school", "stream", "university", "major", "phone"):
                    v = llm_values.get(k)
                    if v:
                        # Prefer LLM value if fields.values was empty or for fields commonly handwritten
                        if k not in fields.values or fields.values[k] in ("", None) or k in ("high_school", "university", "major", "phone"):
                            fields.values[k] = v
                if llm_values.get("stream"):
                    fields.warnings = [w for w in fields.warnings if "ថ្នាក់" not in w]
                if llm_values.get("gender"):
                    fields.warnings = [w for w in fields.warnings if "ភេទ" not in w]
                if llm_values.get("grade"):
                    fields.warnings = [w for w in fields.warnings if "និទ្ទេស" not in w]
            except Exception as exc:
                import logging
                logging.getLogger("scholar.ai").warning("Multimodal LLM student extraction failed: %s", exc)

        if not text.strip():
            fields.warnings.append("រកមិនឃើញអក្សរក្នុងឯកសារនេះទេ — សូមប្រើរូបភាពច្បាស់ជាងនេះ")
        if photo is None:
            fields.warnings.append("រកមិនឃើញរូបថតសិស្សក្នុងឯកសារ — អាចបញ្ចូលរូបដោយដៃបាន")
        return StudentExtraction(
            values=fields.values,
            found=fields.found,
            missing=fields.missing,
            warnings=fields.warnings,
            ocr_text=text,
            pages=document.page_count,
            photo=f"data:image/jpeg;base64,{base64.b64encode(photo).decode()}" if photo else None,
        )

    # --------------------------------------------------------------- reading
    async def to_read(self, students: list[Student]) -> list[StudentRead]:
        versions = await self.repo.photo_versions([s.id for s in students])
        return [
            StudentRead.model_validate(s).model_copy(
                update={
                    "has_photo": s.id in versions,
                    "photo_version": versions[s.id].isoformat() if s.id in versions else None,
                }
            )
            for s in students
        ]

    async def read(self, student: Student) -> StudentRead:
        return (await self.to_read([student]))[0]

    # --------------------------------------------------------------- photos
    async def get_photo(self, student_id: UUID) -> StudentPhoto:
        photo = await self.repo.get_photo(student_id, with_data=True)
        if photo is None:
            raise NotFoundError("This student has no photo.")
        return photo

    async def set_photo(self, student_id: UUID, data: bytes) -> Student:
        student = await self.get(student_id)
        jpeg = await run_in_threadpool(normalize_uploaded_photo, data)
        photo = await self.repo.get_photo(student_id)
        if photo is None:
            self.session.add(StudentPhoto(student_id=student_id, content_type="image/jpeg", data=jpeg))
        else:
            photo.data = jpeg
            photo.content_type = "image/jpeg"
            photo.updated_at = utcnow()
        await self.session.flush()
        await self.audit.log(
            action=AuditAction.UPDATE,
            entity_type="student",
            entity_id=student.id,
            summary=f"Updated photo of {student.full_name}",
            user=self.actor,
        )
        await self.session.commit()
        return student

    async def delete_photo(self, student_id: UUID) -> Student:
        student = await self.get(student_id)
        photo = await self.repo.get_photo(student_id)
        if photo is not None:
            await self.session.delete(photo)
            await self.session.flush()
            await self.audit.log(
                action=AuditAction.UPDATE,
                entity_type="student",
                entity_id=student.id,
                summary=f"Removed photo of {student.full_name}",
                user=self.actor,
            )
            await self.session.commit()
        return student

    async def get(self, student_id: UUID) -> Student:
        student = await self.repo.get(student_id)
        if student is None:
            raise NotFoundError("Student not found.")
        return student

    async def create(self, payload: StudentCreate) -> Student:
        data = payload.model_dump()
        if data.get("academic_year") is None:
            data["academic_year"] = await self.settings.get_current_year()
        student = Student(**data, created_by=self.actor.id if self.actor else None)
        self.repo.add(student)
        await self.session.flush()
        await self.audit.log(
            action=AuditAction.CREATE,
            entity_type="student",
            entity_id=student.id,
            summary=f"Added student {student.full_name}",
            user=self.actor,
        )
        await self.session.commit()
        return student

    async def update(self, student_id: UUID, payload: StudentUpdate) -> Student:
        student = await self.get(student_id)
        data = payload.model_dump(exclude_unset=True)
        # Required columns can't be cleared.
        for key in ("full_name", "gender", "academic_year"):
            if key in data and data[key] is None:
                data.pop(key)
        before = student.to_dict()
        for key, value in data.items():
            setattr(student, key, value)
        await self.session.flush()
        await self.audit.diff_log(
            entity_type="student",
            entity_id=student.id,
            before={k: before.get(k) for k in data},
            after=data,
            user=self.actor,
        )
        await self.session.commit()
        return student

    async def delete(self, student_id: UUID) -> None:
        student = await self.get(student_id)
        name = student.full_name
        await self.session.delete(student)
        await self.session.flush()
        await self.audit.log(
            action=AuditAction.DELETE,
            entity_type="student",
            entity_id=student_id,
            summary=f"Deleted student {name}",
            user=self.actor,
        )
        await self.session.commit()
