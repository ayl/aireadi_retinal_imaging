import os
from copy import deepcopy

import pydicom
from pydicom import dcmread, dcmwrite
from pydicom.datadict import DicomDictionary, keyword_dict
from pydicom.dataelem import DataElement
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence
from pydicom.tag import Tag


def convert_dicom  (input_path: str, output_dir: str, opt):
    oct_path = opt
    seg = pydicom.dcmread(input_path)

    ds = pydicom.dcmread(oct_path)
    oct_pixel_spacing = ds[Tag(0x5200,0x9229)].value[0][Tag(0x0028,0x9110)].value[0][Tag(0x0028,0x0030)].value
    thickness_mm = oct_pixel_spacing[0]

    pm_item = seg[Tag(0x5200,0x9229)].value[0][Tag(0x0028,0x9110)].value[0]
    if Tag(0x0018,0x0050) in pm_item:
        pm_item[Tag(0x0018,0x0050)].value = thickness_mm
    else:
        pm_item.add_new(Tag(0x0018,0x0050), "DS", thickness_mm)

    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.basename(input_path)
    out_path = os.path.join(output_dir, f"converted_{filename}")
    
    dcmwrite(out_path, seg, write_like_original=False)

    return out_path