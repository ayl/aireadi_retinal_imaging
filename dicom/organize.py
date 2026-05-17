import os

import pandas as pd
import pydicom
from tqdm import tqdm

import json
import re

from aireadi_retinal_imaging.dicom import utils as imaging_utils


def get_topcon_info (base_path):
    oct_folders = []

    # Walk two levels deep
    for root, dirs, files in os.walk(base_path):
        depth = root[len(base_path) :].count(os.sep)

        if depth == 2:  # exactly two levels under base_path
            # Count only .dcm files
            dcm_files = [f for f in os.listdir(root) if f.endswith(".dcm")]

            if len(dcm_files) == 3 or len(dcm_files) == 7 or len(dcm_files) == 8:
                oct_folders.append(root)

    data = []  # initialize once, before loop

    for folder in tqdm(oct_folders):

        # Get sorted .dcm files
        dcm_files = sorted([f for f in os.listdir(folder) if f.endswith(".dcm")])

        if dcm_files:
            first_file = os.path.join(folder, dcm_files[0])
            ds = pydicom.dcmread(first_file)

            # Make columns
            sop_uid_trimmed = ".".join(ds.SOPInstanceUID.split(".")[:-2]) + "."
            participant_id = imaging_utils.find_id(ds.PatientID, ds.PatientName)
            folder = folder

            # Append row
            data.append([sop_uid_trimmed, participant_id, "Maestro2", folder])

    # Create DataFrame after loop
    df = pd.DataFrame(
        data,
        columns=["sop_uid_trimmed", "participant_id", "manufacturers_model_name", "folder"],
    )
    return df


def get_difference (file1, file2):
    dcm1 = pydicom.dcmread(file1)
    dcm2 = pydicom.dcmread(file2)

    # build dictionaries: tag -> value
    dict1 = {elem.tag: elem.value for elem in dcm1 if elem.VR != "SQ"}
    dict2 = {elem.tag: elem.value for elem in dcm2 if elem.VR != "SQ"}

    # union of all tags
    all_tags = set(dict1.keys()) | set(dict2.keys())

    # compare
    for tag in sorted(all_tags):
        val1 = dict1.get(tag, "<MISSING>")
        val2 = dict2.get(tag, "<MISSING>")
        if val1 != val2:
            name = dcm1.get(tag).name if tag in dcm1 else dcm2.get(tag).name
            print(f"{tag} ({name}):")
            print(f"  dcm1: {val1}")
            print(f"  dcm2: {val2}")
            print("-" * 40)

import hashlib

import pydicom
from pydicom.datadict import dictionary_description
from pydicom.sequence import Sequence
from pydicom.tag import Tag
from pydicom.valuerep import PersonName

try:
    import numpy as np
    from pydicom.pixel_data_handlers.util import apply_modality_lut
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


def format_tag(tag):
    t = Tag(tag)
    return f"({t.group:04X},{t.element:04X})"


def elem_name(ds, tag):
    try:
        if tag in ds:
            return ds[tag].name
    except Exception:
        pass
    return dictionary_description(Tag(tag)) or "Unknown"



def hash_bytes(b):
    if b is None:
        return None
    return hashlib.md5(b).hexdigest()


def normalize_value(v):
    if isinstance(v, bytes):
        return f"<{len(v)} bytes, md5={hash_bytes(v)}>"
    if isinstance(v, PersonName):
        return str(v)
    if isinstance(v, (list, tuple)) and not isinstance(v, Sequence):
        return tuple(normalize_value(x) for x in v)
    return v


def compare_values(val1, val2):
    return normalize_value(val1) == normalize_value(val2)

