# aireadi_retinal_imaging

Utilities for organizing retinal imaging exports, converting them into
structured DICOM files, extracting metadata, and generating Excel compliance
reports for ophthalmic DICOM objects.

The repository can be installed as a Python package and exposes a console
entry point for compliance reporting. Legacy scripts under `main/` are still
available for direct use.

## Repository Layout

```text
aireadi_retinal_imaging/
  main/
    create_compliance_report.py   # DICOM compliance report CLI
    process_*.py                  # Device-specific processing pipelines
  year_3/
    compliance_report.py          # Excel report generation
    compliance_rules.py           # Ophthalmic DICOM compliance rule sets
    imaging_*                     # Device conversion, organization, metadata helpers
  notebooks/
    main_processing.ipynb
    post_processing.ipynb
  environment_aireadi_2025.yml    # Conda environment definition
```

## Environment

Create the Conda environment from the provided file:

```bash
conda env create -f aireadi_retinal_imaging/environment_aireadi_2025.yml
conda activate aireadi_2025
```

Install the package from the repository root:

```bash
cd aireadi_retinal_imaging
python -m pip install -e ".[test]"
```

If you are working offline in an environment that already has the dependencies
installed, disable build isolation so pip does not try to download build
dependencies:

```bash
python -m pip install -e ".[test]" --no-build-isolation
```

## Compliance Report CLI

After installation, use `aireadi-compliance-report` to take a folder of DICOM
files and generate Excel compliance reports.

```bash
aireadi-compliance-report INPUT_FOLDER DEVICE_NAME OUTPUT_FOLDER
```

Arguments:

| Argument | Description |
| --- | --- |
| `INPUT_FOLDER` | Folder containing input DICOM files. The script walks this folder recursively. |
| `DEVICE_NAME` | Label used in output filenames and folder grouping, for example `Heidelberg_Spectralis_OCT` or `maestro2_check`. |
| `OUTPUT_FOLDER` | Folder where generated `.xlsx` reports are written. |

Example:

```bash
aireadi-compliance-report \
  "/path/to/dicom/input" \
  "maestro2_check" \
  "/path/to/compliance/output"
```

The script also supports:

```bash
aireadi-compliance-report --help
```

The legacy script path remains available:

```bash
python -m aireadi_retinal_imaging.main.create_compliance_report \
  INPUT_FOLDER \
  DEVICE_NAME \
  OUTPUT_FOLDER
```

### Input Behavior

The compliance report command expects a directory, not a single `.dcm` file.
To report on one file, place that file in its own directory and pass the
directory as `INPUT_FOLDER`.

The file discovery helper skips:

- `.csv` files
- macOS AppleDouble files beginning with `._`
- files whose names do not start with a letter or digit

Every remaining file is passed to `pydicom.dcmread(...)`, so non-DICOM files in
the input tree can cause the command to fail.

### Device Scope

The compliance report CLI is SOP-class driven, not device-specific. It reads
each DICOM file's `SOPClassUID`, sorts files into supported ophthalmic SOP
classes, and applies the matching rule set.

The `DEVICE_NAME` argument does not select validation rules. It is used only to
name outputs. Internally, the first underscore-delimited component becomes the
output subfolder name:

```text
DEVICE_NAME=maestro2_check
OUTPUT_FOLDER=/tmp/reports

reports are written under:
/tmp/reports/maestro2/
```

Supported report buckets include:

- Ophthalmic Photography 8 Bit Image
- Ophthalmic Tomography Image
- Ophthalmic Tomography Volume
- Segmentation / heightmap-style objects
- Ophthalmic OCT En Face Image
- Ophthalmic Photography 16 Bit Image

Unsupported SOP classes are not reported.

### Output Files

Depending on the SOP classes found in the input folder, the command writes one
or more Excel files under:

```text
OUTPUT_FOLDER/<device>/
```

Possible report filenames include:

