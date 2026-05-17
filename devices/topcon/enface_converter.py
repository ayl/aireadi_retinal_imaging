import os
from copy import deepcopy

import pydicom
from pydicom import dcmread, dcmwrite
from pydicom.datadict import DicomDictionary, keyword_dict
from pydicom.dataelem import DataElement
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence
from pydicom.tag import Tag

# Define items as (VR, VM, description, is_retired flag, keyword)
#   Leave is_retired flag blank.
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

# Update the dictionary itself
DicomDictionary.update(new_dict_items)

# Update the reverse mapping from name to tag
new_names_dict = dict([(val[4], tag) for tag, val in new_dict_items.items()])
keyword_dict.update(new_names_dict)


def convert_dicom (input_path: str, output_dir: str, op, opt, vol, seg):

    ds = pydicom.dcmread(input_path)

    SEQ_TAG = Tag(0x0022, 0x1627)
    REF_SEQ_TAG = Tag(0x0008, 0x114C)
    SEG_PROP_SEQ_TAG = Tag(0x0062, 0x000F)

    seq_elem = ds.get(SEQ_TAG)
    if not seq_elem or seq_elem.VR != "SQ":
        raise ValueError("(0022,1627) not found or not a sequence")

    # Only process items 0 and 1
    for idx, item in enumerate(seq_elem.value[:2]):
        seg_prop_elem = item.get(SEG_PROP_SEQ_TAG)
        if not seg_prop_elem or seg_prop_elem.VR != "SQ":
            continue

        ref_seq_elem = item.get(REF_SEQ_TAG)
        if not ref_seq_elem or ref_seq_elem.VR != "SQ" or len(ref_seq_elem.value) == 0:
            continue

        ref_item = ref_seq_elem.value[0]  # put under the first (0008,114C) item

        if SEG_PROP_SEQ_TAG not in ref_item:
            ref_item.add(DataElement(SEG_PROP_SEQ_TAG, "SQ", deepcopy(seg_prop_elem.value)))

        # remove from the top-level so it's a true move
        del item[SEG_PROP_SEQ_TAG]

    files_list = [op, opt, vol, seg]

    referenced_series_seq = pydicom.Sequence()

    for i in files_list:

        dss = pydicom.dcmread(i)

        referenced_instance_seq = pydicom.Sequence()

        referenced_instance_item = pydicom.Dataset()
        referenced_instance_item.ReferencedSOPClassUID = dss[Tag(0x0008, 0x0016)].value
        referenced_instance_item.ReferencedSOPInstanceUID = dss[Tag(0x0008, 0x0018)].value
        referenced_instance_seq.append(referenced_instance_item)

        referenced_series_item = pydicom.Dataset()
        referenced_series_item.SeriesInstanceUID = dss[Tag(0x0020, 0x000E)].value
        referenced_series_item.StudyInstanceUID = dss[Tag(0x0020, 0x000D)].value
        referenced_series_item.ReferencedInstanceSequence = referenced_instance_seq
        referenced_series_seq.append(referenced_series_item)

    ds.ReferencedSeriesSequence = referenced_series_seq
    
    if "LossyImageCompressionRatio" not in ds:
        ds.LossyImageCompression = "00"

    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.basename(input_path)
    out_path = os.path.join(output_dir, f"converted_{filename}")
    
    dcmwrite(out_path, ds, write_like_original=False)

    return out_path

