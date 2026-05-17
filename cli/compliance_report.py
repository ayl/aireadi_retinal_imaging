"""CLI for generating ophthalmic DICOM compliance reports."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pydicom
from pydicom.datadict import DicomDictionary, keyword_dict

from ophthalmic_dicom_compliance.compliance import nested_excel, report, rules


OPHTHALMIC_PHOTOGRAPHY_8_BIT = "1.2.840.10008.5.1.4.1.1.77.1.5.1"
OPHTHALMIC_TOMOGRAPHY_IMAGE = "1.2.840.10008.5.1.4.1.1.77.1.5.4"
OPHTHALMIC_TOMOGRAPHY_VOLUME = "1.2.840.10008.5.1.4.1.1.77.1.5.8"
SEGMENTATION_STORAGE = "1.2.840.10008.5.1.4.1.1.66.5"
SURFACE_SCAN_MESH = "1.2.840.10008.5.1.4.1.1.66.8"
LEGACY_HEIGHTMAP = "1.3.6.1.4.1.33437.11.10.240.10"
PLACEHOLDER_HEIGHTMAP = "1.2.840.10008.5.1.4.xxxxx.1"
OPHTHALMIC_OCT_EN_FACE = "1.2.840.10008.5.1.4.1.1.77.1.5.7"
OPHTHALMIC_PHOTOGRAPHY_16_BIT = "1.2.840.10008.5.1.4.1.1.77.1.5.2"


@dataclass(frozen=True)
class ReportSpec:
    name: str
    sop_class_uids: frozenset[str]
    rules: object
    report_suffix: str
    nested_suffix: str
    nested_tags: tuple[str, ...]


REPORT_SPECS: tuple[ReportSpec, ...] = (
    ReportSpec(
        name="Ophthalmic Photography 8 Bit Image",
        sop_class_uids=frozenset({OPHTHALMIC_PHOTOGRAPHY_8_BIT}),
        rules=rules.cfp_ir_rule,
        report_suffix="eval_op",
        nested_suffix="eval_op_nested",
        nested_tags=(
            "00082218",
            "00220006",
            "00220015",
            "00220016",
            "00220017",
            "00220018",
            "00220019",
            "0022001A",
        ),
    ),
    ReportSpec(
        name="Ophthalmic Tomography Image",
        sop_class_uids=frozenset({OPHTHALMIC_TOMOGRAPHY_IMAGE}),
        rules=rules.oct_b_rule,
        report_suffix="eval_oct",
        nested_suffix="eval_oct_nested",
        nested_tags=(
            "52009229",
            "52009230",
            "00209221",
            "00209222",
            "00400555",
            "00220015",
            "00220017",
            "00082218",
        ),
    ),
    ReportSpec(
        name="Ophthalmic Tomography Volume",
        sop_class_uids=frozenset({OPHTHALMIC_TOMOGRAPHY_VOLUME}),
        rules=rules.volume_analysis_rule,
        report_suffix="eval_volume_analysis",
        nested_suffix="eval_volume_analysis_nested",
        nested_tags=(
            "52009229",
            "52009230",
            "00209221",
            "00209222",
            "00221423",
            "00221640",
        ),
    ),
    ReportSpec(
        name="Segmentation",
        sop_class_uids=frozenset(
            {
                PLACEHOLDER_HEIGHTMAP,
                SEGMENTATION_STORAGE,
                LEGACY_HEIGHTMAP,
                SURFACE_SCAN_MESH,
            }
        ),
        rules=rules.heightmap_rule,
        report_suffix="eval_heightmap_segmentation",
        nested_suffix="eval_heightmap_segmentation_nested",
        nested_tags=(
            "52009229",
            "52009230",
            "00209221",
            "00209222",
            "00620002",
            "00081115",
        ),
    ),
    ReportSpec(
        name="En Face",
        sop_class_uids=frozenset({OPHTHALMIC_OCT_EN_FACE}),
        rules=rules.octa_enface_rule,
        report_suffix="eval_en_face",
        nested_suffix="eval_enface_nested",
        nested_tags=(
            "00082112",
            "00221612",
            "00221615",
            "00221620",
            "00082218",
            "0022001D",
            "00082228",
            "00220031",
            "0022EEE0",
            "00081115",
            "00221627",
            "00221632",
        ),
    ),
    ReportSpec(
        name="Ophthalmic Photography 16 Bit Image",
        sop_class_uids=frozenset({OPHTHALMIC_PHOTOGRAPHY_16_BIT}),
        rules=rules.cfp_ir_16_rule,
        report_suffix="op_16",
        nested_suffix="op_16_nested",
        nested_tags=(
            "00082218",
            "00220006",
            "00220015",
            "00220016",
            "00220017",
            "00220018",
            "00220019",
            "0022001A",
        ),
    ),
)


def register_private_dicom_keywords() -> None:
    """Register tags used by the retinal imaging report rules."""
    new_dict_items = {
        0x00221627: (
            "SQ",
            "1",
            "En Face Volume Descriptor Sequence",
            "",
            "EnFaceVolumeDescriptorSequence",
        ),
        0x00221629: (
            "CS",
            "1",
            "En Face Volume Descriptor Scope",
            "",
            "EnFaceVolumeDescriptorScope",
        ),
        0x0008114C: (
            "SQ",
            "1",
            "Referenced Segmentation Sequence",
            "",
            "ReferencedSegmentationSequence",
        ),
        0x00660005: ("FL", "1", "Surface Offset", "", "SurfaceOffset"),
    }

    DicomDictionary.update(new_dict_items)
    keyword_dict.update({val[4]: tag for tag, val in new_dict_items.items()})


def extract_numeric_part(path: str) -> list[int | str]:
    parts = Path(path).name.split(".")
    return [int(part) if part.isdigit() else part for part in parts]


def get_filtered_file_names(folder_path: str | os.PathLike[str]) -> list[str]:
    filtered_files: list[str] = []
    for root, _, files in os.walk(folder_path):
        for file_name in files:
            if file_name.lower().endswith(".csv"):
                continue
            if file_name.startswith("._"):
                continue
            if not file_name or not (file_name[0].isalpha() or file_name[0].isdigit()):
                continue
            filtered_files.append(os.path.join(root, file_name))
    return filtered_files


def output_device_folder(device_protocol: str) -> str:
    return device_protocol.split("_", 1)[0]


def sort_files_by_sop_class(input_files: Iterable[str]) -> dict[str, list[str]]:
    buckets = {spec.name: [] for spec in REPORT_SPECS}
    sop_to_spec = {
        sop_class_uid: spec.name
        for spec in REPORT_SPECS
        for sop_class_uid in spec.sop_class_uids
    }

    for file_path in input_files:
        dicom = pydicom.dcmread(file_path)
        spec_name = sop_to_spec.get(str(dicom.SOPClassUID))
        if spec_name is not None:
            buckets[spec_name].append(file_path)

    return buckets


def create_reports_for_specs(
    buckets: dict[str, list[str]],
    device_protocol: str,
    output_folder: str | os.PathLike[str],
) -> tuple[list[str], ...]:
    device = output_device_folder(device_protocol)
    output_path = Path(output_folder) / device
    output_path.mkdir(parents=True, exist_ok=True)

    ordered_bucket_values: list[list[str]] = []
    for spec in REPORT_SPECS:
        files = sorted(buckets[spec.name], key=extract_numeric_part)
        ordered_bucket_values.append(files)
        if not files:
            continue

        report.create_report(
            spec.rules,
            files,
            str(output_path / f"{device_protocol}_{spec.report_suffix}.xlsx"),
        )
        nested_excel.multi_create_excelsheet_nested_structure(
            files,
            list(spec.nested_tags),
            str(output_path / f"{device_protocol}_{spec.nested_suffix}.xlsx"),
        )

    return tuple(ordered_bucket_values)


def sort_them_by_sop_class(
    input_folder: str | os.PathLike[str],
    device_protocol: str,
    output_folder: str | os.PathLike[str],
) -> tuple[list[str], ...]:
    register_private_dicom_keywords()
    input_files = sorted(get_filtered_file_names(input_folder), key=extract_numeric_part)
    buckets = sort_files_by_sop_class(input_files)
    return create_reports_for_specs(buckets, device_protocol, output_folder)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sort DICOM files by SOP Class UID and generate compliance reports."
    )
    parser.add_argument(
        "input_folder",
        type=str,
        help="Path to the folder containing the input DICOM files.",
    )
    parser.add_argument(
        "device_name",
        type=str,
        help="A unique name for the device and protocol (e.g., 'Heidelberg_Spectralis_OCT').",
    )
    parser.add_argument(
        "output_folder",
        type=str,
        help="Path to the folder where the output reports will be saved.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    print("--- Starting DICOM Sorting and Reporting ---")
    buckets = sort_them_by_sop_class(
        input_folder=args.input_folder,
        device_protocol=args.device_name,
        output_folder=args.output_folder,
    )

    print("\n--- Analysis Complete ---")
    for spec, files in zip(REPORT_SPECS, buckets):
        print(f"Found {len(files)} files for {spec.name}")
    print(f"\nAll reports have been saved in the '{args.output_folder}' directory.")
    print("-----------------------------------------")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
