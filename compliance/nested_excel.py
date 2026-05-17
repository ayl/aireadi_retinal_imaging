import pydicom
import xlsxwriter


class DicomEntry:
    """
    A class representing a single DICOM entry.

    Attributes:
        tag (str): The DICOM tag (in hexadecimal) of the element.
        element_name (str): The name of the DICOM element associated with the tag.
        vr (str): The Value Representation (VR) type of the DICOM element.
        value (str or list): The value of the DICOM element.
    """

    def __init__(self, tag, element_name, vr, value):
        """
        Initializes the DicomEntry with the tag, element name, VR, and value.

        Args:
            tag (str): The DICOM tag (in hexadecimal) of the element.
            element_name (str): The name of the DICOM element.
            vr (str): The Value Representation (VR) type of the DICOM element.
            value (str or list): The value of the DICOM element.
        """
        self.tag = tag
        self.element_name = element_name
        self.vr = vr
        self.value = value


def extract_dicom_dict(file, tags):
    """
    Extracts DICOM metadata and organizes it in a nested structure for specific tags.

    Args:
        file (str): Path to the DICOM file.
        tags (list): A list of DICOM tags to extract from the file.

    Returns:
        dict: A dictionary with the following keys:
            - "indentation": Indentation strings to represent nesting levels.
            - "tag": The extracted DICOM tags.
            - "element_name": The corresponding names of the DICOM elements.
            - "vr": The Value Representation (VR) type for each tag.
            - "value": The value of the DICOM elements.
    """
    dataset = pydicom.dcmread(file)
    json_dict = dataset.to_json_dict()
    dicom = json_dict
    output_lists = {
        "indentation": [],
        "tag": [],
        "element_name": [],
        "vr": [],
        "value": [],
    }
    process_tags(tags, dicom, 0, output_lists)  # Start with nesting level 0
    return output_lists


def process_tags(tags, dicom, nesting_level, output_lists):
    """
    Processes and extracts values for specific DICOM tags and handles nested structures.

    Args:
        tags (list): A list of DICOM tags to process.
        dicom (dict): The parsed DICOM dataset as a dictionary.
        nesting_level (int): The current level of nesting (used for indentation).
        output_lists (dict): The dictionary where the output is stored, including:
            - "indentation": Indentation strings for each tag.
            - "tag": The DICOM tags.
            - "element_name": The corresponding DICOM element names.
            - "vr": The Value Representation (VR) for each tag.
            - "value": The values of the DICOM elements.

    Returns:
        None: The function modifies `output_lists` in place.
    """
    indent = ">" * nesting_level  # Indentation string based on the nesting level

    for tag in tags:
        if tag in dicom:
            element_name = pydicom.datadict.keyword_for_tag(tag)
            vr = dicom[tag]["vr"]
            value = dicom[tag].get("Value", [])

            # Create an indentation string based on the nesting level
            indentation = indent

            # Check if the value is a DicomEntry before skipping printing
            if not isinstance(value, DicomEntry):
                output_lists["indentation"].append(indentation)
                output_lists["tag"].append(tag)
                output_lists["element_name"].append(element_name)
                output_lists["vr"].append(vr)
                output_lists["value"].append(value)

            if not value or not isinstance(value[0], dict):
                output = DicomEntry(tag, element_name, vr, value)
            else:
                nested_output = []
                for item in value:
                    keys_list = list(item.keys())
                    process_tags(
                        keys_list, item, nesting_level + 1, output_lists
                    )  # Increment nesting level


def create_excelsheet_nested_structure(input, tags, output):
    """
    Creates an Excel sheet for DICOM metadata with a nested structure for specific tags.

    Args:
        input (str): The path to the DICOM file.
        tags (list): A list of DICOM tags to extract and organize in the Excel sheet.
        output (str): The file path where the output Excel file will be saved.

    Returns:
        None: The function saves the extracted DICOM metadata to an Excel file.
    """
    a = input
    output_file = output

    workbook = xlsxwriter.Workbook(output_file)

    for tag in tags:
        worksheet = workbook.add_worksheet(tag)

        tags_to_extract = [tag]  # Use the current 'tag' value in the loop
        result = extract_dicom_dict(a, tags_to_extract)

        # Assuming 'extract_dicom_dict' returns the necessary data
        # Modify the following lines accordingly if needed
        result["tags"] = [
            str(a) + b for a, b in zip(result["indentation"], result["tag"])
        ]
        result["value"] = [
            (
                ""
                if isinstance(item, list)
                and any(isinstance(subitem, dict) for subitem in item)
                else str(item)
            )
            for item in result["value"]
        ]
        result["value"] = [
            item.strip("[]") if isinstance(item, str) and "," not in item else item
            for item in result["value"]
        ]
        result["value"] = [value.strip("'") for value in result["value"]]

        worksheet.write_column("A1", result["tags"])
        worksheet.write_column("B1", result["element_name"])
        worksheet.write_column("C1", result["vr"])
        worksheet.write_column("D1", result["value"])

    workbook.close()


def multi_create_excelsheet_nested_structure(inputs, tags, output):
    """
    Creates an Excel sheet for multiple DICOM files, each with nested structures for specific tags.

    Args:
        inputs (list): A list of file paths to DICOM files to process.
        tags (list): A list of DICOM tags to extract and organize for each DICOM file.
        output (str): The file path where the output Excel file will be saved.

    Returns:
        None: The function saves the extracted metadata from multiple DICOM files to an Excel file.
    """
    aa = inputs
    output_file = output
    workbook = xlsxwriter.Workbook(output_file)

    for tag in tags:
        num = 0
        worksheet = workbook.add_worksheet(tag)
        tags_to_extract = [tag]  # Use the current 'tag' value in the loop

        for a in aa:
            num = num + 1

            result = extract_dicom_dict(a, tags_to_extract)
            # Assuming 'extract_dicom_dict' returns the necessary data
            # Modify the following lines accordingly if needed
            result["tags"] = [
                str(a) + b for a, b in zip(result["indentation"], result["tag"])
            ]
            result["value"] = [
                (
                    ""
                    if isinstance(item, list)
                    and any(isinstance(subitem, dict) for subitem in item)
                    else str(item)
                )
                for item in result["value"]
            ]
            result["value"] = [
                item.strip("[]") if isinstance(item, str) and "," not in item else item
                for item in result["value"]
            ]
            result["value"] = [value.strip("'") for value in result["value"]]

            start_column = (num - 1) * 4  # 4 columns per file

            # Write data to consecutive columns
            worksheet.write_column(1, start_column, result["tags"])
            worksheet.write_column(1, start_column + 1, result["element_name"])
            worksheet.write_column(1, start_column + 2, result["vr"])
            worksheet.write_column(1, start_column + 3, result["value"])

            worksheet.write(0, (num - 1) * 4, a)

    workbook.close()
