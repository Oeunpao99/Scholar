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


@pytest.mark.asyncio
async def test_student_changes_are_audited(api):
    client, headers = api
    await client.post("/api/v1/students", headers=headers, json=STUDENT)
    logs = (await client.get("/api/v1/audit", headers=headers)).json()["items"]
    assert any(i["entity_type"] == "student" and i["action"] == "create" for i in logs)
