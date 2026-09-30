"""Importing a student list from Word / Excel."""

import io

import pytest
from openpyxl import Workbook

from app.core.errors import ValidationError
from app.services.student_export import export_students_docx, export_students_xlsx
from app.services.student_import import parse_student_list
from tests.test_student_export import _make_dummy_students


@pytest.mark.parametrize("export", [export_students_xlsx, export_students_docx])
def test_exported_file_imports_back(export):
    parsed = parse_student_list(export(_make_dummy_students(), academic_year=2026))
    assert parsed.errors == []
    first, second = (r.values for r in parsed.rows)
    assert first["full_name"] == "ឈាន ស្រីនិត"
    assert (first["gender"], first["grade"], first["score_rank"]) == ("F", "D", 152)
    assert first["stream"] == "science"
    assert first["university"] == "សាកលវិទ្យាល័យភូមិន្ទភ្នំពេញ"
    assert first["high_school"] == "វិទ្យាល័យ ហ៊ុន សែន រលាំងចក"
    assert second["stream"] == "social_science"
    assert "note" not in second  # "—" placeholder means empty


def _sheet(rows):
    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_english_headers_any_order_and_bad_rows_reported():
    parsed = parse_student_list(_sheet([
        ["Phone", "Sex", "Name", "Grade"],
        [12345678, "Female", "Sok Dara", "b"],
        ["", "?", "Bad Gender", ""],
        ["", "M", "", ""],
        [None, None, None, None],
    ]))
    assert len(parsed.rows) == 1
    assert parsed.rows[0].values == {"phone": "012345678", "gender": "F", "full_name": "Sok Dara", "grade": "B"}
    assert [row for row, _ in parsed.errors] == [3, 4]


def test_rejects_non_office_and_headerless_files():
    with pytest.raises(ValidationError):
        parse_student_list(b"not a zip")
    with pytest.raises(ValidationError):
        parse_student_list(_sheet([["a", "b"], [1, 2]]))
