from __future__ import annotations

from pathlib import Path

import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import ExplicitVRLittleEndian, generate_uid


def write_minimal_dicom(
    path: str | Path,
    *,
    sop_class_uid: str = "1.2.840.10008.5.1.4.1.1.77.1.5.1",
    include_patient_id: bool = False,
    include_source_sequence: bool = False,
) -> Path:
    """Write a small valid DICOM file for unit tests."""
    path = Path(path)
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationVersion = b"\x00\x01"
    file_meta.MediaStorageSOPClassUID = sop_class_uid
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    dataset = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    dataset.is_little_endian = True
    dataset.is_implicit_VR = False
    dataset.SOPClassUID = sop_class_uid
    dataset.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    dataset.PatientName = "Alice^Example"
    if include_patient_id:
        dataset.PatientID = "123"
    dataset.Modality = "OP"

    if include_source_sequence:
        item = Dataset()
        item.ReferencedSOPClassUID = sop_class_uid
        item.ReferencedSOPInstanceUID = generate_uid()
        dataset.SourceImageSequence = Sequence([item])

    pydicom.dcmwrite(str(path), dataset, write_like_original=False)
    return path
