import enum
import os

try:
    from . import compliance_rules
except ImportError:  # pragma: no cover - keeps legacy direct script usage working
    import compliance_rules

import pydicom
import xlsxwriter


class ActionNeeded(enum.Enum):
    NONE = 0
    TAG_AND_VALUE_NEEDED = 1
    TAG_NEEDED = 2
    VALUE_NEEDED = 3
    PREFERRED = 4


class DicomEntry:
    def __init__(self, tag, name, vr, value):
        self.tag = tag
        self.name = name
        self.vr = vr
        self.value = value

    def is_empty(self):
        return len(self.value) == 0


def extract_dicom_dict(file, tags):
    if not os.path.exists(file):
        raise FileNotFoundError(f"File {file} not found.")

    dicom = pydicom.dcmread(file).to_json_dict()
    output = dict()
    output["filepath"] = file

    for tag in tags:
        if isinstance(tag, str):
            if tag in dicom:
                element_name = pydicom.tag.Tag(tag)
                vr = dicom[tag]["vr"]
                value = dicom[tag]["Value"] if "Value" in dicom[tag] else []

                output[tag] = DicomEntry(tag, element_name, vr, value)

        elif isinstance(tag, list):
            raise NotImplementedError("Nested tags not implemented yet.")

    return output


def extract_dicom_dict_extra(file, tags):
    if not os.path.exists(file):
        raise FileNotFoundError(f"File {file} not found.")

    dicom = pydicom.dcmread(file).to_json_dict()
    alltags = list(dicom.keys())

    output_extra = dict()

    for tag in alltags:
        if isinstance(tag, str) and tag not in tags:
            if tag in dicom:
                element_name = pydicom.datadict.keyword_for_tag(tag)
                vr = dicom[tag]["vr"]
                value = dicom[tag]["Value"] if "Value" in dicom[tag] else []

                output_extra[tag] = DicomEntry(tag, element_name, vr, value)

    return output_extra


def evaluate_compliance(rules, dicom_dict):
    result = dict()

    for entity in rules.entities:
        for module in entity.modules:
            for element_ref in module.elements:
                if element_ref.condition == compliance_rules.MUST_EXIST:
                    if element_ref.tag in dicom_dict:
                        if not dicom_dict[element_ref.tag].is_empty():
                            result[element_ref.tag] = ActionNeeded.NONE
                        else:
                            result[element_ref.tag] = ActionNeeded.VALUE_NEEDED
                    else:
                        result[element_ref.tag] = ActionNeeded.TAG_AND_VALUE_NEEDED

                # can be empty
                elif element_ref.condition == compliance_rules.ALLOW_EMPTY:
                    if element_ref.tag in dicom_dict:
                        result[element_ref.tag] = ActionNeeded.NONE
                    else:
                        result[element_ref.tag] = ActionNeeded.TAG_NEEDED

                # optional
                elif element_ref.condition == compliance_rules.PREFERRED:
                    result[element_ref.tag] = ActionNeeded.PREFERRED

                #conditional tag
                elif isinstance(element_ref.condition, compliance_rules.MustTagExistIf):
                    if element_ref.condition.premise in dicom_dict:
                        if element_ref.condition.condition(
                            dicom_dict[element_ref.condition.premise].value
                        ):
                            if element_ref.tag in dicom_dict:
                                result[element_ref.tag] = ActionNeeded.NONE
                            else:
                                result[
                                    element_ref.tag
                                ] = ActionNeeded.TAG_NEEDED

                        else:
                            result[element_ref.tag] = ActionNeeded.NONE
                    else:
                        result[element_ref.tag] = ActionNeeded.PREFERRED

                #conditional tag and value
                elif isinstance(element_ref.condition, compliance_rules.MustExistIf):
                    if element_ref.condition.premise in dicom_dict:
                        if element_ref.condition.condition(
                            dicom_dict[element_ref.condition.premise].value
                        ):
                            if element_ref.tag in dicom_dict:
                                if not dicom_dict[element_ref.tag].is_empty():
                                    result[element_ref.tag] = ActionNeeded.NONE
                                else:
                                    result[element_ref.tag] = ActionNeeded.VALUE_NEEDED
                            else:
                                result[
                                    element_ref.tag
                                ] = ActionNeeded.TAG_AND_VALUE_NEEDED

                        else:
                            result[element_ref.tag] = ActionNeeded.NONE
                    else:
                        result[element_ref.tag] = ActionNeeded.PREFERRED

    return result