def compare_pixel_data(ds1, ds2, path):
    """Special handling for PixelData (7FE0,0010)."""
    v1 = ds1.get(Tag(0x7FE0, 0x0010))
    v2 = ds2.get(Tag(0x7FE0, 0x0010))

    if v1 is None and v2 is None:
        return
    if v1 is None or v2 is None:
        print(f"{path}(7FE0,0010) PixelData:")
        print(f"  dcm1: {normalize_value(v1.value) if v1 else '<MISSING>'}")
        print(f"  dcm2: {normalize_value(v2.value) if v2 else '<MISSING>'}")
        print("-" * 40)
        return

    # Compare byte length and hash
    b1, b2 = v1.value, v2.value
    if b1 != b2:
        print(f"{path}(7FE0,0010) PixelData differs:")
        print(f"  dcm1: <{len(b1)} bytes, md5={hash_bytes(b1)}>")
        print(f"  dcm2: <{len(b2)} bytes, md5={hash_bytes(b2)}>")
        if NUMPY_AVAILABLE:
            try:
                arr1 = apply_modality_lut(ds1.pixel_array, ds1)
                arr2 = apply_modality_lut(ds2.pixel_array, ds2)
                if arr1.shape != arr2.shape:
                    print(f"  Array shapes differ: {arr1.shape} vs {arr2.shape}")
                else:
                    diff = arr1.astype(np.int64) - arr2.astype(np.int64)
                    n_diff = np.count_nonzero(diff)
                    print(f"  Arrays differ in {n_diff} pixels")
                    print(f"  Min/Max/Mean difference: "
                          f"{diff.min()} / {diff.max()} / {diff.mean():.3f}")
            except Exception as e:
                print(f"  (Could not decode PixelData: {e})")
        print("-" * 40)


def get_difference_pixel_nested(file1, file2):
    dcm1 = pydicom.dcmread(file1)
    dcm2 = pydicom.dcmread(file2)

    printed = {"diff": False}  # use dict to allow mutation inside nested function

    def diff_datasets(ds1, ds2, path=""):
        tags = set(ds1.keys()) | set(ds2.keys())

        for tag in sorted(tags):
            in1 = tag in ds1
            in2 = tag in ds2

            # Special PixelData handling
            if tag == Tag(0x7FE0, 0x0010):
                changed = compare_pixel_data(ds1, ds2, path)
                if changed:
                    printed["diff"] = True
                continue

            # Missing cases
            if in1 and not in2:
                printed["diff"] = True
                print(f"{path}{format_tag(tag)} {elem_name(ds1, tag)}:")
                print(f"  dcm1: {normalize_value(ds1[tag].value)}")
                print(f"  dcm2: <MISSING>")
                print("-" * 40)
                continue
            if in2 and not in1:
                printed["diff"] = True
                print(f"{path}{format_tag(tag)} {elem_name(ds2, tag)}:")
                print(f"  dcm1: <MISSING>")
                print(f"  dcm2: {normalize_value(ds2[tag].value)}")
                print("-" * 40)
                continue

            # Both present
            elem1 = ds1[tag]
            elem2 = ds2[tag]

            # Sequences
            if elem1.VR == "SQ":
                seq1, seq2 = elem1.value, elem2.value
                if len(seq1) != len(seq2):
                    printed["diff"] = True
                    print(f"{path}{format_tag(tag)} {elem_name(ds1, tag)} (SQ) length differs:")
                    print(f"  dcm1: {len(seq1)} item(s)")
                    print(f"  dcm2: {len(seq2)} item(s)")
                    print("-" * 40)
                max_len = max(len(seq1), len(seq2))
                for i in range(max_len):
                    item_path = f"{path}{format_tag(tag)} {elem_name(ds1, tag)}[{i}]/"
                    if i >= len(seq1):
                        printed["diff"] = True
                        print(f"{item_path} <MISSING ITEM IN dcm1>")
                        print("-" * 40)
                        continue
                    if i >= len(seq2):
                        printed["diff"] = True
                        print(f"{item_path} <MISSING ITEM IN dcm2>")
                        print("-" * 40)
                        continue
                    diff_datasets(seq1[i], seq2[i], item_path)
                continue

            # Regular elements
            if not compare_values(elem1.value, elem2.value):
                printed["diff"] = True
                print(f"{path}{format_tag(tag)} {elem_name(ds1, tag)}:")
                print(f"  dcm1: {normalize_value(elem1.value)}")
                print(f"  dcm2: {normalize_value(elem2.value)}")
                print("-" * 40)

    def compare_pixel_data(ds1, ds2, path):
        v1 = ds1.get(Tag(0x7FE0, 0x0010))
        v2 = ds2.get(Tag(0x7FE0, 0x0010))
        if v1 is None and v2 is None:
            return False
        if v1 is None or v2 is None or v1.value != v2.value:
            print(f"{path}(7FE0,0010) PixelData differs "
                  f"md5={hash_bytes(v1.value) if v1 else None} vs {hash_bytes(v2.value) if v2 else None}")
            print("-" * 40)
            return True
        return False

    diff_datasets(dcm1, dcm2)

    if not printed["diff"]:
        print("Same ✅")


