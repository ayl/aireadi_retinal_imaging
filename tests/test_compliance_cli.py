from __future__ import annotations

from types import SimpleNamespace

from aireadi_retinal_imaging.compliance import nested_excel, report, rules
from aireadi_retinal_imaging.cli import compliance_report as cli
from aireadi_retinal_imaging.dicom import classification, standards, utils


def test_new_package_layout_imports_core_modules():
    assert report is not None
    assert rules is not None
    assert nested_excel is not None
    assert classification is not None
    assert standards is not None
    assert utils is not None


def test_parser_accepts_three_positional_arguments():
    parser = cli.build_parser()

    args = parser.parse_args(["/input", "maestro2_check", "/output"])

    assert args.input_folder == "/input"
    assert args.device_name == "maestro2_check"
    assert args.output_folder == "/output"


def test_filtered_file_names_match_legacy_behavior(tmp_path):
    keep = tmp_path / "1.2.3.dcm"
    keep.write_text("not read in this test")
    csv_file = tmp_path / "skip.csv"
    csv_file.write_text("skip")
    apple_double = tmp_path / "._skip.dcm"
    apple_double.write_text("skip")
    punctuation = tmp_path / "-skip.dcm"
    punctuation.write_text("skip")
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    nested = nested_dir / "A-file.dcm"
    nested.write_text("not read in this test")

    assert sorted(cli.get_filtered_file_names(tmp_path)) == sorted(
        [str(keep), str(nested)]
    )


def test_sort_them_by_sop_class_dispatches_reports_by_sop_uid(tmp_path, monkeypatch):
    input_folder = tmp_path / "input"
    output_folder = tmp_path / "output"
    input_folder.mkdir()

    oct_file = input_folder / "2.1.dcm"
    oct_file.write_text("not read in this test")
    op_file = input_folder / "1.1.dcm"
    op_file.write_text("not read in this test")
    unsupported_file = input_folder / "3.1.dcm"
    unsupported_file.write_text("not read in this test")

    sop_by_path = {
        str(oct_file): cli.OPHTHALMIC_TOMOGRAPHY_IMAGE,
        str(op_file): cli.OPHTHALMIC_PHOTOGRAPHY_8_BIT,
        str(unsupported_file): "1.2.3.unsupported",
    }

    def fake_dcmread(file_path):
        return SimpleNamespace(SOPClassUID=sop_by_path[str(file_path)])

    create_report_calls = []
    nested_report_calls = []

    def fake_create_report(rules, files, output_file):
        create_report_calls.append((rules, files, output_file))

    def fake_nested_report(files, tags, output_file):
        nested_report_calls.append((files, tags, output_file))

    monkeypatch.setattr(cli.pydicom, "dcmread", fake_dcmread)
    monkeypatch.setattr(cli.report, "create_report", fake_create_report)
    monkeypatch.setattr(
        cli.nested_excel,
        "multi_create_excelsheet_nested_structure",
        fake_nested_report,
    )

    buckets = cli.sort_them_by_sop_class(input_folder, "maestro2_check", output_folder)

    assert buckets[0] == [str(op_file)]
    assert buckets[1] == [str(oct_file)]
    assert all(bucket == [] for bucket in buckets[2:])
    assert len(create_report_calls) == 2
    assert len(nested_report_calls) == 2
    assert create_report_calls[0][2].endswith(
        "output/maestro2/maestro2_check_eval_op.xlsx"
    )
    assert create_report_calls[1][2].endswith(
        "output/maestro2/maestro2_check_eval_oct.xlsx"
    )


def test_main_returns_success(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "sort_them_by_sop_class",
        lambda input_folder, device_protocol, output_folder: tuple(
            [] for _ in cli.REPORT_SPECS
        ),
    )

    exit_code = cli.main(["/input", "device_name", "/output"])

    assert exit_code == 0
    assert "Analysis Complete" in capsys.readouterr().out
