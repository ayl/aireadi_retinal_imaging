from __future__ import annotations

import pytest

from aireadi_retinal_imaging.compliance import nested_excel, report
from aireadi_retinal_imaging.compliance import rules as compliance_rules
from tests.fixtures import write_minimal_dicom


def make_rules(elements):
    return compliance_rules.ComplianceRules(
        "test",
        [
            compliance_rules.Entity(
                "Entity",
                [compliance_rules.Module("Module", "M.1", elements)],
            )
        ],
    )


def test_compliance_rule_tags_returns_unique_tags():
    rules = make_rules(
        [
            compliance_rules.Element("PatientName", "00100010", "PN"),
            compliance_rules.Element("PatientNameAgain", "00100010", "PN"),
            compliance_rules.Element("PatientID", "00100020", "LO"),
        ]
    )

    assert set(rules.tags()) == {"00100010", "00100020"}


def test_extract_dicom_dict_reads_selected_tags(tmp_path):
    dcm_file = write_minimal_dicom(tmp_path / "sample.dcm")

    result = report.extract_dicom_dict(str(dcm_file), ["00100010", "00100020"])

    assert result["filepath"] == str(dcm_file)
    assert result["00100010"].value == [{"Alphabetic": "Alice^Example"}]
    assert "00100020" not in result
    assert not result["00100010"].is_empty()


def test_extract_dicom_dict_validates_inputs(tmp_path):
    missing = tmp_path / "missing.dcm"

    with pytest.raises(FileNotFoundError):
        report.extract_dicom_dict(str(missing), ["00100010"])

    existing = write_minimal_dicom(tmp_path / "sample.dcm")
    with pytest.raises(NotImplementedError):
        report.extract_dicom_dict(str(existing), [["00100010"]])


def test_extract_dicom_dict_extra_excludes_rule_tags(tmp_path):
    dcm_file = write_minimal_dicom(tmp_path / "sample.dcm", include_patient_id=True)

    result = report.extract_dicom_dict_extra(str(dcm_file), ["00100010"])

    assert "00100020" in result
    assert result["00100020"].value == ["123"]


def test_evaluate_compliance_covers_required_optional_and_conditionals():
    elements = [
        compliance_rules.Element("MustPresent", "00100010", "PN"),
        compliance_rules.Element("MustEmpty", "00100020", "LO"),
        compliance_rules.Element("MustMissing", "00100030", "DA"),
        compliance_rules.Element(
            "AllowMissing", "00100040", "CS", compliance_rules.ALLOW_EMPTY
        ),
        compliance_rules.Element(
            "Preferred", "00100050", "LO", compliance_rules.PREFERRED
        ),
        compliance_rules.Element(
            "ConditionalTag",
            "00100060",
            "LO",
            compliance_rules.MustTagExistIf("00200010", lambda value: value == ["yes"]),
        ),
        compliance_rules.Element(
            "ConditionalValue",
            "00100070",
            "LO",
            compliance_rules.MustExistIf("00200020", lambda value: value == ["yes"]),
        ),
        compliance_rules.Element(
            "ConditionalFalse",
            "00100080",
            "LO",
            compliance_rules.MustExistIf("00200030", lambda value: value == ["yes"]),
        ),
        compliance_rules.Element(
            "ConditionalNoPremise",
            "00100090",
            "LO",
            compliance_rules.MustTagExistIf("00200040", lambda value: True),
        ),
    ]
    dicom_dict = {
        "00100010": report.DicomEntry("00100010", "MustPresent", "PN", ["Alice"]),
        "00100020": report.DicomEntry("00100020", "MustEmpty", "LO", []),
        "00200010": report.DicomEntry("00200010", "Premise", "LO", ["yes"]),
        "00200020": report.DicomEntry("00200020", "Premise", "LO", ["yes"]),
        "00200030": report.DicomEntry("00200030", "Premise", "LO", ["no"]),
    }

    result = report.evaluate_compliance(make_rules(elements), dicom_dict)

    assert result["00100010"] == report.ActionNeeded.NONE
    assert result["00100020"] == report.ActionNeeded.VALUE_NEEDED
    assert result["00100030"] == report.ActionNeeded.TAG_AND_VALUE_NEEDED
    assert result["00100040"] == report.ActionNeeded.TAG_NEEDED
    assert result["00100050"] == report.ActionNeeded.PREFERRED
    assert result["00100060"] == report.ActionNeeded.TAG_NEEDED
    assert result["00100070"] == report.ActionNeeded.TAG_AND_VALUE_NEEDED
    assert result["00100080"] == report.ActionNeeded.NONE
    assert result["00100090"] == report.ActionNeeded.PREFERRED