import os


def get_all_paths(root):
    """
    Recursively collect all file and folder paths (relative to root).
    """
    all_paths = set()
    for dirpath, dirnames, filenames in os.walk(root):
        # Normalize path relative to root
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        # Add folders
        for d in dirnames:
            all_paths.add(os.path.join(rel_dir, d))
        # Add files
        for f in filenames:
            all_paths.add(os.path.join(rel_dir, f))
    return all_paths

def compare_folders(folder1, folder2):
    set1 = get_all_paths(folder1)
    set2 = get_all_paths(folder2)

    only_in_1 = set1 - set2
    only_in_2 = set2 - set1

    if not only_in_1 and not only_in_2:
        print("✅ Both folders have the same structure and file/folder names.")
    else:
        if only_in_1:
            print(f"📂 Present only in {folder1}:")
            for item in sorted(only_in_1):
                print("  ", item)
        if only_in_2:
            print(f"\n📂 Present only in {folder2}:")
            for item in sorted(only_in_2):
                print("  ", item)


################################################
from collections import Counter


def same_number_tags(files):

    tag_counts = []

    for f in files:
        try:
            ds = pydicom.dcmread(f, stop_before_pixels=True)  # metadata only
            count = len(ds.keys())  # number of data elements (tags)
            tag_counts.append(count)
        except Exception as e:
            print(f"❌ Error reading {f}: {e}")

    # summarize
    counter = Counter(tag_counts)
    print("Tag counts frequency:")
    for count, freq in counter.items():
        print(f"  {count} tags → {freq} files")

    if len(counter) == 1:
        print("\n✅ All files have the same number of tags.")
    else:
        print("\n⚠️ Files differ in number of tags.")

import pydicom


def check_sopclassuid(file_list):
    sop_uids = {}

    for f in tqdm(file_list):
        try:
            ds = pydicom.dcmread(f, stop_before_pixels=True)  # metadata only
            sop_uid = getattr(ds, "SOPClassUID", None)
            sop_uids[f] = str(sop_uid) if sop_uid else None
        except Exception as e:
            sop_uids[f] = f"Error: {e}"

    # Collect unique UIDs
    unique_uids = set(v for v in sop_uids.values() if v and not str(v).startswith("Error"))

    print("\nSOPClassUIDs found:")
    # for f, uid in sop_uids.items():
    #     print(f"  {f}: {uid}")

    if len(unique_uids) == 1:
        print("\n✅ All files share the same SOPClassUID:", unique_uids.pop())
    else:
        print("\n⚠️ Different SOPClassUIDs detected:")
        for uid in unique_uids:
            print("  ", uid)

    return sop_uids

import os


def compare_subfolders(folder_a, folder_b):
    # 1. Get basenames of all subfolders in A
    subfolders_a = [d for d in os.listdir(folder_a) if os.path.isdir(os.path.join(folder_a, d))]

    print("Subfolders in A:", subfolders_a)

    for sub_a in subfolders_a:
        path_a = os.path.join(folder_a, sub_a)
        path_b = os.path.join(folder_b, sub_a)  # matching subfolder in B

        if not os.path.exists(path_b):
            print(f"⚠️ No matching subfolder for {sub_a} in B")
            continue

        # 2. Collect file names from each subfolder (ignore hidden/system files)
        files_a = {f for f in os.listdir(path_a) if os.path.isfile(os.path.join(path_a, f)) and not f.startswith("._")}
        files_b = {f for f in os.listdir(path_b) if os.path.isfile(os.path.join(path_b, f)) and not f.startswith("._")}

        # 3. Find intersection (same file names in both)
        common_files = files_a & files_b

        if common_files:
            print(f"✅ Common files in subfolder '{sub_a}': {sorted(common_files)}")
        else:
            print(f"❌ No common files in subfolder '{sub_a}'")
            
