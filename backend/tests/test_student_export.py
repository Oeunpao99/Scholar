"""Test student export to Word docx, Excel xlsx, and PDF."""

from app.models.student import Student
from app.services.student_export import (
    export_students_docx,
    export_students_xlsx,
    export_students_pdf,
)


def _make_dummy_students():
    return [
        Student(
            academic_year=2026,
            full_name="ឈាន ស្រីនិត",
            gender="F",
            grade="D",
            score_rank=152,
            high_school="វិទ្យាល័យ ហ៊ុន សែន រលាំងចក",
            stream="science",
            university="សាកលវិទ្យាល័យភូមិន្ទភ្នំពេញ",
            major="វិទ្យាសាស្ត្រកុំព្យូទ័រ",
            phone="012345678",
            note="សិស្សអាហារូបករណ៍ ១០០%",
        ),
        Student(
            academic_year=2026,
            full_name="ស៊ុន វណ្ណៈ",
            gender="M",
            grade="B",
            score_rank=45,
            high_school="វិទ្យាល័យ ព្រះស៊ីសុវត្ថិ",
            stream="social_science",
            university="សាកលវិទ្យាល័យភូមិន្ទនីតិសាស្ត្រ",
            major="ច្បាប់",
            phone="098765432",
            note=None,
        ),
    ]


def test_export_students_docx():
    students = _make_dummy_students()
    data = export_students_docx(students, academic_year=2026, institution="Scholar System")
    assert isinstance(data, bytes)
    assert len(data) > 1000
    # Check docx zip magic bytes
    assert data[:4] == b"PK\x03\x04"


def test_export_students_xlsx():
    students = _make_dummy_students()
    data = export_students_xlsx(students, academic_year=2026, institution="Scholar System")
    assert isinstance(data, bytes)
    assert len(data) > 1000
    # Check xlsx zip magic bytes
    assert data[:4] == b"PK\x03\x04"


def test_export_students_pdf():
    students = _make_dummy_students()
    data = export_students_pdf(students, academic_year=2026, institution="Scholar System")
    assert isinstance(data, bytes)
    assert len(data) > 500
    # Check PDF magic bytes
    assert data[:4] == b"%PDF"
