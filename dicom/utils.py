import importlib.util
import os
import re
import shutil
import string
import zipfile
from pathlib import Path

import pydicom
from aireadi_retinal_imaging.dicom import classification as imaging_classifying_rules
from bs4 import BeautifulSoup


def find_string_in_files(file_list, target_string):
    """
    Searches for the target string in a list of file contents.

    Args:
        file_list (list of str): A list of strings, where each string represents the content of a file.
        target_string (str): The string to search for within the file contents.

    Returns:
        int: The index of the first file in which the target string is found.
        str: A message indicating that the string was not found if the target string is not found in any file.
    """
    for i in file_list:
        if target_string in i:
            return i
    return "String not found in any file."


def extract_numeric_part(uid):
    """
    Extract numerical parts of the UID.

    Args:
        uid (str): A unique identifier (UID) that may contain numeric and non-numeric parts separated by periods.

    Returns:
        list: A list containing the numeric parts as integers and the non-numeric parts as strings.
    """
    parts = uid.split(".")
    return [int(part) if part.isdigit() else part for part in parts]


def list_zip_files(directory):
    """
    List all zip files in a given directory.

    Args:
        directory (str): The path to the directory to search for zip files.

    Returns:
        list: A list of file paths for each zip file found in the directory.
    """
    zip_files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.endswith(".zip") and f[0].lower() in string.ascii_lowercase
    ]
    return zip_files


def unzip_fda_file(input_zip_path, output_folder_path):
    """
    Unzips the contents of a zip file into the specified output folder based on specific criteria.

    The function will only unzip files if they contain 'fda' in their name. It also categorizes the files into
    'Maestro2' or 'Triton' folders based on their names. If the file does not meet these criteria, it will be skipped.

    Parameters:
    input_zip_path (str): Path to the input zip file.
    output_folder_path (str): Path to the output folder where files will be extracted.

    Returns:
    dict: A dictionary containing the input zip path and the unzipping status.
    """
    input_name = input_zip_path.split("/")[-1].replace(".", "_")
    input_name = input_name[:-4] if input_name.endswith("_zip") else input_name

    if "fda" not in input_zip_path.lower():
        dic = {
            "Input": f"{input_zip_path}",
            "Unzipping": "no fda file will be skipped",
        }

        return dic

    elif "maestro2" in input_zip_path.lower():
        # Create the output folder if it doesn't exist
        maestro2 = f"{output_folder_path}/Maestro2/{input_name}"
        os.makedirs(maestro2, exist_ok=True)

        # Unzip the contents of the zip file into the output folder
        with zipfile.ZipFile(input_zip_path, "r") as zip_ref:
            zip_ref.extractall(maestro2)

        dic = {"Input": f"{input_zip_path}", "Unzipping": "correct"}

        return dic

    elif "triton" in input_zip_path.lower():
        # Create the output folder if it doesn't exist
        triton = f"{output_folder_path}/Triton/{input_name}"
        os.makedirs(triton, exist_ok=True)

        # Unzip the contents of the zip file into the output folder
        with zipfile.ZipFile(input_zip_path, "r") as zip_ref:
            zip_ref.extractall(triton)
        dic = {"Input": f"{input_zip_path}", "Unzipping": "correct"}

        return dic

    elif "cirrus" in input_zip_path.lower():
        # Create the output folder if it doesn't exist
        cirrus = f"{output_folder_path}/Cirrus/{input_name}"
        os.makedirs(cirrus, exist_ok=True)

        # Unzip the contents of the zip file into the output folder
        with zipfile.ZipFile(input_zip_path, "r") as zip_ref:
            zip_ref.extractall(cirrus)

        for root, dirs, files in os.walk(cirrus):
            for file in files:
                if not file.lower().endswith(".dcm"):
                    os.remove(os.path.join(root, file))

        dic = {"Input": f"{input_zip_path}", "Unzipping": "correct"}

        return dic

    else:
        print("unknown")
        dic = {"Input": f"{input_zip_path}", "Unzipping": "unknown"}

        return dic

import os


def get_filtered_file_names(folder_path):
    """
    Get filtered file names from a folder.

    This function walks through a folder and filters out:
      - hidden files starting with "._"
      - files not starting with an alphabet or digit
      - any '.csv' files

    Args:
        folder_path (str): The path to the folder to search for files.

    Returns:
        list: A list of filtered file paths.
    """
    filtered_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(".csv"):  # skip CSV files
                continue

            if file.startswith("._"):  # skip hidden AppleDouble files
                continue

            if not (file[0].isalpha() or file[0].isdigit()):  # must start with letter or digit
                continue

            full_path = os.path.join(root, file)
            filtered_files.append(full_path)

    return filtered_files


oct_mapping = {
    "maestro2_3d_wide_oct": [
        "Topcon",
        "Maestro2",
        "Wide Field",
        "OCT",
    ],
    "maestro2_macula_6x6_oct": ["Topcon", "Maestro2", "Macula, 6 x 6", "OCT"],
    "maestro2_3d_macula_oct": ["Topcon", "Maestro2", "Macula", "OCT"],
    "triton_3d_radial_oct": ["Topcon", "Triton", "Optic Disc", "OCT"],
    "triton_macula_6x6_oct": ["Topcon", "Triton", "Macula, 6 x 6", "OCT"],
    "triton_macula_12x12_oct": ["Topcon", "Triton", "Macula, 12 x 12", "OCT"],
    "spectralis_onh_rc_hr_oct": ["Heidelberg", "Spectralis", "Optic Disc", "OCT"],
    "spectralis_ppol_mac_hr_oct": ["Heidelberg", "Spectralis", "Macula", "OCT"],
}

