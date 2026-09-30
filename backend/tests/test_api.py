"""End-to-end API tests against a real PostgreSQL database.

These exercise the paths a real user takes: log in, read reference data, create
a daily report, read it back with its derived cumulative figures, edit it, and
confirm the cumulative numbers moved correctly.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
import pytest_asyncio

D1 = date(2026, 9, 28)
D2 = date(2026, 9, 29)


def make_report(day: date, total: int, female: int, pp: int, kp: int, grades: dict) -> dict:
    return {
        "date": day.isoformat(),
        "category_code": "current_year",
        "today_total": total,
        "today_female": female,
        "today_pp": pp,
        "today_kp": kp,
        "note": None,
        "source": "manual",
        "grades": [
            {
                "grade": code,
                "today_total": values[0],
                "today_female": values[1],
                "today_pp": values[2],
                "today_kp": values[3],
            }
            for code, values in grades.items()
        ],
    }


@pytest_asyncio.fixture
async def api(client, seeded):
    """A client plus the ids the tests need."""
    resp = await client.get("/api/v1/references/categories", headers=await _auth(client))
    assert resp.status_code == 200, resp.text
    categories = resp.json()["items"]
    return {"categories": {c["code"]: c for c in categories}, "client": client}


async def _auth(client) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"login": "admin@test.example.com", "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# --------------------------------------------------------------------- auth
@pytest.mark.asyncio
async def test_login_returns_a_usable_token(client, seeded):
    headers = await _auth(client)
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "admin@test.example.com"
    assert me.json()["role"] == "superadmin"


@pytest.mark.asyncio
async def test_login_rejects_a_wrong_password(client, seeded):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"login": "admin@test.example.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_routes_require_a_token(client, seeded):
    assert (await client.get("/api/v1/reports/daily")).status_code == 401
    assert (await client.get("/api/v1/reports/daily", headers={"Authorization": "Bearer x"})).status_code == 401


# ---------------------------------------------------------------- reference
@pytest.mark.asyncio
async def test_reference_data_is_seeded(api):
    categories = api["categories"]
    assert [c["code"] for c in api["categories"].values()] == [
        "current_year",
        "before_current_year",
        "other_province",
    ]
    assert [c["position"] for c in categories.values()] == [1, 2, 3]
    assert categories["current_year"]["roman_numeral"] == "I."
    assert "2026" in categories["current_year"]["title"]


@pytest.mark.asyncio
async def test_grades_are_seeded_in_order(api):
    resp = await api["client"].get(
        "/api/v1/references/grades", headers=await _auth(api["client"])
    )
    assert resp.status_code == 200
    codes = [g["code"] for g in resp.json()["items"]]
    assert codes == ["A", "B", "C", "D", "E"]


# ------------------------------------------------------------------ reports
@pytest.mark.asyncio
async def test_create_read_update_delete_lifecycle(api):
    client = api["client"]
    headers = await _auth(client)

    created = await client.post(
        "/api/v1/reports/daily",
        headers=headers,
        json=make_report(D1, 10, 4, 3, 2, {"A": (6, 2, 2, 1), "D": (4, 2, 1, 1)}),
    )
    assert created.status_code == 201, created.text
    report_id = created.json()["id"]
    assert created.json()["today_total"] == 10
    assert created.json()["cumulative"]["total"] == 10

    # A second day accumulates on top of the first.
    second = await client.post(
        "/api/v1/reports/daily",
        headers=headers,
        json=make_report(D2, 5, 1, 1, 1, {"B": (5, 1, 1, 1)}),
    )
    assert second.status_code == 201, second.text
    assert second.json()["cumulative"]["total"] == 15
    assert second.json()["cumulative"]["female"] == 5
    assert second.json()["cumulative"]["pp"] == 4
    assert second.json()["cumulative"]["kp"] == 3

    fetched = await client.get(f"/api/v1/reports/daily/{second.json()['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["cumulative"]["total"] == 15

    # Editing day 2 must move the cumulative for day 2, and day 1 must not change.
    edited = await client.patch(
        f"/api/v1/reports/daily/{second.json()['id']}",
        headers=headers,
        json={"today_total": 8, "today_female": 2, "today_pp": 2, "today_kp": 1},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["cumulative"]["total"] == 18

    day1 = await client.get(f"/api/v1/reports/daily/{report_id}", headers=headers)
    assert day1.json()["cumulative"]["total"] == 10

    deleted = await client.delete(f"/api/v1/reports/daily/{second.json()['id']}", headers=headers)
    assert deleted.status_code == 204
    after = await client.get(f"/api/v1/reports/daily/{report_id}", headers=headers)
    assert after.json()["cumulative"]["total"] == 10


@pytest.mark.asyncio
async def test_cumulative_history_tracks_every_day(api):
    client = api["client"]
    headers = await _auth(client)
    for offset, total in enumerate((3, 4, 5)):
        await client.post(
            "/api/v1/reports/daily",
            headers=headers,
            json=make_report(D1 + timedelta(days=offset), total, 0, 0, 0, {"A": (total, 0, 0, 0)}),
        )

    end_d = D1 + timedelta(days=2)
    resp = await client.get(
        f"/api/v1/reports/cumulative?category_code=current_year&end_date={end_d.isoformat()}",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["cumulative"]["total"] == 12
    assert [row["report_date"] for row in body["history"]] == [
        D1.isoformat(),
        (D1 + timedelta(days=1)).isoformat(),
        end_d.isoformat(),
    ]
    assert [row["cumulative"]["total"] for row in body["history"]] == [3, 7, 12]


@pytest.mark.asyncio
async def test_duplicate_date_and_category_is_rejected(api):
    client = api["client"]
    headers = await _auth(client)
    payload = make_report(D1, 1, 0, 0, 0, {"A": (1, 0, 0, 0)})
    assert (await client.post("/api/v1/reports/daily", headers=headers, json=payload)).status_code == 201
    dup = await client.post("/api/v1/reports/daily", headers=headers, json=payload)
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_female_greater_than_total_is_rejected(api):
    client = api["client"]
    headers = await _auth(client)
    resp = await client.post(
        "/api/v1/reports/daily",
        headers=headers,
        json=make_report(D1, 5, 9, 0, 0, {"A": (5, 9, 0, 0)}),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_pp_kp_greater_than_total_is_rejected(api):
    client = api["client"]
    headers = await _auth(client)
    resp = await client.post(
        "/api/v1/reports/daily",
        headers=headers,
        json=make_report(D1, 5, 1, 4, 4, {"A": (5, 1, 4, 4)}),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_negative_numbers_are_rejected(api):
    client = api["client"]
    headers = await _auth(client)
    resp = await client.post(
        "/api/v1/reports/daily",
        headers=headers,
        json=make_report(D1, -1, 0, 0, 0, {}),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_history_is_paginated_and_filtered(api):
    client = api["client"]
    headers = await _auth(client)
    for offset in range(5):
        await client.post(
            "/api/v1/reports/daily",
            headers=headers,
            json=make_report(D1 + timedelta(days=offset), 1, 0, 0, 0, {"A": (1, 0, 0, 0)}),
        )
    page = await client.get("/api/v1/reports/history?page=1&size=2", headers=headers)
    assert page.status_code == 200
    body = page.json()
    assert len(body["items"]) == 2
    assert body["meta"]["total"] == 5


# ---------------------------------------------------------------- dashboard
@pytest.mark.asyncio
async def test_dashboard_headline_uses_cumulative_not_today(api):
    client = api["client"]
    headers = await _auth(client)
    for offset, total in enumerate((10, 20)):
        await client.post(
            "/api/v1/reports/daily",
            headers=headers,
            json=make_report(D1 + timedelta(days=offset), total, 0, 0, 0, {"A": (total, 0, 0, 0)}),
        )
    resp = await client.get(f"/api/v1/dashboard?date={D2.isoformat()}", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["headline"]["total"] == 30
    assert body["today"]["total"] == 20


# ----------------------------------------------------------------- telegram
@pytest.mark.asyncio
async def test_telegram_preview_matches_the_required_layout(api):
    client = api["client"]
    headers = await _auth(client)
    await client.post(
        "/api/v1/reports/daily",
        headers=headers,
        json=make_report(D2, 1, 0, 1, 0, {"D": (1, 0, 1, 0)}),
    )
    resp = await client.get(f"/api/v1/telegram/preview?date={D2.isoformat()}", headers=headers)
    assert resp.status_code == 200, resp.text
    text = resp.json()["text"]
    assert text.startswith("29/09/2026")
    assert "I. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026" in text
    assert "-និទ្ទេស D ចំនួន : 01 នាក់ ស្រី 00 នាក់" in text
    assert "(PP: 01 នាក់ , KP: 00 នាក់)" in text


@pytest.mark.asyncio
async def test_telegram_preview_can_be_filtered_to_one_grade(api):
    client = api["client"]
    headers = await _auth(client)
    await client.post(
        "/api/v1/reports/daily",
        headers=headers,
        json=make_report(D2, 5, 2, 3, 2, {"A": (3, 1, 2, 1), "D": (2, 1, 1, 1)}),
    )
    resp = await client.get(
        f"/api/v1/telegram/preview?date={D2.isoformat()}&grades=d", headers=headers
    )
    assert resp.status_code == 200, resp.text
    text = resp.json()["text"]
    assert text.startswith("29/09/2026\nនិទ្ទេស : D\n")
    assert "-និទ្ទេស D ចំនួន : 02 នាក់ ស្រី 01 នាក់" in text
    assert "-និទ្ទេស A" not in text
    # Totals count grade D only, not the category's 5.
    assert "សរុបរួមចំនួន : 02 នាក់ ស្រី 01 នាក់" in text
    assert "(PP: 01 នាក់, KP: 01 នាក់)" in text

    unfiltered = await client.get(
        f"/api/v1/telegram/preview?date={D2.isoformat()}", headers=headers
    )
    assert "និទ្ទេស : " not in unfiltered.json()["text"]
    assert "សរុបរួមចំនួន : 05 នាក់ ស្រី 02 នាក់" in unfiltered.json()["text"]


# -------------------------------------------------------------------- audit
@pytest.mark.asyncio
async def test_changes_are_audited(api):
    client = api["client"]
    headers = await _auth(client)
    created = await client.post(
        "/api/v1/reports/daily",
        headers=headers,
        json=make_report(D1, 7, 2, 1, 1, {"C": (7, 2, 1, 1)}),
    )
    assert created.status_code == 201

    logs = await client.get("/api/v1/audit", headers=headers)
    assert logs.status_code == 200
    actions = [item["action"] for item in logs.json()["items"]]
    assert "create" in actions
    assert any(item["entity_type"] == "daily_report" for item in logs.json()["items"])