# def get_dcm_files(folder_path):
#     dcm_files = []
#     for root, _, files in os.walk(folder_path):
#         for file in files:
#             if file.lower().endswith(".dcm"):  # case-insensitive match
#                 dcm_files.append(os.path.join(root, file))
#     return dcm_files

def get_dcm_files(folder_path):
    dcm_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            # exclude hidden/system files and ensure .dcm extension
            if not file.startswith(".") and file.lower().endswith(".dcm"):
                dcm_files.append(os.path.join(root, file))
    return dcm_files

def get_json_files(folder_path):
    dcm_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            # exclude hidden/system files and ensure .dcm extension
            if not file.startswith(".") and file.lower().endswith(".json"):
                dcm_files.append(os.path.join(root, file))
    return dcm_files

def clean_filename(filename):
    """
    Removes all underscores and periods from a filename.

    Args:
    - filename (str): The filename to clean.

    Returns:
    - str: The cleaned filename with underscores and periods removed.
    """
    return filename.replace("_", "").replace(".", "")

import shutil


def merge_folders_filter_id_files(patientid_csv, sources, destination, remove_txt):
    """
    Merge files from the source directories into the destination directory
    based on a list of unique study IDs and an optional list of files to exclude by base name.

    Args:
    - patientid_csv (str): Path to the CSV file containing patient IDs.
    - sources (list): List of source directories.
    - destination (str): Path to the destination directory.
    - remove_txt (str): Path to the text file that contains the list of base filenames (without extension)
                        that need to be excluded.
    """

    # Read the files to be removed from the remove_txt file
    with open(remove_txt, "r", encoding="utf-8") as file:
        # Read all lines and strip newline characters
        files_to_remove = [line.strip() for line in file]

    # Read the CSV and get the list of unique study IDs
    unique_study_ids_list = pd.read_csv(patientid_csv)["Participant ID"].astype(str).unique().tolist()

    # Convert the files_to_remove list to a set for faster lookup
    files_to_remove_set = set(files_to_remove)
    print("folder numbers:")
    print(len(sources))

    removed_count = 0

    for source in sources:
        print(source)
        for root, dirs, files in os.walk(source):
            relative_path = os.path.relpath(root, source)
            dest_path = os.path.join(destination, relative_path)

            # Collect valid files (those matching the IDs and not in the removal list)
            valid_files = []

            for file in files:
                if not file.startswith("._"):
                    file_id = file.split("_")[0]

                    # Get the base name of the file (without the extension)
                    base_file_name = os.path.splitext(file)[0]
                    cleaned_base_file_name = clean_filename(base_file_name)

                    # Check if any cleaned element in files_to_remove_set is part of the cleaned base file name
                    should_remove = any(
                        clean_filename(item) in cleaned_base_file_name
                        for item in files_to_remove_set
                    )

                    if file_id in unique_study_ids_list and not should_remove:
                        valid_files.append(file)
                    else:
                        if should_remove:
                            removed_count += 1 
                            print(
                                f"File {file} is in the removal list after cleaning. Skipping..."
                            )
                        else:
                            print(
                                f"File {file} not in the list of study IDs. Skipping..."
                            )

            # Only create the destination folder if there are valid files to copy
            if valid_files:
                os.makedirs(
                    dest_path, exist_ok=True
                )  # Create the folder if it doesn't exist

                # Copy over the valid files
                for file in valid_files:
                    src_file = os.path.join(root, file)
                    dest_file = os.path.join(dest_path, file)

                    if not os.path.exists(dest_file):
                        shutil.copy2(src_file, dest_file)
                        # print(f"Copied {src_file} to {dest_file}")
                    else:
                        print(f"File {dest_file} already exists. Skipping...")

    print(removed_count)
    print("removed")
    return removed_count


def get_patient_ids_from_final_output(folder_path):
    """
    Given a folder, return a list of patient IDs (subfolder basenames).
    
    Args:
        folder_path (str): Path to the main folder.
    
    Returns:
        list: List of patient IDs (subfolder names).
    """
    patient_ids = []
    for entry in os.scandir(folder_path):
        if entry.is_dir():
            patient_ids.append(os.path.basename(entry.path))
    return patient_ids

only_year2_list = []
total_list = []
only_year3_list = []

