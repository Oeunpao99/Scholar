"""Student list API."""

from __future__ import annotations

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def api(client, seeded):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"login": "admin@test.example.com", "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text
    return client, {"Authorization": f"Bearer {resp.json()['access_token']}"}


STUDENT = {
    "full_name": "សុខ ដារ៉ា",
    "gender": "F",
    "grade": "b",
    "score_rank": 152,
    "high_school": "វិទ្យាល័យព្រះស៊ីសុវត្ថិ",
    "stream": "science",
    "university": "សាកលវិទ្យាល័យភូមិន្ទភ្នំពេញ",
    "major": "វិទ្យាសាស្ត្រកុំព្យូទ័រ",
    "phone": "012 345 678",
    "note": "",
}


@pytest.mark.asyncio
async def test_add_student_defaults_to_current_year_and_normalises_input(api):
    client, headers = api
    resp = await client.post("/api/v1/students", headers=headers, json=STUDENT)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["academic_year"] == 2026
    assert body["grade"] == "B"  # upper-cased
    assert body["note"] is None  # blank stored as NULL
    assert body["stream"] == "science"


@pytest.mark.asyncio
async def test_list_is_in_entry_order_and_filters(api):
    client, headers = api
    await client.post("/api/v1/students", headers=headers, json=STUDENT)
    await client.post(
        "/api/v1/students",
        headers=headers,
        json={"full_name": "ចាន់ វុទ្ធី", "gender": "M", "grade": "A", "stream": "social_science"},
    )

    all_rows = (await client.get("/api/v1/students?academic_year=2026", headers=headers)).json()
    assert all_rows["meta"]["total"] == 2
    assert [s["full_name"] for s in all_rows["items"]] == ["សុខ ដារ៉ា", "ចាន់ វុទ្ធី"]

    males = (await client.get("/api/v1/students?gender=M", headers=headers)).json()
    assert [s["full_name"] for s in males["items"]] == ["ចាន់ វុទ្ធី"]

    grade_b = (await client.get("/api/v1/students?grade=B", headers=headers)).json()
    assert grade_b["meta"]["total"] == 1

    found = (await client.get("/api/v1/students?q=345", headers=headers)).json()
    assert [s["full_name"] for s in found["items"]] == ["សុខ ដារ៉ា"]

    other_year = (await client.get("/api/v1/students?academic_year=2025", headers=headers)).json()
    assert other_year["meta"]["total"] == 0


