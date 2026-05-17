import argparse
import csv
import os
import shutil
from datetime import datetime

from tqdm import tqdm

from ophthalmic_dicom_compliance.dicom import utils as imaging_utils
import pydicom
from ophthalmic_dicom_compliance.devices.spectralis.root import Spectralis


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
    Main function to parse command-line arguments and run the Spectralis processing pipeline.
    """
    # 1. --- Argument Parsing ---
    # This section sets up how the script receives instructions from the command line.
    parser = argparse.ArgumentParser(
        description="A script to process Spectralis imaging data from raw files to structured DICOMs."
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

    print("--- Starting Spectralis Processing Pipeline ---")
    print(f"Input Folder: {input_folder}")
    print(f"Output Folder: {output_folder}")
    print("-----------------------------------------")

    # 2. --- Setup ---
    # Initialize your custom class
    spectralis_instance = Spectralis()

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
    folders = imaging_utils.list_subfolders(input_folder)
    for folder in tqdm(folders, desc="Organizing Folders"):

        filtered_list = imaging_utils.spectralis_get_filtered_file_names(folder)

        for file in tqdm(filtered_list, desc="Organizing Files"):

            try:
                organize_result = spectralis_instance.organize(file, step2_folder)
                # write_log(step2_log_path, file, "SUCCESS")

            except Exception as e:
                # If an error occurs, log it and continue to the next folder
                print(f"\nERROR organizing {file}: {e}")
                write_log(step2_log_path, file, "FAILURE", str(e))

    # Step 2: Convert to DICOM
    print("\nStep: Converting to DICOM format...")
    step3_log_path = os.path.join(logs_folder, "step3_convert_log.csv")
    folders = imaging_utils.list_subfolders(step2_folder)
    protocols = [
    "spectralis_onh_rc_hr_oct",
    "spectralis_onh_rc_hr_retinal_photography",
    "spectralis_ppol_mac_hr_oct",
    "spectralis_ppol_mac_hr_oct_small",
    "spectralis_ppol_mac_hr_retinal_photography",
    "spectralis_ppol_mac_hr_retinal_photography_small",
]

    for protocol in protocols:
        output = f"{step3_folder}/{protocol}"
        if not os.path.exists(output):
            os.makedirs(output)

        files = imaging_utils.get_filtered_file_names(f"{step2_folder}/{protocol}")

        for file in tqdm(files, desc="Converting"):
            try:
                convert_result = spectralis_instance.convert(file, output)
                # write_log(step3_log_path, file, "SUCCESS")
            except Exception as e:
                 # If an error occurs, log it and continue to the next folder
                print(f"\nERROR converting {file}: {e}")
                write_log(step3_log_path, file, "FAILURE", str(e))
                


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
                    metadata_result = spectralis_instance.metadata(
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
