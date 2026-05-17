import os

import pydicom
from pydicom import dcmread, dcmwrite
from pydicom.dataelem import DataElement
from pydicom.tag import Tag


def convert_dicom(input_path: str, output_dir: str) -> str:

    ds = dcmread(input_path)
    if "LossyImageCompressionRatio" not in ds:
        ds.LossyImageCompression = "00"


    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.basename(input_path)
    out_path = os.path.join(output_dir, f"converted_{filename}")

    # Write with "write_like_original=False" to harmonize/normalize the file
    dcmwrite(out_path, ds, write_like_original=False)

    return out_path