retinal_photography_mapping = {
    "optomed_mac_or_disk_centered_cfp": [
        "Optomed",
        "Aurora",
        "Macula or Optic Disc",
        "Color Photography",
        "3",
    ],
    "eidon_mosaic_cfp": ["iCare", "Eidon", "Mosaic", "Color Photography", "3"],
    "eidon_uwf_central_faf": ["iCare", "Eidon", "Macula", "Autofluorescence", "3"],
    "eidon_uwf_central_ir": ["iCare", "Eidon", "Macula", "Infrared Reflectance", "3"],
    "eidon_uwf_nasal_cfp": ["iCare", "Eidon", "Nasal", "Color Photography", "3"],
    "eidon_uwf_temporal_cfp": [
        "iCare",
        "Eidon",
        "Temporal Periphery",
        "Color Photography",
        "3",
    ],
    "eidon_uwf_central_cfp": ["iCare", "Eidon", "Macula", "Color Photography", "3"],
    "maestro2_3d_wide": ["Topcon", "Maestro2", "Wide Field", "Color Photography", "3"],
    "maestro2_macula_6x6": [
        "Topcon",
        "Maestro2",
        "Macula, 6 x 6",
        "Infrared Reflectance",
        "3",
    ],
    "maestro2_3d_macula": ["Topcon", "Maestro2", "Macula", "Color Photography", "3"],
    "triton_3d_radial": ["Topcon", "Triton", "Optic Disc", "Color Photography", "3"],
    "triton_macula_6x6": [
        "Topcon",
        "Triton",
        "Macula, 6 x 6",
        "Color Photography",
        "3",
    ],
    "triton_macula_12x12": [
        "Topcon",
        "Triton",
        "Macula, 12 x 12",
        "Color Photography",
        "3",
    ],
    "spectralis_onh_rc": [
        "Heidelberg",
        "Spectralis",
        "Optic Disc",
        "Infrared Reflectance",
        "0",
    ],
    "spectralis_ppol_mac_hr": [
        "Heidelberg",
        "Spectralis",
        "Macula",
        "Infrared Reflectance",
        "0",
    ],
}
# def get_filtered_file_names(folder_path):
#     """
#     Get filtered file names from a folder.

#     This function walks through a folder and filters out files that don't start with a valid
#     character (alphabet or digit) and aren't hidden files (starting with "._").

#     Args:
#         folder_path (str): The path to the folder to search for files.

#     Returns:
#         list: A list of filtered file paths.
#     """
#     filtered_files = []
#     for root, dirs, files in os.walk(folder_path):
#         for file in files:
#             full_path = os.path.join(root, file)
#             file_name = full_path.split("/")[-1]
#             if (
#                 file_name
#                 and not file_name.startswith("._")
#                 and (file_name[0].isalpha() or file_name[0].isdigit())
#             ):
#                 filtered_files.append(full_path)
#     return filtered_files


def spectralis_get_filtered_file_names(folder_path):
    """
    Get filtered file names from a folder.

    This function walks through a folder and filters out files that don't start with a valid
    character (alphabet or digit) and aren't hidden files (starting with "._").

    Args:
        folder_path (str): The path to the folder to search for files.

    Returns:
        list: A list of filtered file paths.
    """
    filtered_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            full_path = os.path.join(root, file)
            if full_path.split("/")[-1] and full_path.split("/")[-1].startswith("0"):
                filtered_files.append(full_path)
    return filtered_files


def list_subfolders(folder_path):
    """
    List all subfolders in a given folder.

    Args:
        folder_path (str): The path to the folder.

    Returns:
        list: A list of paths to subfolders.
    """

    if not os.path.isdir(folder_path):
        print("Invalid folder path.")
        return []
    subfolders = [
        os.path.join(folder_path, item)
        for item in os.listdir(folder_path)
        if os.path.isdir(os.path.join(folder_path, item))
    ]
    return subfolders


def check_files_in_folder(folder_path, file_names):
    """
    Check if specific files exist in a folder.

    Args:
        folder_path (str): The path to the folder.
        file_names (list): A list of file names to check for.

    Returns:
        bool: True if all files are present, False otherwise.
    """
    files = os.listdir(folder_path)

    for file_name in file_names:
        if file_name not in files:
            return False

    return True


import os
import shutil


def create_structure(main_folder: str) -> None:
    """
    Ensure main_folder exists. Empty (remove & recreate) step2..step5 and metadata.
    Leave step1 untouched if present.
    """
    # Normalize the path
    main = os.path.abspath(os.path.expanduser(main_folder))

    # Validate / create main folder
    if os.path.exists(main) and not os.path.isdir(main):
        raise ValueError(f"{main} exists and is not a directory")
    os.makedirs(main, exist_ok=True)

    to_reset = ["step2", "step3", "step4", "step5", "metadata"]

    for name in to_reset:
        p = os.path.join(main, name)
        if os.path.exists(p):
            # If it's a file, remove it; if it's a dir, remove it recursively
            if os.path.isfile(p) or os.path.islink(p):
                os.remove(p)
            else:
                shutil.rmtree(p)
        os.mkdir(p)

    print("Reset directories in:", main)
    for name in to_reset:
        print(" -", os.path.join(main, name))




def get_html_in_folder(folder_path):
    """
    Check if specific files exist in a folder and return the file that ends with .html.

    Args:
        folder_path (str): The path to the folder.
        file_names (list): A list of file names to check for.

    Returns:
        str: The name of the .html file if found, otherwise an empty string.
    """
    files = os.listdir(folder_path)

    # Check for a file that ends with .html
    for file in files:
        if file.endswith(".html"):
            return file


def find_consecutive_integers(s):
    # Regular expression to find 4 consecutive digits
    match = re.search(r"\d{4}", s)
    if match:
        return match.group(0)
    else:
        return "9999"


def get_patient_id_from_html(html_file):
    with open(html_file, "r") as file:
        html_content = file.read()
        soup = BeautifulSoup(html_content, "html.parser")

        # Extracting FLIO HTML table data
        tables = soup.find_all("table")
        all_table_data = []
        for table in tables:
            table_data = []
            rows = table.find_all("tr")
            for row in rows:
                row_data = [
                    cell.get_text().strip() for cell in row.find_all(["td", "th"])
                ]
                table_data.append(row_data)
            all_table_data.append(table_data)

        patient_id = find_consecutive_integers(
            all_table_data[0][2][1].replace("-", "").replace(",", "-").replace(" ", "")
        )

    return patient_id


