import argparse
import csv
import os
import shutil
from datetime import datetime

from tqdm import tqdm

from aireadi_retinal_imaging.dicom import utils as imaging_utils
import pydicom
from aireadi_retinal_imaging.devices.topcon.root import Maestro2_Triton
from pydicom.datadict import DicomDictionary, keyword_dict
from pydicom.dataset import Dataset

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

def write_log(log_file_path, input_path, status, error_message=""):
    """
    Appends a log entry to a specified CSV file.
    Creates the file and writes a header if it doesn't exist.

    Args:
        log_file_path (str): The full path to the log file.
        input_path (str): The input file or folder being processed.
        status (str): The result of the operation (e.g., "SUCCESS", "FAILURE").
        error_message (str, optional): The error message if the status is "FAILURE".
    """
    # Check if the log file needs a header
    file_exists = os.path.exists(log_file_path)

    # 'a' mode is for appending, newline='' prevents extra blank rows
    with open(log_file_path, 'a', newline='') as csvfile:
        fieldnames = ['Timestamp', 'Input', 'Status', 'ErrorMessage']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()  # Write the header row

        writer.writerow({
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Input': input_path,
            'Status': status,
            'ErrorMessage': error_message
        })

def main():
    """
    Main function to parse command-line arguments and run the Topcon processing pipeline.
    """
    # 1. --- Argument Parsing ---
    # This section sets up how the script receives instructions from the command line.
    parser = argparse.ArgumentParser(
        description="A script to process Topcon imaging data from raw files to structured DICOMs."
    )

    parser.add_argument(
        "-i", "--input-folder",
        dest="input_folder",
        required=True,
        help="Path to the root input folder containing the initial data.",
        metavar="PATH"
    )

    parser.add_argument(
        "-o", "--output-folder",
        dest="output_folder",
        required=True,
        help="Path to the root folder where all processed steps and outputs will be saved.",
        metavar="PATH"
    )


    args = parser.parse_args()

    # Assign the parsed arguments to variables
    input_folder = args.input_folder
    output_folder = args.output_folder

    print("--- Starting Topcon Processing Pipeline ---")
    print(f"Input Folder: {input_folder}")
    print(f"Output Folder: {output_folder}")
    print("-----------------------------------------")

    # 2. --- Setup ---
    # Initialize your custom class
    maestro2_triton_instance = Maestro2_Triton()

    # Define paths for each step within the main output folder
    step2_folder = os.path.join(output_folder, "step2_organized")
    step3_folder = os.path.join(output_folder, "step3_converted_dicom")
    step4_folder = os.path.join(output_folder, "step4_final_structure")
    metadata_folder = os.path.join(output_folder, "metadata")
    logs_folder = os.path.join(output_folder, "logs") 

    # Create the main output folder structure
    folders_to_recreate = [step2_folder, step3_folder, step4_folder, metadata_folder, logs_folder]

    print("Resetting output directories...")
    for folder in folders_to_recreate:
        # If the folder exists, delete it and all its contents
        if os.path.exists(folder):
            shutil.rmtree(folder)
        # Create the folder fresh
        os.makedirs(folder)
    
    print("Directory structure is ready.")


    # 3. --- Processing Pipeline ---

    # Step 1: Organize
    print("\nStep: Organizing files...")
    step2_log_path = os.path.join(logs_folder, "step2_organized_log.csv")
    batch_folders = imaging_utils.list_subfolders(input_folder)
    
    print(batch_folders)

    for batch_folder in tqdm(batch_folders, desc="Organizing Batch Folders"):
  
        subfolders = imaging_utils.list_subfolders(batch_folder)

        for folder in tqdm(subfolders, desc="Organizing Folders"):

            try:
                organize_result = maestro2_triton_instance.organize(folder, step2_folder)
                # write_log(step2_log_path, folder, "SUCCESS")

            except Exception as e:
                # If an error occurs, log it and continue to the next folder
                print(f"\nERROR organizing {folder}: {e}")
                write_log(step2_log_path, folder, "FAILURE", str(e))

    # Step 2: Convert to DICOM
    print("\nStep: Converting to DICOM format...")
    step3_log_path = os.path.join(logs_folder, "step3_convert_log.csv")
    folders = imaging_utils.list_subfolders(step2_folder)
    
    protocols = [
        "maestro2_3d_macula_oct",
        "maestro2_3d_wide_oct",
        "maestro2_mac_6x6_octa",
        "triton_3d_radial_oct",
        "triton_macula_6x6_octa",
        "triton_macula_12x12_octa",
    ]

    for protocol in protocols:
        output = f"{step3_folder}/{protocol}"
        if not os.path.exists(output):
            os.makedirs(output)

        folders = imaging_utils.list_subfolders(f"{step2_folder}/{protocol}")

        for folder in tqdm(folders, desc="Converting"):
    
            try:
                convert_result = maestro2_triton_instance.convert(folder, output)
                # write_log(step3_log_path, folder, "SUCCESS")
            except Exception as e:
                 # If an error occurs, log it and continue to the next folder
                print(f"\nERROR converting {folder}: {e}")
                write_log(step3_log_path, folder, "FAILURE", str(e))
                


    # Step 3: Final Structure and Metadata Extraction
    print("\nStep: Arranging final structure and extracting metadata...")
    step4_log_path = os.path.join(logs_folder, "step4_final_log.csv")
    folders = imaging_utils.list_subfolders(step3_folder)


    for folder in folders:
        filelist = imaging_utils.get_filtered_file_names(folder)

        for file in tqdm(filelist):
            try:
                full_file_path = imaging_utils.format_file(file, step4_folder)
                if full_file_path:
                    metadata_result = maestro2_triton_instance.metadata(
                        full_file_path, metadata_folder
                    )
                    # write_log(step4_log_path, file, "SUCCESS")
                    
            except Exception as e:
                # If an error occurs, log it and continue to the next folder
                print(f"\nERROR finalizing {file}: {e}")
                write_log(step4_log_path, file, "FAILURE", str(e))




if __name__ == "__main__":
    # This block ensures that the main() function is called only when
    # the script is executed directly from the terminal.
    main()