def compare_lists(list1, list2):
    """
    Compare two lists and return three lists as strings:
    1. Overlap (common elements)
    2. Only in list1
    3. Only in list2
    """
    # Convert everything to string
    set1, set2 = set(map(str, list1)), set(map(str, list2))

    overlap = sorted(list(set1 & set2))       # Intersection
    only_in_list1 = sorted(list(set1 - set2)) # Difference
    only_in_list2 = sorted(list(set2 - set1)) # Difference

    return overlap, only_in_list1, only_in_list2

import os


def list_subfolders(path):
    return [
        name for name in os.listdir(path)
        if os.path.isdir(os.path.join(path, name))
    ]
import os

MAPPING = {
    "maestro2_3d_wide": "maestro2_3d_wide_oct",
    "maestro2_macula_6x6": "maestro2_macula_6x6_octa",
    "maestro2_3d_macula": "maestro2_3d_macula_oct",
    "triton_3d_radial": "triton_3d_radial_oct",
    "triton_macula_6x6": "triton_macula_6x6_octa",
    "triton_macula_12x12": "triton_macula_12x12_octa",
    "spectralis_onh_rc_hr_oct": "spectralis_onh_rc_hr_oct_oct",
    "spectralis_onh_rc_hr_ir": "spectralis_onh_rc_hr_oct_ir",
    "spectralis_ppol_mac_hr_oct": "spectralis_ppol_mac_hr_oct_oct",
    "spectralis_ppol_mac_hr_ir": "spectralis_ppol_mac_hr_oct_ir",
}

def apply_mapping_to_basename(basename, mapping):
    new_name = basename
    for old in sorted(mapping.keys(), key=len, reverse=True):
        if old in new_name:
            new_name = new_name.replace(old, mapping[old])
    return new_name


def check_discrepancies(folder_a, folder_b, mapping=MAPPING):
    subfolders_a = [
        d for d in os.listdir(folder_a)
        if os.path.isdir(os.path.join(folder_a, d))
    ]
    print(len(subfolders_a))

    for sub in subfolders_a:
        path_a = os.path.join(folder_a, sub)
        path_b = os.path.join(folder_b, sub)

        if not os.path.exists(path_b) or not os.path.isdir(path_b):
            print(f"⚠️ No matching subfolder in B for '{sub}'")
            continue

        # Collect files
        files_a = [
            f for f in os.listdir(path_a)
            if os.path.isfile(os.path.join(path_a, f)) and not f.startswith("._")
        ]
        files_b = {
            f for f in os.listdir(path_b)
            if os.path.isfile(os.path.join(path_b, f)) and not f.startswith("._")
        }

        # Apply mapping to A
        mapped_a = []
        for f in files_a:
            base, ext = os.path.splitext(f)
            new_base = apply_mapping_to_basename(base, mapping)
            mapped_a.append(new_base + ext)

        mapped_a_set = set(mapped_a)

        # Check discrepancies
        if len(mapped_a_set) != len(files_b) or mapped_a_set != files_b:
            print(f"❌ Discrepancy in subfolder '{sub}':")
            if len(mapped_a_set) != len(files_b):
                print(f"   • Different file counts (A={len(mapped_a_set)}, B={len(files_b)})")
            else:
                print(f"   • Same count but different names")

import os


def save_dcm_basenames_to_txt(folder, output_txt):
    """
    Read all files in a folder, collect basenames (without .dcm),
    and save them to a text file.
    """
    # Collect only .dcm files
    files = [
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f)) and f.lower().endswith(".dcm")
    ]

    # Remove .dcm extension
    basenames = [os.path.splitext(f)[0] for f in files]

    # Write to txt file
    with open(output_txt, "w", encoding="utf-8") as out:
        for name in basenames:
            out.write(name + "\n")

    print(f"✅ Saved {len(basenames)} basenames to {output_txt}")


def get_dcm_basenames(folder):
    """
    Read all files in a folder, collect basenames (without .dcm),
    and save them to a text file.
    """
    # Collect only .dcm files
    files = [
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f)) and f.lower().endswith(".dcm")
    ]

    # Remove .dcm extension
    basenames = [os.path.splitext(f)[0] for f in files]

    for b in basenames:
        print(b)

import numpy as np
from PIL import Image
from pydicom.pixel_data_handlers.util import convert_color_space