def filter_flio_files_process(input, output):
    """
    Filters and processes FLIO (Fluorescence Lifetime Imaging Ophthalmoscopy) files from the input directory and copies them to an output directory.

    This function navigates through subdirectories in the input folder, identifies folders containing the necessary FLIO files
    ("Measurement.sdt" and "measurement_info.html"), and copies these folders to the output directory with a modified folder name.
    If any required files are missing, a message is printed indicating the missing file and its folder path.

    Args:
        input (str): The full path to the input directory containing subfolders of FLIO files.
        output (str): The full path to the output directory where processed FLIO files will be copied.

    Returns:
        None

    """
    pts = list_subfolders(input)
    for pt in pts:
        laterality = list_subfolders(pt)
        for one in laterality:
            folder_path = one
            if check_files_in_folder(
                folder_path, ["Measurement.sdt", "measurement_info.html"]
            ):
                patient = pt.split("/")[-1]
                side = one.split("/")[-1]

                outputpath = f"{output}/flio_{patient}_{side}"
                shutil.copytree(folder_path, outputpath)
            else:
                print("missing file", folder_path)


def get_filtered_all_file_names(folder_path):
    """
    Retrieves a list of all file paths in a directory, excluding those with names starting with '._'.

    This function walks through all subdirectories of the specified folder and collects the full paths
    of files, excluding any files whose names start with '._' (often used for metadata or system files on some systems).

    Args:
        folder_path (str): The full path to the directory to search for files.

    Returns:
        list: A list of strings, where each string is the full path to a file that does not start with '._'.
    """
    filtered_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            full_path = os.path.join(root, file)
            if not full_path.split("/")[-1].startswith("._"):
                filtered_files.append(full_path)
    return filtered_files


# def find_html_sdt_files(folder_path):
#     """
#     Finds and returns the paths of the HTML and SDT files within a specified folder.

#     This function searches through all files in the given folder, identifying one HTML file and one SDT file.
#     If multiple HTML or SDT files are found, or if either file type is missing, the function raises a ValueError.

#     Args:
#         folder_path (str): The full path to the folder to search for HTML and SDT files.

#     Returns:
#         tuple: A tuple containing two elements:
#             - sdt_file (str): The full path to the found SDT file.
#             - html_file (str): The full path to the found HTML file.

#     Raises:
#         ValueError: If multiple HTML files or multiple SDT files are found.
#         ValueError: If either the HTML file or the SDT file is not found in the folder.

#     """
#     html_file = None
#     sdt_file = None

#     # List all files in the folder
#     files = get_filtered_all_file_names(folder_path)

#     # Check for HTML and SDT files
#     for file in files:
#         if file.endswith(".html"):
#             if html_file is not None:
#                 raise ValueError("Multiple HTML files found")
#             html_file = os.path.join(folder_path, file)
#         elif file.endswith(".sdt"):
#             if sdt_file is not None:
#                 raise ValueError("Multiple SDT files found")
#             sdt_file = os.path.join(folder_path, file)

#     # Ensure both HTML and SDT files are found
#     if html_file is None or sdt_file is None:
#         html_file = ""
#         sdt_file = ""

#     return sdt_file, html_file




def topcon_check_files_expected(folder_path):
    """
    Check if a folder contains the expected number of specific files for Topcon devices.

    Args:
        folder_path (str): The path to the folder.

    Returns:
        str: "Expected" if the files match the expected patterns, otherwise "Unknown".
    """

    files_count_9 = 0

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(
                (
                    "1.1.dcm",
                    "2.1.dcm",
                    "3.1.dcm",
                    "7.3.dcm",
                    "6.3.dcm",
                    "6.4.dcm",
                    "6.5.dcm",
                    "6.80.dcm",
                )
            ) and file.startswith("2"):
                files_count_9 += 1

    # Check if files match expected patterns

    if (files_count_9 == 3) or (files_count_9 == 8) or (files_count_9 == 7):
        return "Expected"
    else:
        return "Unknown"


def cirrus_check_files_expected(folder_path):
    """
    Check if a folder contains the expected number of specific files for Cirrus devices.

    Args:
        folder_path (str): The path to the folder.

    Returns:
        str: "Expected" if the files match the expected patterns, otherwise "Unknown".
    """

    files_count = 0

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith((".dcm",)) and file.startswith("A"):
                files_count += 1

    # Check if files match expected patterns

    if (files_count == 7) or (files_count == 15):
        return "Expected"
    else:
        return "Unknown"


def topcon_process_folder(folder_path, outputpath, rule):
    """
    Process a folder of Topcon device files and copy them to an output directory based on rules.

    Args:
        folder_path (str): The path to the folder to process.
        outputpath (str): The path to the output directory.
        rule (str): The classification rule to apply.
        empty_df (pd.DataFrame): A DataFrame to store information about processed files.

    Returns:
        pd.DataFrame: Updated DataFrame with information about processed files.
    """
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith("1.1.dcm") and file.startswith("2"):
                file_path = os.path.join(root, file)
                original_folder_basename = os.path.basename(os.path.dirname(file_path))
                info = imaging_classifying_rules.extract_dicom_entry(file_path)
                laterality = info.laterality
                patientid = info.patientid
                error = info.error
                if rule.endswith("_oct"):
                    output = f"{outputpath}/{rule[:-4]}/{rule[:-4]}_{patientid}_{laterality}_{original_folder_basename}"
                else:
                    output = f"{outputpath}/{rule}/{rule}_{patientid}_{laterality}_{original_folder_basename}"

                os.makedirs(output, exist_ok=True)
                
                folder = os.path.dirname(file_path)
                all_items = os.listdir(folder)
                all_files = [f for f in all_items if os.path.isfile(os.path.join(folder, f))]

                if len(all_files) == 3:
                    for item in all_items:
                        source_path = os.path.join(folder, item)
                        if os.path.isdir(source_path):
                            dest_path = os.path.join(output, item)
                            if os.path.exists(dest_path):
                                shutil.rmtree(dest_path)
                            shutil.copytree(source_path, dest_path)
                        elif item.endswith(("1.1.dcm", "2.1.dcm")):
                            new_filename = f"{original_folder_basename}_{item}"
                            dest_path = os.path.join(output, new_filename)
                            shutil.copy2(source_path, dest_path)
                else:
                    for item in all_items:
                        source_path = os.path.join(folder, item)
                        if os.path.isdir(source_path):
                            dest_path = os.path.join(output, item)
                            if os.path.exists(dest_path):
                                shutil.rmtree(dest_path)
                            shutil.copytree(source_path, dest_path)
                        else:
                            new_filename = f"{original_folder_basename}_{item}"
                            dest_path = os.path.join(output, new_filename)
                            shutil.copy2(source_path, dest_path)


                # for item in os.listdir(os.path.dirname(file_path)):
                #     source_path = os.path.join(os.path.dirname(file_path), item)
                #     dest_path = os.path.join(output, item)

                #     if os.path.isdir(source_path):
                #         if os.path.exists(dest_path):
                #             shutil.rmtree(dest_path)
                #         shutil.copytree(source_path, dest_path)
                #     else:
                #         new_filename = f"{original_folder_basename}_{item}"
                #         dest_path = os.path.join(output, new_filename)
                #         shutil.copy2(source_path, dest_path)
                #         # shutil.copy2(source_path, dest_path)

    # for root, dirs, files in os.walk(outputpath):
    #     for file in files:
    #         file_path = os.path.join(root, file)
    #         if os.path.isfile(file_path):
    #             if file[0].isdigit():
    #                 parent_folder = os.path.basename(os.path.normpath(root))
    #                 new_name = os.path.join(root, f"{parent_folder}_{file}")
    #                 os.rename(file_path, new_name)

    #             if rule in [
    #                 "maestro2_mac_6x6_octa_oct",
    #                 "maestro2_macula_oct_oct",
    #                 "maestro2_3d_wide_oct_oct",
    #                 "triton_3d_radial_oct_oct",
    #                 "triton_macula_6x6_octa_oct",
    #                 "triton_macula_12x12_octa_oct",
    #             ]:
    #                 row_to_append = {
    #                     "Rule": rule[:-4],
    #                     "PatientID": patientid,
    #                     "Folder": original_folder_basename,
    #                     "Laterality": laterality,
    #                     "Error": error,
    #                 }

    return output