def export_to_excel(rules, dicom_dict_list, action_list, output_file_path, file_paths):
    tags = rules.tags()
    workbook = xlsxwriter.Workbook(output_file_path)
    worksheet = workbook.add_worksheet("compliance_report")

    offset = 1

    # Write headers and file paths
    titles = ["Information Entity", "Module", "Reference", "Tag", "Element Name", "VR"]
    titles += [dicom_dict_list[i]["filepath"] for i in range(len(dicom_dict_list))]

    for index, element in enumerate(titles):
        worksheet.write(0, index, element)

    # Define cell formats for different actions
    info = workbook.add_format({"bg_color": "#0dcaf0"})  # blue color
    warning = workbook.add_format({"bg_color": "#ffc107"})  # Yellow color
    danger = workbook.add_format({"bg_color": "#dc3545"})  # red color

    for i in range(len(rules.entities)):
        entity = rules.entities[i]
        offset_a = offset

        for j in range(len(entity.modules)):
            module = entity.modules[j]
            offset_b = offset

            for k in range(len(module.elements)):
                element_ref = module.elements[k]

                worksheet.write(offset, 3, element_ref.tag)
                worksheet.write(offset, 4, element_ref.name)
                worksheet.write(offset, 5, element_ref.vr)

                for l in range(len(dicom_dict_list)):
                    records = dicom_dict_list[l]

                    cell_value = ""
                    if element_ref.tag in records:
                        cell_value = ", ".join(map(str, records[element_ref.tag].value))

                    cell_format = None
                    if (
                        action_list[l][element_ref.tag]
                        == ActionNeeded.TAG_AND_VALUE_NEEDED
                    ):
                        cell_format = danger
                        cell_value = "TAG AND VALUE NEEDED"

                    elif action_list[l][element_ref.tag] == ActionNeeded.TAG_NEEDED:
                        cell_format = danger
                        cell_value = "TAG NEEDED"

                    elif action_list[l][element_ref.tag] == ActionNeeded.VALUE_NEEDED:
                        cell_format = warning
                        cell_value = "VALUE NEEDED"

                    elif action_list[l][element_ref.tag] == ActionNeeded.PREFERRED:
                        cell_format = info

                    worksheet.write(offset, 6 + l, cell_value, cell_format)

                offset += 1

            if offset_b == offset - 1:
                worksheet.write(offset_b, 1, module.name)
                worksheet.write(offset_b, 2, module.reference)
            else:
                worksheet.merge_range(offset_b, 1, offset - 1, 1, module.name)
                worksheet.merge_range(offset_b, 2, offset - 1, 2, module.reference)

        if offset_a == offset - 1:
            worksheet.write(offset_a, 0, entity.name)
        else:
            worksheet.merge_range(offset_a, 0, offset - 1, 0, entity.name)

    bold_format = workbook.add_format({"bold": True})
    worksheet.set_row(0, None, bold_format)

    worksheet_next = workbook.add_worksheet("extra_headers")

    merge_format = workbook.add_format({"bold": True, "align": "center"})
    header_format = workbook.add_format({"bold": True})

    for col_offset, file_path in enumerate(file_paths):
        start_col = col_offset * 4
        headers = ["Tag", "Name", "VR", "Value"]

        for col, header in enumerate(headers):
            worksheet_next.write(2, start_col + col, header, header_format)

        end_col = start_col + len(headers) - 1
        worksheet_next.merge_range(1, start_col, 1, end_col, file_path, merge_format)

        dicom_entries = extract_dicom_dict_extra(file_path, tags)

        for row, entry in enumerate(dicom_entries.values(), start=3):
            col = start_col

            worksheet_next.write(row, col, entry.tag)
            worksheet_next.write(row, col + 1, entry.name)
            worksheet_next.write(row, col + 2, entry.vr)
            worksheet_next.write(row, col + 3, str(entry.value))

    num_cols = len(file_paths) * 4
    worksheet_next.merge_range(
        0, 0, 0, num_cols - 1, "Extra Tags and Information", merge_format
    )

    workbook.close()


def create_report(rules, input_files, output_file):
    dicom_dict_list = [extract_dicom_dict(file, rules.tags()) for file in input_files]
    action_list = [
        evaluate_compliance(rules, dicom_dict) for dicom_dict in dicom_dict_list
    ]
    export_to_excel(rules, dicom_dict_list, action_list, output_file, input_files)