@pytest.mark.asyncio
async def test_update_and_delete_student(api):
    client, headers = api
    created = (await client.post("/api/v1/students", headers=headers, json=STUDENT)).json()

    resp = await client.patch(
        f"/api/v1/students/{created['id']}",
        headers=headers,
        json={"major": "គណិតវិទ្យា", "phone": ""},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["major"] == "គណិតវិទ្យា"
    assert resp.json()["phone"] is None
    assert resp.json()["full_name"] == "សុខ ដារ៉ា"

    resp = await client.delete(f"/api/v1/students/{created['id']}", headers=headers)
    assert resp.status_code == 200
    resp = await client.get(f"/api/v1/students/{created['id']}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_student_is_rejected(api):
    client, headers = api
    for bad in (
        {**STUDENT, "full_name": "  "},
        {**STUDENT, "gender": "X"},
        {**STUDENT, "grade": "F"},
        {**STUDENT, "stream": "arts"},
        {**STUDENT, "score_rank": 0},
    ):
        resp = await client.post("/api/v1/students", headers=headers, json=bad)
        assert resp.status_code == 422, (bad, resp.text)


# ------------------------------------------------------------ upload / OCR
FORM_TEXT = "គោត្តនាម-នាម៖ សុខ ដារ៉ា\nភេទ៖ ស្រី\nនិទ្ទេស៖ B\nលេខទូរស័ព្ទ៖ ០១២ ៣៤៥ ៦៧៨"


@pytest.fixture
def fake_ocr(monkeypatch):
    """Tesseract isn't installed everywhere tests run; stand in for it."""
    from app.services.ai.ocr import OcrService

    seen: list[int] = []

    def _extract(self, images):
        seen.append(len(images))
        return FORM_TEXT

    monkeypatch.setattr(OcrService, "available", property(lambda self: True))
    monkeypatch.setattr(OcrService, "extract_text_from_images", _extract)
    return seen


def _png() -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (60, 40), "white").save(buf, format="PNG")
    return buf.getvalue()


def _pdf(pages: int) -> bytes:
    import io

    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument.new()
    for _ in range(pages):
        pdf.new_page(595, 842)
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_extract_reads_fields_from_an_image_without_saving(api, fake_ocr):
    client, headers = api
    resp = await client.post(
        "/api/v1/students/extract", headers=headers,
        files={"file": ("form.png", _png(), "image/png")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["values"] == {
        "full_name": "សុខ ដារ៉ា", "gender": "F", "grade": "B", "phone": "012 345 678",
    }
    assert "major" in body["missing"]
    assert body["ocr_text"] == FORM_TEXT
    assert body["pages"] == 1
    listed = (await client.get("/api/v1/students", headers=headers)).json()
    assert listed["meta"]["total"] == 0  # review first; nothing saved


@pytest.mark.asyncio
async def test_extract_renders_pdf_pages_up_to_the_limit(api, fake_ocr):
    client, headers = api
    resp = await client.post(
        "/api/v1/students/extract", headers=headers,
        files={"file": ("scan.pdf", _pdf(5), "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["pages"] == 5
    assert fake_ocr == [2]


@pytest.mark.asyncio
async def test_extract_rejects_files_that_are_not_images_or_pdfs(api, fake_ocr):
    client, headers = api
    for name, data in (("notes.txt", b"hello"), ("empty.png", b""), ("fake.pdf", b"%PDF-broken")):
        resp = await client.post(
            "/api/v1/students/extract", headers=headers,
            files={"file": (name, data, "application/octet-stream")},
        )
        assert resp.status_code == 422, (name, resp.text)
    assert fake_ocr == []


@pytest.mark.asyncio
async def test_extract_reports_when_ocr_is_unavailable(api, monkeypatch):
    from app.services.ai.ocr import OcrService

    monkeypatch.setattr(OcrService, "available", property(lambda self: False))
    client, headers = api
    resp = await client.post(
        "/api/v1/students/extract", headers=headers,
        files={"file": ("form.png", _png(), "image/png")},
    )
    assert resp.status_code == 422
    assert "OCR" in resp.text


@pytest.mark.asyncio
async def test_extract_returns_the_cropped_photo(api, fake_ocr, monkeypatch):
    import app.services.student_service as svc

    monkeypatch.setattr(svc, "extract_student_photo", lambda pages: b"\xff\xd8\xff-fake-jpeg")
    client, headers = api
    resp = await client.post(
        "/api/v1/students/extract", headers=headers,
        files={"file": ("form.png", _png(), "image/png")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["photo"].startswith("data:image/jpeg;base64,")


# ------------------------------------------------------------------ photos
@pytest.mark.asyncio
async def test_photo_upload_view_replace_and_remove(api):
    client, headers = api
    sid = (await client.post("/api/v1/students", headers=headers, json=STUDENT)).json()["id"]
    assert (await client.get(f"/api/v1/students/{sid}/photo", headers=headers)).status_code == 404

    resp = await client.put(
        f"/api/v1/students/{sid}/photo", headers=headers,
        files={"file": ("me.png", _png(), "image/png")},
    )
    assert resp.status_code == 200, resp.text
    first_version = resp.json()["photo_version"]
    assert resp.json()["has_photo"] is True and first_version

    img = await client.get(f"/api/v1/students/{sid}/photo", headers=headers)
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/jpeg"
    assert img.content[:3] == b"\xff\xd8\xff"
    assert "private" in img.headers["cache-control"]

    listed = (await client.get("/api/v1/students", headers=headers)).json()["items"]
    assert listed[0]["has_photo"] is True and listed[0]["photo_version"] == first_version

    replaced = await client.put(
        f"/api/v1/students/{sid}/photo", headers=headers,
        files={"file": ("me2.png", _png(), "image/png")},
    )
    assert replaced.json()["photo_version"] != first_version  # busts client caches

    removed = await client.delete(f"/api/v1/students/{sid}/photo", headers=headers)
    assert removed.json()["has_photo"] is False
    assert (await client.get(f"/api/v1/students/{sid}/photo", headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_photo_rejects_non_images_and_needs_auth(api):
    client, headers = api
    sid = (await client.post("/api/v1/students", headers=headers, json=STUDENT)).json()["id"]
    bad = await client.put(
        f"/api/v1/students/{sid}/photo", headers=headers,
        files={"file": ("x.txt", b"hello", "text/plain")},
    )
    assert bad.status_code == 422
    assert (await client.get(f"/api/v1/students/{sid}/photo")).status_code == 401


@pytest.mark.asyncio
async def test_deleting_a_student_removes_the_photo(api, session):
    from sqlalchemy import func, select

    from app.models import StudentPhoto

    client, headers = api
    sid = (await client.post("/api/v1/students", headers=headers, json=STUDENT)).json()["id"]
    await client.put(
        f"/api/v1/students/{sid}/photo", headers=headers,
        files={"file": ("me.png", _png(), "image/png")},
    )
    await client.delete(f"/api/v1/students/{sid}", headers=headers)
    count = (await session.execute(select(func.count()).select_from(StudentPhoto))).scalar_one()
    assert count == 0


@pytest.mark.asyncio
async def test_student_changes_are_audited(api):
    client, headers = api
    await client.post("/api/v1/students", headers=headers, json=STUDENT)
    logs = (await client.get("/api/v1/audit", headers=headers)).json()["items"]
    assert any(i["entity_type"] == "student" and i["action"] == "create" for i in logs)


@pytest.mark.asyncio
async def test_export_students_endpoint(api):
    client, headers = api
    await client.post("/api/v1/students", headers=headers, json=STUDENT)

    # Word export
    resp_word = await client.get("/api/v1/students/export?format=word", headers=headers)
    assert resp_word.status_code == 200
    assert "wordprocessingml" in resp_word.headers["content-type"]
    assert resp_word.content[:4] == b"PK\x03\x04"

    # Excel export
    resp_excel = await client.get("/api/v1/students/export?format=excel", headers=headers)
    assert resp_excel.status_code == 200
    assert "spreadsheetml" in resp_excel.headers["content-type"]
    assert resp_excel.content[:4] == b"PK\x03\x04"

    # PDF export
    resp_pdf = await client.get("/api/v1/students/export?format=pdf", headers=headers)
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert resp_pdf.content[:4] == b"%PDF"