def filter_eidon_files(file, outputfolder):
    """
    Filter and process EIDON files based on classification rules.

    This function applies classification rules to a DICOM file, extracts relevant information,
    and copies the file to an appropriate output directory based on the classification rule.

    Args:
        file (str): The path to the DICOM file to be processed.
        outputfolder (str): The directory where the processed files will be stored.

    Returns:
        dict: A dictionary containing information about the processed file, including rule, patient ID,
        patient name, laterality, rows, columns, SOP instance UID, series instance UID, filename,
        original file path, and any errors encountered.
    """

    filename = file.split("/")[-1]
    rule = imaging_classifying_rules.find_rule(file)
    b = imaging_classifying_rules.extract_dicom_entry(file)
    laterality = b.laterality
    uid = b.sopinstanceuid
    patientid = b.patientid
    rows = b.rows
    columns = b.columns
    seriesuid = b.seriesuid
    error = b.error
    name = b.name

    original_path = file
    output_path = f"{outputfolder}/{rule}/{rule}_{filename}"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    shutil.copyfile(original_path, output_path)

    dic = {
        "Rule": rule,
        "PatientID": patientid,
        "PatientName": name,
        "Laterality": laterality,
        "Rows": rows,
        "Columns": columns,
        "SOPInstanceuid": uid,
        "SeriesInstanceuid": seriesuid,
        "Filename": filename,
        "Path": file,
        "Error": error,
    }

    return dic


protocol_mapping = {
    "optomed_mac_or_disk_centered_cfp": "optomed mac or disk centered color retinal photography",
    "eidon_mosaic_cfp": "eidon mosaic color retinal photography",
    "eidon_uwf_central_faf": "eidon central autofluorescence retinal photography",
    "eidon_uwf_central_ir": "eidon central infrared retinal photography",
    "eidon_uwf_nasal_cfp": "eidon nasal color retinal photography",
    "eidon_uwf_temporal_cfp": "eidon temporal color retinal photography",
    "eidon_uwf_central_cfp": "eidon central color retinal photography",
    "maestro2_3d_wide_oct": "maestro2 3d wide oct",
    "maestro2_mac_6x6_octa": "maestro2 macula 6x6 octa",
    "maestro2_3d_macula_oct": "maestro2 3d macula oct",
    "triton_3d_radial_oct": "triton 3d radial oct",
    "triton_macula_6x6_octa": "triton macula 6x6 octa",
    "triton_macula_12x12_octa": "triton macula 12x12 octa",
    "spectralis_onh_rc_hr_oct": "spectralis onh rc hr oct",
    "spectralis_onh_rc_hr_retinal_photography": "spectralis onh rc hr oct",
    "spectralis_ppol_mac_hr_oct": "spectralis ppol mac hr oct",
    "spectralis_ppol_mac_hr_oct_small": "spectralis ppol mac hr oct",
    "spectralis_ppol_mac_hr_retinal_photography": "spectralis ppol mac hr oct",
    "spectralis_ppol_mac_hr_retinal_photography_small": "spectralis ppol mac hr oct",
    "flio": "fluorescence lifetime imaging ophthalmoscopy",
}


name_mapping = {
    "optomed_mac_or_disk_centered_cfp": "optomed_mac_or_disk_centered_cfp",
    "eidon_mosaic_cfp": "eidon_mosaic_cfp",
    "eidon_uwf_central_faf": "eidon_uwf_central_faf",
    "eidon_uwf_central_ir": "eidon_uwf_central_ir",
    "eidon_uwf_nasal_cfp": "eidon_uwf_nasal_cfp",
    "eidon_uwf_temporal_cfp": "eidon_uwf_temporal_cfp",
    "eidon_uwf_central_cfp": "eidon_uwf_central_cfp",
    # 6 
    "maestro2_3d_wide_oct": "maestro2_3d_wide_oct",
    "maestro2_mac_6x6_octa": "maestro2_macula_6x6_octa",
    "maestro2_3d_macula_oct": "maestro2_3d_macula_oct",
    "triton_3d_radial_oct": "triton_3d_radial_oct",
    "triton_macula_6x6_octa": "triton_macula_6x6_octa",
    "triton_macula_12x12_octa": "triton_macula_12x12_octa",
    "spectralis_onh_rc_hr_oct": "spectralis_onh_rc_hr_oct_oct",
    "spectralis_onh_rc_hr_retinal_photography": "spectralis_onh_rc_hr_oct_ir",
    "spectralis_ppol_mac_hr_oct": "spectralis_ppol_mac_hr_oct_oct",
    "spectralis_ppol_mac_hr_oct_small": "spectralis_ppol_mac_hr_oct_oct",
    "spectralis_ppol_mac_hr_retinal_photography": "spectralis_ppol_mac_hr_oct_ir",
    "spectralis_ppol_mac_hr_retinal_photography_small": "spectralis_ppol_mac_hr_oct_ir",
    "flio": "flio",
    "mac_angiography": "cirrus_macula_6x6_octa",
    "onh_angiography": "cirrus_disc_6x6_octa",
    "mac_macular_cube_": "cirrus_mac_oct",
    "onh_optic_disc_cube_": "cirrus_disc_oct",
}

