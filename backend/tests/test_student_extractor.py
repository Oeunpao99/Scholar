"""Parsing student fields out of application-form OCR text."""

from __future__ import annotations

from app.services.ai.student_extractor import extract_student_fields

FORM = """
ពាក្យស្នើសុំអាហារូបករណ៍
គោត្តនាម-នាម៖ សុខ ដារ៉ា          ភេទ៖ ស្រី
និទ្ទេស៖ B        លំដាប់ពិន្ទុ៖ ១៥២
វិទ្យាល័យ៖ វិទ្យាល័យព្រះស៊ីសុវត្ថិ
ថ្នាក់៖ វិទ្យាសាស្ត្រសង្គម
ស្នើសុំនៅសាកលវិទ្យាល័យ/វិទ្យាស្ថាន៖ សាកលវិទ្យាល័យភូមិន្ទភ្នំពេញ
ជំនាញ/មុខវិជ្ជា៖ វិទ្យាសាស្ត្រកុំព្យូទ័រ
លេខទូរស័ព្ទ៖ ០១២ ៣៤៥ ៦៧៨
"""


def test_reads_every_labelled_field_from_a_khmer_form():
    result = extract_student_fields(FORM)
    assert result.values == {
        "full_name": "សុខ ដារ៉ា",
        "gender": "F",
        "grade": "B",
        "score_rank": 152,  # Khmer digits converted
        "high_school": "វិទ្យាល័យព្រះស៊ីសុវត្ថិ",
        "stream": "social_science",
        "university": "សាកលវិទ្យាល័យភូមិន្ទភ្នំពេញ",
        "major": "វិទ្យាសាស្ត្រកុំព្យូទ័រ",
        "phone": "012 345 678",
    }
    assert result.missing == []
    assert result.warnings == []


def test_value_on_the_line_below_its_label_and_dotted_leaders():
    text = "គោត្តនាម និងនាម\nចាន់ វុទ្ធី\nភេទ ........ ប្រុស ........\nជំនាញ: គណិតវិទ្យា"
    result = extract_student_fields(text)
    assert result.values["full_name"] == "ចាន់ វុទ្ធី"
    assert result.values["gender"] == "M"
    assert result.values["major"] == "គណិតវិទ្យា"


def test_school_name_label_is_not_read_as_the_student_name():
    result = extract_student_fields("ឈ្មោះ: ចាន់ ធីតា\nឈ្មោះវិទ្យាល័យ: ហ៊ុន សែន បូទុម")
    assert result.values["full_name"] == "ចាន់ ធីតា"
    assert result.values["high_school"] == "ហ៊ុន សែន បូទុម"


def test_major_containing_science_does_not_set_the_stream():
    result = extract_student_fields("ជំនាញ: វិទ្យាសាស្ត្រកុំព្យូទ័រ")
    assert "stream" not in result.values


def test_english_labels_and_unlabelled_phone():
    text = "Name: Sok Dara\nSex: Female\nGrade: A\nRank: 12\nContact +855 12 345 678"
    result = extract_student_fields(text)
    assert result.values["full_name"] == "Sok Dara"
    assert result.values["gender"] == "F"
    assert result.values["grade"] == "A"
    assert result.values["score_rank"] == 12
    assert result.values["phone"] == "+855 12 345 678"


def test_unreadable_values_are_left_empty_with_a_warning():
    result = extract_student_fields("ភេទ: ??\nនិទ្ទេស: ៥")
    assert "gender" not in result.values
    assert "grade" not in result.values
    assert len(result.warnings) == 2
    assert "full_name" in result.missing


def test_empty_text_extracts_nothing():
    result = extract_student_fields("")
    assert result.values == {}
    assert result.found == []


def test_handles_common_khmer_ocr_typos_and_missing_coeng():
    text = (
        "គោតានាម-នាម: លី ម៉េង\n"
        "ភេទ: ប្រុស\n"
        "និទេស: A\n"
        "ចំណាត់ថ្នាក់: 15\n"
        "វិទាល័យ: វិទ្យាល័យបាក់ទូក\n"
        "លេខទូរសព្ទ: 098 765 432\n"
    )
    result = extract_student_fields(text)
    assert result.values["full_name"] == "លី ម៉េង"
    assert result.values["gender"] == "M"
    assert result.values["grade"] == "A"
    assert result.values["score_rank"] == 15
    assert result.values["high_school"] == "វិទ្យាល័យបាក់ទូក"
    assert result.values["phone"] == "098 765 432"


def test_stream_fallback_detects_bacii_stream_keywords():
    text = (
        "ឈ្មោះ: ជា ចិន្តា\n"
        "និទ្ទេស: B\n"
        "ផ្នែកវិទ្យាសាស្ត្រពិត\n"
    )
    result = extract_student_fields(text)
    assert result.values["stream"] == "science"


def test_handles_mangled_handwritten_form_with_filename():
    mangled_ocr = (
        "2រាជាណាចក្រកម្ពុជា\n"
        "ជាតិ សាសនា ព្រះមហាក្សត្រ\n"
        "D rite Kefichh\n"
        "ពាក្យស្នើសុំអាហារូបករណ៍ (%)\n"
        "ខ្ញុំបាទ/ នាងខ្ញុំឈ្មោះ: ឈាន...[2នឹក ee wives ...,អក្សរខ្នាត chheara. 206M 107 F ban.\n"
        "សញ្ញាតិ ,.7ខ្ញុំ:2.., ជនជាតិ gic MRTG. 2.2.18 RAN ) ឆ្នាំ 200.6 នៅភូមិ aan PEAI Le etn\n"
        "/#ន..ត័2ញ៉.5 -.-.- មុខរបរ ... នី.2: -.- លេខទូរស័ព្ទ\n"
    )
    result = extract_student_fields(mangled_ocr, filename="ឈាន ស្រីនិត.pdf")
    assert result.values["full_name"] == "ឈាន ស្រីនិត"
    assert result.values["gender"] == "F"
