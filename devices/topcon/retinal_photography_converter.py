import os

import pydicom
from pydicom import dcmread, dcmwrite
from pydicom.dataelem import DataElement
from pydicom.tag import Tag


def convert_dicom(input_path: str, output_dir: str) -> str:
    """
    Read a DICOM, set PupilDilated (0022,000D) to 'YES', and save it to output_dir
    as converted_<original_filename>. Returns the output path.
    """
    # Read the source file
    ds = dcmread(input_path)

    # Ensure/modify PupilDilated (VR: CS). Valid values are 'YES' or 'NO'.
    tag = Tag(0x0022, 0x000D)  # PupilDilated
    if tag in ds:
        ds[tag].value = "YES"
    else:
        ds.add(DataElement(tag, "CS", "YES"))

    ds.PixelSpacing = [0.006868132, 0.006868132]
    ds.DegreeOfDilation = None
    ds.MydriaticAgentSequence = []

    if "LossyImageCompressionRatio" not in ds:
        ds.LossyImageCompression = "00"

    # Build output path and write
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.basename(input_path)
    out_path = os.path.join(output_dir, f"converted_{filename}")

    # Write with "write_like_original=False" to harmonize/normalize the file
    dcmwrite(out_path, ds, write_like_original=False)

    return out_path