# name_mapping = {
#     "optomed_mac_or_disk_centered_cfp": "optomed_mac_or_disk_centered_cfp",
#     "eidon_mosaic_cfp": "eidon_mosaic_cfp",
#     "eidon_uwf_central_faf": "eidon_uwf_central_faf",
#     "eidon_uwf_central_ir": "eidon_uwf_central_ir",
#     "eidon_uwf_nasal_cfp": "eidon_uwf_nasal_cfp",
#     "eidon_uwf_temporal_cfp": "eidon_uwf_temporal_cfp",
#     "eidon_uwf_central_cfp": "eidon_uwf_central_cfp",
#     "maestro2_3d_wide_oct": "maestro2_3d_wide",
#     "maestro2_mac_6x6_octa": "maestro2_macula_6x6",
#     "maestro2_3d_macula_oct": "maestro2_3d_macula",
#     "triton_3d_radial_oct": "triton_3d_radial",
#     "triton_macula_6x6_octa": "triton_macula_6x6",
#     "triton_macula_12x12_octa": "triton_macula_12x12",
#     "spectralis_onh_rc_hr_oct": "spectralis_onh_rc_hr_oct",
#     "spectralis_onh_rc_hr_retinal_photography": "spectralis_onh_rc_hr_ir",
#     "spectralis_ppol_mac_hr_oct": "spectralis_ppol_mac_hr_oct",
#     "spectralis_ppol_mac_hr_oct_small": "spectralis_ppol_mac_hr_oct",
#     "spectralis_ppol_mac_hr_retinal_photography": "spectralis_ppol_mac_hr_ir",
#     "spectralis_ppol_mac_hr_retinal_photography_small": "spectralis_ppol_mac_hr_ir",
#     "flio": "flio",
#     "mac_angiography": "cirrus_macula_6x6_octa",
#     "onh_angiography": "cirrus_disc_6x6_octa",
#     "mac_macular_cube_": "cirrus_mac_oct",
#     "onh_optic_disc_cube_": "cirrus_disc_oct",
# }

cirrus_submodality_mapping = {
    "LSO": "ir",
    "Struc.": "oct",
    "Flow.": "flow_cube",
    "ProjectionRemoved": "enface_projection_removed",
    "AngioEnface.": "enface",
    "StructuralEnface": "enface_structural",
    "Seg": "segmentation",
}


def topcon_submodality(file):

    a = pydicom.dcmread(file)
    submodality = ""
    if (
        a.SOPClassUID == "1.2.840.10008.5.1.4.1.1.77.1.5.1"
        and a.ImageType[3] == "COLOR"
    ):
        submodality = "cfp"

    elif (
        a.SOPClassUID == "1.2.840.10008.5.1.4.1.1.77.1.5.1"
        and a.ImageType[3] == "IR"
    ):
        submodality = "ir"

    elif a.SOPClassUID == "1.2.840.10008.5.1.4.1.1.77.1.5.4":
        submodality = "oct"

    elif a.SOPClassUID == "1.2.840.10008.5.1.4.1.1.66.8":
        submodality = "segmentation"

    # elif a.SOPClassUID == "1.2.840.10008.5.1.4.1.1.77.1.5.8" and file.endswith(
    #     "5.1.dcm"
    # ):
    #     submodality = "flow_cube"

    elif a.SOPClassUID == "1.2.840.10008.5.1.4.1.1.77.1.5.8" and file.endswith(
        "3.1.dcm"
    ):
        submodality = "flow_cube"

    elif a.SOPClassUID == "1.2.840.10008.5.1.4.1.1.77.1.5.7":
        submodality = "enface"

    return submodality


# maestro_octa_submodality_mapping = {
#     "1.1.dcm": "oct",
#     "2.1.dcm": "ir",
#     "3.1.dcm": "flow_cube_raw_data",
#     "4.1.dcm": "segmentation",
#     "5.1.dcm": "flow_cube",
#     "6.3.dcm": "enface",
#     "6.4.dcm": "enface",
#     "6.5.dcm": "enface",
#     "6.80.dcm": "enface",
# }

# topcon_except_maestro_octa_submodality_mapping = {
#     "1.1.dcm": "oct",
#     "2.1.dcm": "cfp",
#     "3.1.dcm": "flow_cube_raw_data",
#     "4.1.dcm": "segmentation",
#     "5.1.dcm": "flow_cube",
#     "6.3.dcm": "enface",
#     "6.4.dcm": "enface",
#     "6.5.dcm": "enface",
#     "6.80.dcm": "enface",
# }


modality_folder_mapping = {
    "ir_": "retinal_photography",
    "cfp": "retinal_photography",
    "faf": "retinal_photography",
    "flow_cube": "retinal_octa",
    "segmentation": "retinal_octa",
    "enface": "retinal_octa",
    "_oct_l": "retinal_oct",
    "_oct_r": "retinal_oct",
    "flio": "retinal_flio",
    "Flow.": "retinal_octa",
}

cirrus_modality_folder_mapping = {
    "ir_": "retinal_photography",
    "segmentation": "retinal_octa",
    "enface_projection": "retinal_octa",
    "enface_l": "retinal_octa",
    "enface_r": "retinal_octa",
    "_oct_oct_": "retinal_oct",
    "_octa_oct_": "retinal_oct",
    "flow_cube": "retinal_octa",
}