def file_to_jpg(file, jpg_output):
    os.makedirs(jpg_output, exist_ok=True)
    try:
        ds = pydicom.dcmread(file)
        dimension = len(ds.pixel_array.shape)

        if dimension == 3:
            arr = ds.pixel_array
            # arr = convert_color_space(arr, "YBR_FULL", "RGB")
            img = Image.fromarray(arr)
            img.save(
                os.path.join(jpg_output, os.path.basename(file) + ".jpg"),
                format="JPEG",
                quality=90  # adjust quality (default 75, higher = bigger file, better quality)
            )
        elif dimension == 2:
            arr = ds.pixel_array
            img = Image.fromarray(arr)
            img.save(
                os.path.join(jpg_output, os.path.basename(file) + ".jpg"),
                format="JPEG",
                quality=90
            )
        else:
            print("Error: Image dimension not supported")
            return
    except Exception as e:
        print("Error reading file:", file, "| Exception:", e)
        return

import pydicom


# Example: maestro2 is your list of DICOM file paths
def check_unique_sopclassuids(file_list):
    sop_uids = []
    
    for file in tqdm(file_list):
        dcm = pydicom.dcmread(file, stop_before_pixels=True)  # faster, no pixel data
        sop_uids.append(dcm.SOPClassUID)
    
    unique_uids = set(sop_uids)
    
    print("Total files:", len(sop_uids))
    print("Unique SOPClassUIDs:", len(unique_uids))
    print("Unique values:")
    for uid in unique_uids:
        print("  ", uid)


import os
from hashlib import sha256

import pydicom
from tqdm import tqdm

# def _schema_signature(ds):
#     """Return a hashable structural signature of a dataset (tags + nested tags)."""
#     def walk(dataset):
#         entries = []
#         for elem in dataset:
#             if elem.VR == "SQ":  # recurse into sequences
#                 item_sigs = tuple(walk(item) for item in (elem.value or []))
#                 entries.append((int(elem.tag), "SQ", item_sigs))
#             else:
#                 entries.append((int(elem.tag), elem.VR))
#         return tuple(sorted(entries))
#     return sha256(repr(walk(ds)).encode("utf-8")).hexdigest()

# def all_same_structure(dcm_files):
#     """Check if all DICOMs have the same tag/nested-tag structure."""
#     sig_map = {}
#     for file in tqdm(dcm_files):
#         try:
#             ds = pydicom.dcmread(file, stop_before_pixels=True)
#             sig = _schema_signature(ds)
#             sig_map.setdefault(sig, []).append(file)
#         except Exception as e:
#             sig_map.setdefault(f"ERROR:{e}", []).append(file)

#     if len(sig_map) == 1:
#         return True
#     else:
#         print("⚠️ Different structures found:")
#         for sig, files in sig_map.items():
#             print(f"\nGroup {sig[:10]}... ({len(files)} files)")
#             for f in files:
#                 print("   ", f)
#         return False


def _schema_signature(ds):
    """Return a hashable structural signature of a dataset (tags + nested tags)."""
    def walk(dataset):
        entries = []
        for elem in dataset:
            if elem.VR == "SQ":  # recurse into sequences
                item_sigs = tuple(walk(item) for item in (elem.value or []))
                entries.append((int(elem.tag), "SQ", item_sigs))
            else:
                entries.append((int(elem.tag), elem.VR))
        return tuple(sorted(entries))
    return sha256(repr(walk(ds)).encode("utf-8")).hexdigest()

def all_same_structure(dcm_files, sample_per_group=20):
    """
    Check if all DICOMs have the same tag/nested-tag structure.
    If not, print the group count and up to `sample_per_group` example files per group.
    Returns True if all same, else False.
    """
    sig_map = {}
    for file in tqdm(dcm_files):
        try:
            ds = pydicom.dcmread(file, stop_before_pixels=True)
            sig = _schema_signature(ds)
            sig_map.setdefault(sig, []).append(file)
        except Exception as e:
            sig_map.setdefault(f"ERROR:{e}", []).append(file)

    if len(sig_map) == 1:
        return True

    print("⚠️ Different structures found:")
    for sig, files in sig_map.items():
        files_sorted = sorted(files)
        examples = files_sorted[:sample_per_group]
        print(f"\nGroup {sig[:15]}... — {len(files)} files (showing {len(examples)}):")
        for f in examples:
            print("   ", f)

    return False