def test_export_to_excel_and_create_report_write_workbooks(tmp_path):
    dcm_file = write_minimal_dicom(tmp_path / "sample.dcm")
    output_file = tmp_path / "report.xlsx"
    rules = make_rules(
        [
            compliance_rules.Element("PatientName", "00100010", "PN"),
            compliance_rules.Element("PatientID", "00100020", "LO"),
            compliance_rules.Element(
                "PatientSex", "00100040", "CS", compliance_rules.PREFERRED
            ),
        ]
    )

    report.create_report(rules, [str(dcm_file)], str(output_file))

    assert output_file.exists()
    assert output_file.stat().st_size > 0


def test_export_to_excel_single_row_paths(tmp_path, monkeypatch):
    dcm_file = tmp_path / "sample.dcm"
    dcm_file.write_text("placeholder")
    output_file = tmp_path / "single.xlsx"
    rules = make_rules([compliance_rules.Element("PatientName", "00100010", "PN")])
    dicom_dict = {
        "filepath": str(dcm_file),
        "00100010": report.DicomEntry("00100010", "PatientName", "PN", ["Alice"]),
    }
    actions = [{"00100010": report.ActionNeeded.NONE}]
    monkeypatch.setattr(report, "extract_dicom_dict_extra", lambda file_path, tags: {})

    report.export_to_excel(rules, [dicom_dict], actions, str(output_file), [str(dcm_file)])

    assert output_file.exists()


def test_nested_process_tags_extracts_simple_and_nested_values():
    output = {"indentation": [], "tag": [], "element_name": [], "vr": [], "value": []}
    dicom = {
        "00100010": {"vr": "PN", "Value": ["Alice"]},
        "00082112": {
            "vr": "SQ",
            "Value": [{"00081150": {"vr": "UI", "Value": ["1.2.3"]}}],
        },
    }

    nested_excel.process_tags(["00100010", "00082112"], dicom, 0, output)

    assert output["tag"] == ["00100010", "00082112", "00081150"]
    assert output["indentation"] == ["", "", ">"]


def test_nested_extract_dicom_dict_reads_requested_tags(tmp_path):
    dcm_file = write_minimal_dicom(
        tmp_path / "sample.dcm", include_source_sequence=True
    )

    result = nested_excel.extract_dicom_dict(str(dcm_file), ["00100010", "00082112"])

    assert result["tag"][:2] == ["00100010", "00082112"]
    assert "00081150" in result["tag"]


def fake_nested_result():
    return {
        "indentation": ["", ">"],
        "tag": ["00082112", "00081150"],
        "element_name": ["SourceImageSequence", "ReferencedSOPClassUID"],
        "vr": ["SQ", "UI"],
        "value": [[{"00081150": {"vr": "UI", "Value": ["1.2.3"]}}], ["1.2.3"]],
    }


def test_create_excelsheet_nested_structure_writes_workbook(tmp_path, monkeypatch):
    output_file = tmp_path / "nested.xlsx"
    monkeypatch.setattr(
        nested_excel, "extract_dicom_dict", lambda input_file, tags: fake_nested_result()
    )

    nested_excel.create_excelsheet_nested_structure(
        "sample.dcm", ["00082112"], str(output_file)
    )

    assert output_file.exists()


def test_multi_create_excelsheet_nested_structure_writes_workbook(tmp_path, monkeypatch):
    output_file = tmp_path / "multi_nested.xlsx"
    monkeypatch.setattr(
        nested_excel, "extract_dicom_dict", lambda input_file, tags: fake_nested_result()
    )

    nested_excel.multi_create_excelsheet_nested_structure(
        ["one.dcm", "two.dcm"], ["00082112"], str(output_file)
    )

    assert output_file.exists()