cirrus_submodality_folder_mapping = {
    "ir_": "ir",
    "_oct_oct_": "structural_oct",
    "_octa_oct_": "structural_oct",
    "flow_cube": "flow_cube",
    "segmentation": "segmentation",
    "enface_projection": "enface",
    "enface_l": "enface",
    "enface_r": "enface",
}

submodality_folder_mapping = {
    "ir_": "ir",
    "cfp": "cfp",
    "faf": "faf",
    "_oct_l": "structural_oct",
    "_oct_r": "structural_oct",
    "flow_cube": "flow_cube",
    "Flow.": "flow_cube",
    "segmentation": "segmentation",
    "enface": "enface",
    "flio": "flio",
}

device_folder_mapping = {
    "eidon": "icare_eidon",
    "optomed": "optomed_aurora",
    "maestro2": "topcon_maestro2",
    "triton": "topcon_triton",
    "spectralis": "heidelberg_spectralis",
    "flio": "heidelberg_flio",
    "cirrus": "zeiss_cirrus",
}


def get_description(filename, mapping):
    """
    Get a description based on a filename and a mapping dictionary.

    Args:
        filename (str): The name of the file.
        mapping (dict): A dictionary mapping keys to descriptions.

    Returns:
        str: The description corresponding to the filename, or "Description not found" if no match is found.
    """
    for key, value in mapping.items():
        if key in filename:
            return value
    return "Description not found"


def check_format(string):
    """
    Check if a string follows a specific format.

    Args:
        string (str): The string to check.

    Returns:
        bool: True if the string follows the format "AIREADI-XXXX" where XXXX are digits, otherwise False.
    """
    if string.startswith("AIREADI-"):
        digits = string[len("AIREADI-") : len("AIREADI-") + 4]
        if len(digits) == 4 and digits[0] in ["1", "4", "7"] and digits.isdigit():
            return True
    return False


def find_number(val):
    """
    Find the first four-digit number in a string.

    Args:
        val (str): The string to search.

    Returns:
        str: The first four-digit number found, or "noid" if none is found.
    """
    is_number = False
    buffer = []
    for i in range(len(val)):
        if val[i].isnumeric():
            buffer.append(val[i])
            is_number = True
        else:
            if is_number:
                return "".join(buffer[:4])
    if is_number:
        return "".join(buffer[:4])
    return "noid"


def find_id(patientid, patientname):
    """
    Find a patient ID based on the given patient ID and name.

    This function checks the patient ID and name to extract a valid ID. It first checks if
    the ID follows a specific format, and if not, it searches for a number within the ID
    or name strings.

    Args:
        patientid (str): The patient ID.
        patientname (str): The patient name.

    Returns:
        str: The extracted patient ID or "noid" if no valid ID is found.
    """
    patientid = (
        ""
        if patientid == "None" or patientid is None or not isinstance(patientid, str)
        else patientid
    )
    patientname = (
        ""
        if patientname == "None"
        or patientname is None
        or not isinstance(patientname, str)
        else patientname
    )

    if check_format(patientid):
        return patientid[len("AIREADI-") : len("AIREADI-") + 4]

    else:
        if find_number(patientid) != "noid":
            return find_number(patientid)
        else:
            if find_number(patientname) != "noid":

                return find_number(patientname)
            else:
                return find_number(patientname)
import traceback


def format_file(file, output):
    """
    Format a DICOM file and save it to an output directory.

    This function reads a DICOM file, extracts relevant information, and formats it according to
    specified rules. It then saves the formatted file to the appropriate output directory.

    Args:
        file (str): The path to the DICOM file to be formatted.
        output (str): The base path to the output directory.

    Returns:
        dict: A dictionary containing protocol, patient ID, and laterality information.
    """

    try:
        dataset = pydicom.dcmread(file)

    except Exception:
        full_dir_path = output + "/invalid_dicom"
        os.makedirs(full_dir_path, exist_ok=True)
        filename = os.path.basename(file)
        full_file_path = os.path.join(full_dir_path, filename)
        shutil.copy(file, full_file_path)
    else:
        # try:
        #     # Check if dataset has pixel data
        #     pixel = dataset.pixel_array
        # except Exception:
        #     # Handle case where pixel_array is not available
        #     full_dir_path = output + "/error_pixel_data/"
        #     os.makedirs(full_dir_path, exist_ok=True)
        #     filename = os.path.basename(file)
        #     full_file_path = os.path.join(full_dir_path, filename)
        #     shutil.copy(file, full_file_path)

        # else:
        id = find_id(str(dataset.PatientID), str(dataset.PatientName))

        if id == "noid":
            full_dir_path = output + "/missing_critical_info/no_id/"
            os.makedirs(full_dir_path, exist_ok=True)
            filename = os.path.basename(file)
            full_file_path = os.path.join(full_dir_path, filename)
            dataset.save_as(full_file_path)

        else:
            uid = dataset.SOPInstanceUID

            dataset.PatientID = id
            dataset.PatientName = ""
            dataset.PatientSex = "M"
            dataset.PatientBirthDate = ""

            if "cirrus" in file:
                dataset.ProtocolName = dataset.ProtocolName

            else:
                protocol = get_description(file, protocol_mapping)
                dataset.ProtocolName = protocol

            laterality = dataset.ImageLaterality.lower()
            patientid = id

            modality = get_description(file, name_mapping)

            submodality = ""

            if "maestro2" in file or "triton" in file:

                submodality = topcon_submodality(file)
                submodality = f"{submodality}"
                filename = f"{id}_{modality}_{submodality}_{laterality}_{uid}.dcm"

            elif "cirrus" in file:
                submodality = get_description(file, cirrus_submodality_mapping)
                # n = f"{n}"
                submodality = f"{submodality}"

                filename = f"{id}_{modality}_{submodality}_{laterality}_{uid}.dcm"

            elif "flio" in file:
                submodality = next(
                    (
                        submodality
                        for submodality in ["short_wavelength", "long_wavelength"]
                        if submodality in file
                    ),
                    "unknown_submodality",
                )
                filename = f"{id}_{modality}_{submodality}_{laterality}_{uid}.dcm"

            else:
      
                filename = f"{id}_{modality}_{laterality}_{uid}.dcm"

            if "cirrus" in filename:
                modality_folder = get_description(
                    filename, cirrus_modality_folder_mapping
                )
                submodality_folder = get_description(
                    filename, cirrus_submodality_folder_mapping
                )
                device_folder = get_description(filename, device_folder_mapping)
            else:
                modality_folder = get_description(filename, modality_folder_mapping)

                submodality_folder = get_description(
                    filename, submodality_folder_mapping
                )
                
                device_folder = get_description(filename, device_folder_mapping)
           


            folderpath = (
                f"/{modality_folder}/{submodality_folder}/{device_folder}/{id}/"
            )

            full_dir_path = output + folderpath

            os.makedirs(full_dir_path, exist_ok=True)

            full_file_path = os.path.join(full_dir_path, filename)

            dataset.save_as(full_file_path)

            return full_file_path