from typing import List, Tuple

import pydicom
from pydicom.datadict import keyword_for_tag
from pydicom.tag import Tag


def _tag_str(t: int) -> str:
    """Readable tag like (0008,103E) SeriesDescription."""
    tg = Tag(t)
    kw = keyword_for_tag(tg) or ""
    return f"({tg.group:04X},{tg.element:04X})" + (f" {kw}" if kw else "")

def _is_private(tag_int: int) -> bool:
    """Private tags have odd group number."""
    return ((tag_int >> 16) & 0xFFFF) % 2 == 1

def _ds_children(ds: pydicom.dataset.Dataset, include_private_tags: bool) -> dict:
    """Map int(tag) -> element (one per tag at this level)."""
    out = {}
    for elem in ds:
        ti = int(elem.tag)
        if not include_private_tags and _is_private(ti):
            continue
        out[ti] = elem
    return out

def _diff_ds(
    ds1: pydicom.dataset.Dataset,
    ds2: pydicom.dataset.Dataset,
    path: str,
    include_vr: bool,
    include_private_tags: bool,
    diffs: List[str],
):
    m1 = _ds_children(ds1, include_private_tags)
    m2 = _ds_children(ds2, include_private_tags)

    # Missing / extra tags
    only1 = sorted(set(m1.keys()) - set(m2.keys()))
    only2 = sorted(set(m2.keys()) - set(m1.keys()))
    for t in only1:
        diffs.append(f"{path}{_tag_str(t)} present only in A")
    for t in only2:
        diffs.append(f"{path}{_tag_str(t)} present only in B")

    # Compare common tags
    for t in sorted(set(m1.keys()) & set(m2.keys())):
        e1, e2 = m1[t], m2[t]
        p = f"{path}{_tag_str(t)}"

        # VR difference (structure-level)
        if include_vr and e1.VR != e2.VR:
            diffs.append(f"{p} VR differs: A={e1.VR}, B={e2.VR}")

        # Recurse for sequences
        if e1.VR == "SQ" and e2.VR == "SQ":
            items1 = e1.value or []
            items2 = e2.value or []
            if len(items1) != len(items2):
                diffs.append(f"{p} sequence length differs: A={len(items1)}, B={len(items2)}")
            # Compare per-index up to min length
            for i in range(min(len(items1), len(items2))):
                _diff_ds(items1[i], items2[i], path=f"{p}[{i}]/", include_vr=include_vr,
                         include_private_tags=include_private_tags, diffs=diffs)

def diff_dicom_structures(
    a_file: str,
    b_file: str,
    *,
    include_vr: bool = True,
    include_private_tags: bool = True,
    stop_before_pixels: bool = True,
) -> List[str]:
    """
    Return a list of human-readable differences in structure (tags + nesting).
    Values are ignored.
    """
    ds1 = pydicom.dcmread(a_file, stop_before_pixels=stop_before_pixels)
    ds2 = pydicom.dcmread(b_file, stop_before_pixels=stop_before_pixels)
    diffs: List[str] = []
    _diff_ds(ds1, ds2, path="", include_vr=include_vr,
             include_private_tags=include_private_tags, diffs=diffs)
    return diffs




# def _schema_signature(ds):
#     """Return a hashable structural signature of a dataset (tags + nested tags)."""
#     def walk(dataset):
#         entries = []
#         for elem in dataset:
#             if elem.VR == "SQ":  # recurse into sequences
#                 item_sigs = tuple(walk(item) for item in (elem.value or []))
#                 entries.append((int(elem.tag), "SQ", item_sigs))
#             else:
#                 entries.append((int(elem.tag), elem.VR))
#         return tuple(sorted(entries))
#     return sha256(repr(walk(ds)).encode("utf-8")).hexdigest()

# def all_same_structure(dcm_files):
#     """
#     Check if all DICOMs have the same tag/nested-tag structure.
#     Prints only the count of files per structure group and one representative file.
#     Returns True if all same, else False.
#     """
#     sig_map = {}
#     for file in tqdm(dcm_files):
#         try:
#             ds = pydicom.dcmread(file, stop_before_pixels=True)
#             sig = _schema_signature(ds)
#             sig_map.setdefault(sig, []).append(file)
#         except Exception as e:
#             sig_map.setdefault(f"ERROR:{e}", []).append(file)