```text
<DEVICE_NAME>_eval_op.xlsx
<DEVICE_NAME>_eval_op_nested.xlsx
<DEVICE_NAME>_eval_oct.xlsx
<DEVICE_NAME>_eval_oct_nested.xlsx
<DEVICE_NAME>_eval_volume_analysis.xlsx
<DEVICE_NAME>_eval_volume_analysis_nested.xlsx
<DEVICE_NAME>_eval_heightmap_segmentation.xlsx
<DEVICE_NAME>_eval_heightmap_segmentation_nested.xlsx
<DEVICE_NAME>_eval_en_face.xlsx
<DEVICE_NAME>_eval_enface_nested.xlsx
<DEVICE_NAME>_op_16.xlsx
<DEVICE_NAME>_op_16_nested.xlsx
```

Each standard compliance workbook contains:

- `compliance_report`: required, missing, empty, and preferred tags according
  to the relevant rule set
- `extra_headers`: DICOM tags present in the source files that were not part
  of the selected compliance rule set

Nested workbooks break selected sequence tags into separate sheets for easier
inspection.

## Device Processing CLIs

The `main/process_*.py` scripts run broader device-specific pipelines. These
scripts organize raw exports, convert supported data into DICOM, arrange final
folder structure, and extract metadata. They do not run the compliance report
CLI automatically.

These processing scripts have not yet been converted to packaged console
entry points. Several still contain local development path assumptions, so use
`PYTHONPATH` when running them directly from this checkout:

```bash
export PYTHONPATH="$PWD/year_3"
```

All device processing scripts use the same argument shape:

```bash
python main/process_DEVICE.py \
  --input-folder INPUT_FOLDER \
  --output-folder OUTPUT_FOLDER
```

Available scripts:

| Script | Purpose |
| --- | --- |
| `process_topcon.py` | Topcon Maestro2 / Triton processing pipeline |
| `process_cirrus.py` | Zeiss Cirrus processing pipeline |
| `process_spectralis.py` | Heidelberg Spectralis processing pipeline |
| `process_flio.py` | FLIO processing pipeline |
| `process_optomed.py` | Optomed retinal photography processing pipeline |
| `process_eidon.py` | Eidon retinal photography processing pipeline |

Example:

```bash
python main/process_topcon.py \
  --input-folder "/path/to/raw/topcon/export" \
  --output-folder "/path/to/processed/output"
```

Typical pipeline output folders:

```text
OUTPUT_FOLDER/
  step2_organized/
  step3_converted_dicom/
  step4_final_structure/
  metadata/
  logs/
```

The processing scripts recreate their output subdirectories at startup. Do not
point `--output-folder` at a directory containing files you need to keep.

## Common Workflows

### Generate a compliance report for existing DICOM files

```bash
aireadi-compliance-report \
  "/path/to/dicom/files" \
  "report_batch_name" \
  "/path/to/reports"
```

### Process raw device data, then report on converted DICOM files

```bash
export PYTHONPATH="$PWD/year_3"

python main/process_topcon.py \
  --input-folder "/path/to/raw/topcon/export" \
  --output-folder "/path/to/processed/topcon"

aireadi-compliance-report \
  "/path/to/processed/topcon/step3_converted_dicom" \
  "topcon_batch" \
  "/path/to/processed/topcon/compliance_reports"
```

## Tests

Install the test extra and run pytest from the repository root:

```bash
python -m pip install -e ".[test]"
python -m pytest
```

The current tests focus on the packaged compliance report CLI: argument
parsing, file filtering, SOP-class dispatch, output naming, and the main entry
point.

## Known Limitations

- The compliance report workflow is packaged and exposed as
  `aireadi-compliance-report`; the device processing pipelines are still
  legacy direct-run scripts.
- Several device processing scripts rely on local path assumptions from the
  original development environment; set `PYTHONPATH` as shown above.
- The compliance report CLI accepts folders only. Single-file use requires
  putting the file in a folder.
- Compliance reporting is designed for supported ophthalmic DICOM SOP classes,
  not arbitrary DICOM objects.
- Unsupported SOP classes are silently omitted from generated reports.