# def format_file(file, output):
#     """
#     Format a DICOM file and save it to an output directory.

#     This function reads a DICOM file, extracts relevant information, and formats it according to
#     specified rules. It then saves the formatted file to the appropriate output directory.

#     Args:
#         file (str): The path to the DICOM file to be formatted.
#         output (str): The base path to the output directory.

#     Returns:
#         dict: A dictionary containing protocol, patient ID, and laterality information.
#     """

#     try:
#         dataset = pydicom.dcmread(file)

#     except Exception:
#         full_dir_path = output + "/invalid_dicom"
#         os.makedirs(full_dir_path, exist_ok=True)
#         filename = os.path.basename(file)
#         full_file_path = os.path.join(full_dir_path, filename)
#         shutil.copy(file, full_file_path)
#         return None
#     else:
#         # try:
#         # try:
#         #     # Check if dataset has pixel data
#         #     pixel = dataset.pixel_array
#         # except Exception:
#         #     # Handle case where pixel_array is not available
#         #     full_dir_path = output + "/error_pixel_data/"
#         #     os.makedirs(full_dir_path, exist_ok=True)
#         #     filename = os.path.basename(file)
#         #     full_file_path = os.path.join(full_dir_path, filename)
#         #     shutil.copy(file, full_file_path)

#         # else:
#         id = find_id(str(dataset.PatientID), str(dataset.PatientName))

#         if id == "noid":
#             full_dir_path = output + "/missing_critical_info/no_id/"
#             os.makedirs(full_dir_path, exist_ok=True)
#             filename = os.path.basename(file)
#             full_file_path = os.path.join(full_dir_path, filename)
#             dataset.save_as(full_file_path)

#         else:
#             uid = dataset.SOPInstanceUID

#             dataset.PatientID = id
#             dataset.PatientName = ""
#             dataset.PatientSex = "M"
#             dataset.PatientBirthDate = ""

#             if "cirrus" in file:
#                 dataset.ProtocolName = dataset.ProtocolName

#             else:
#                 protocol = get_description(file, protocol_mapping)
#                 dataset.ProtocolName = protocol

#             laterality = dataset.ImageLaterality.lower()
#             patientid = id

#             modality = get_description(file, name_mapping)

#             submodality = ""

#             if "maestro2" in file or "triton" in file:

#                 submodality = topcon_submodality(file)
#                 submodality = f"{submodality}"
#                 filename = f"{id}_{modality}_{submodality}_{laterality}_{uid}.dcm"

#             elif "cirrus" in file:
#                 submodality = get_description(file, cirrus_submodality_mapping)
#                 # n = f"{n}"
#                 submodality = f"{submodality}"

#                 filename = f"{id}_{modality}_{submodality}_{laterality}_{uid}.dcm"

#             elif "flio" in file:
#                 submodality = next(
#                     (
#                         submodality
#                         for submodality in ["short_wavelength", "long_wavelength"]
#                         if submodality in file
#                     ),
#                     "unknown_submodality",
#                 )
#                 filename = f"{id}_{modality}_{submodality}_{laterality}_{uid}.dcm"

#             else:
#                 filename = f"{id}_{modality}_{laterality}_{uid}.dcm"

#             if "cirrus" in filename:
#                 modality_folder = get_description(
#                     filename, cirrus_modality_folder_mapping
#                 )
#                 submodality_folder = get_description(
#                     filename, cirrus_submodality_folder_mapping
#                 )
#                 device_folder = get_description(filename, device_folder_mapping)
#             else:
#                 modality_folder = get_description(filename, modality_folder_mapping)
#                 submodality_folder = get_description(
#                     filename, submodality_folder_mapping
#                 )
#                 device_folder = get_description(filename, device_folder_mapping)

#             folderpath = (
#                 f"/{modality_folder}/{submodality_folder}/{device_folder}/{id}/"
#             )

#             full_dir_path = output + folderpath

#             os.makedirs(full_dir_path, exist_ok=True)

#             full_file_path = os.path.join(full_dir_path, filename)

#             dataset.save_as(full_file_path)

#             return full_file_path