#     if len(sig_map) == 1:
#         return True

#     print("⚠️ Different structures found:")
#     # Print a compact summary: count + one representative per group
#     for sig, files in sig_map.items():
#         # pick a stable representative (alphabetically first path)
#         rep = min(files) if files else "(no example)"
#         print(f"- Group {sig[:10]}...: {len(files)} files | example: {rep}")

#     return False


# Usage
# check_unique_sopclassuids(maestro2)

# def compare_after_mapping(folder_a, folder_b, mapping=MAPPING):
#     # Get subfolders of A (by basename)
#     subfolders_a = [
#         d for d in os.listdir(folder_a)
#         if os.path.isdir(os.path.join(folder_a, d))
#     ]

#     total_mapped = 0
#     total_matches = 0

#     for sub in subfolders_a:
#         path_a = os.path.join(folder_a, sub)
#         path_b = os.path.join(folder_b, sub)  # expect same-named subfolder in B

#         if not os.path.exists(path_b) or not os.path.isdir(path_b):
#             print(f"⚠️ No matching subfolder in B for '{sub}'")
#             continue

#         # Collect files from A and B (ignore hidden/system files like ._foo)
#         files_a = [
#             f for f in os.listdir(path_a)
#             if os.path.isfile(os.path.join(path_a, f)) and not f.startswith("._")
#         ]
#         files_b = {
#             f for f in os.listdir(path_b)
#             if os.path.isfile(os.path.join(path_b, f)) and not f.startswith("._")
#         }

#         # Map A filenames using the mapping on the basename only
#         mapped_a = []
#         mapped_count_here = 0

#         for f in files_a:
#             base, ext = os.path.splitext(f)
#             new_base, changed = apply_mapping_to_basename(base, mapping)
#             if changed:
#                 mapped_count_here += 1
#             new_name = new_base + ext  # put extension back
#             mapped_a.append(new_name)

#         total_mapped += mapped_count_here

#         # Compare mapped A vs raw B
#         mapped_a_set = set(mapped_a)
#         common = mapped_a_set & files_b
#         only_in_a = sorted(mapped_a_set - files_b)
#         only_in_b = sorted(files_b - mapped_a_set)

#         total_matches += len(common)

#         print(f"\n📁 Subfolder: {sub}")
#         print(f"  • Files in A (mapped): {len(mapped_a_set)}")
#         print(f"  • Files in B:          {len(files_b)}")
#         print(f"  • Lines mapped here:   {mapped_count_here}")
#         if common:
#             print(f"  ✅ Matches ({len(common)}): {sorted(common)[:10]}{' ...' if len(common) > 10 else ''}")
#         else:
#             print("  ❌ No filename matches after mapping.")

#         # Optional detail: show some differences for debugging
#         if only_in_a:
#             print(f"  ↪ Only in A (after mapping), e.g.: {only_in_a[:5]}{' ...' if len(only_in_a) > 5 else ''}")
#         if only_in_b:
#             print(f"  ↩ Only in B, e.g.: {only_in_b[:5]}{' ...' if len(only_in_b) > 5 else ''}")

#     print("\n==== Summary ====")
#     print(f"Total renamed (A-side mapping applied): {total_mapped}")
#     print(f"Total matches (mapped A vs B):          {total_matches}")

# # Example usage:
# # folder_a = "/path/to/folder_a"
# # folder_b = "/path/to/folder_b"
# # compare_after_mapping(folder_a, folder_b)
# # compare_after_mapping(folder_a, folder_b)
# # compare_after_mapping(folder_a, folder_b)
# # compare_after_mapping(folder_a, folder_b)
# # compare_after_mapping(folder_a, folder_b)
# # compare_after_mapping(folder_a, folder_b)
# # compare_after_mapping(folder_a, folder_b)
# # compare_after_mapping(folder_a, folder_b)
# # compare_after_mapping(folder_a, folder_b)
# # compare_after_mapping(folder_a, folder_b)
# # compare_after_mapping(folder_a, folder_b)
# # compare_after_mapping(folder_a, folder_b)
# # compare_after_mapping(folder_a, folder_b)