def update_pydicom_dicom_dictionary(file_path):
    """
    Update the DICOM dictionary with new elements if they don't already exist.

    Args:
        file_path (str): The path to the Python file containing the DICOM dictionary.

    This function imports the existing DICOM dictionary from the specified file,
    adds new elements to the dictionary if they are not already present, and writes
    the updated dictionary back to the file.

    The new elements added are:
        - 0x0022EEE0: En Face Volume Descriptor Sequence
        - 0x0022EEE1: En Face Volume Descriptor Scope
        - 0x0022EEE2: Referenced Segmentation Sequence
        - 0x0022EEE3: Surface Offset

    Returns:
        None
    """

    new_elements = {
        0x0022EEE0: (
            "SQ",
            "1",
            "En Face Volume Descriptor Sequence",
            "",
            "EnFaceVolumeDescriptorSequence",
        ),
        0x0022EEE1: (
            "CS",
            "1",
            "En Face Volume Descriptor Scope",
            "",
            "EnFaceVolumeDescriptorScope",
        ),
        0x0022EEE2: (
            "SQ",
            "1",
            "Referenced Segmentation Sequence",
            "",
            "ReferencedSegmentationSequence",
        ),
        0x0022EEE3: ("FL", "1", "Surface Offset", "", "SurfaceOffset"),
    }

    # Step 1: Import the dictionary from the .py file
    spec = importlib.util.spec_from_file_location("dictionaries", file_path)
    dicom_dict_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dicom_dict_module)

    # Get the DicomDictionary and RepeatersDictionary from the module
    DicomDictionary = dicom_dict_module.DicomDictionary
    RepeatersDictionary = dicom_dict_module.RepeatersDictionary

    # Step 2: Add new elements only if they don't exist
    for key, value in new_elements.items():
        if key not in DicomDictionary:
            DicomDictionary[key] = value

    # Step 3: Write the updated dictionary back to the .py file
    with open(file_path, "w") as file:
        file.write("DicomDictionary = {\n")
        for key, value in DicomDictionary.items():
            if isinstance(key, int):
                key_str = f"0x{key:08X}"
            else:
                key_str = str(key)
            file.write(f"    {key_str}: {value},\n")
        file.write("}\n\n")

        file.write("RepeatersDictionary = {\n")
        for key, value in RepeatersDictionary.items():
            if isinstance(key, int):
                key_str = f"0x{key:08X}"
            else:
                key_str = f"'{key}'"
            file.write(f"    {key_str}: {value},\n")
        file.write("}\n")

    print(f"DicomDictionary has been updated successfully in {file_path}.")
    
import os

# def delete_csv_files(root_folder):
#     deleted_files = []

#     for dirpath, dirnames, filenames in os.walk(root_folder):
#         for filename in filenames:
#             if filename.lower().endswith(".csv"):
#                 file_path = os.path.join(dirpath, filename)
#                 try:
#                     os.remove(file_path)
#                     deleted_files.append(file_path)
#                 except Exception as e:
#                     print(f"Failed to delete {file_path}: {e}")

#     return deleted_files



# def delete_csv_files(root_folder):
#     """
#     Delete 'fileIndex.csv' files, but only if one of the parent
#     directories in the path has 'Cirrus' (case-insensitive) in its name.

#     Args:
#         root_folder (str): Root directory to start searching.

#     Returns:
#         list: absolute paths of deleted files.
#     """
#     deleted_files = []

#     for dirpath, _, filenames in os.walk(root_folder):
#         for filename in filenames:
#             if filename == "fileIndex.csv":
#                 # break the path into folders and check each for 'cirrus'
#                 parts = os.path.normpath(dirpath).split(os.sep)
#                 if any("cirrus" in part.lower() for part in parts):
#                     file_path = os.path.join(dirpath, filename)
#                     try:
#                         os.remove(file_path)
#                         deleted_files.append(file_path)
#                         print(f"Deleted: {file_path}")
#                     except Exception as e:
#                         print(f"Failed to delete {file_path}: {e}")
#                 else:
#                     print(f"Skipped (no 'Cirrus' parent): {os.path.join(dirpath, filename)}")

#     return deleted_files

def check_critical_info_from_files_in_folder(folder):
    """
    Check for critical information in DICOM files within a folder.

    Args:
        folder (str): The path to the folder containing DICOM files.

    This function reads the first DICOM file in the specified folder and checks
    for the presence of critical information, including the SOPInstanceUID and
    PatientID. If the information is missing or invalid, it returns "critical_info_missing".
    Otherwise, it returns "pass".

    Returns:
        str: "critical_info_missing" if critical information is missing, "pass" otherwise.
    """

    files = get_filtered_file_names(folder)
    if not files:
        raise ValueError(f"No files found in folder: {folder}")

    file = files[0]

    dataset = pydicom.dcmread(file)
    try:
        uid = dataset.SOPInstanceUID
    except AttributeError:
        return "critical_info_missing"

    id = find_id(str(dataset.PatientID), str(dataset.PatientName))
    if id == "noid":
        return "critical_info_missing"

    else:
        return "pass"


import pydicom


def replace_last_three(path, a, b, c):
    filename = path.split("/")[-1]
    parts = filename.split(".")
    parts[-3:] = [a, b, c]
    new_filename = ".".join(parts)
    directory = "/".join(path.split("/")[:-1])
    return f"{directory}/{new_filename}"


# for i in [file11, file22, file33, file44]:  # , b, c, d, e, f

def get_protocol_updated(i):
    main = i
    ds = pydicom.dcmread(main)
    protocol = imaging_classifying_rules.find_rule(main)

    make_unknown = False

    # --- Check 1
    if "maestro2_3d_wide_oct" in protocol and len(ds.PrimaryAnatomicStructureSequence) == 1:
        make_unknown = True

    # --- Check 2 d
    if (
        "maestro2_mac_6x6_octa" in protocol
        and len(ds.PerFrameFunctionalGroupsSequence) != 360
    ):
        make_unknown = True

    # --- Check 3
    if "triton_3d_radial_oct" in protocol and len(ds.PrimaryAnatomicStructureSequence) == 1:
        make_unknown = True

    # --- Check 4
    if "triton_3d_radial_oct" in protocol and ds.get("LossyImageCompressionRatio") is None:
        make_unknown = True

    # --- Check 5
    if (
        "triton_macula_12x12_octa" in protocol
        and ds.get("LossyImageCompressionRatio") is None
    ):
        make_unknown = True

    # --- Check 6
    if (
        "triton_macula_6x6_octa" in protocol
        and ds.get("LossyImageCompressionRatio") is None
    ):
        make_unknown = True

    # --- Check 7 (segmentation file 7.3.dcm)
    if "triton_macula_12x12_octa" in protocol or "triton_macula_6x6_octa" in protocol:
        segmentation_path = replace_last_three(main, "7", "3", "dcm")
        if os.path.exists(segmentation_path):
            seg = pydicom.dcmread(segmentation_path)
            if len(seg.SegmentSequence) == 9:
                make_unknown = True

    # --- Check 8 (op file 2.1.dcm)
    if "triton_macula_6x6_octa" in protocol:
        op_path = replace_last_three(main, "2", "1", "dcm")
        if os.path.exists(op_path):
            op = pydicom.dcmread(op_path)
            if op.get("PixelSpacing") is None:
                make_unknown = True

    if make_unknown:
        protocol = "unknown_protocol"

    return protocol
