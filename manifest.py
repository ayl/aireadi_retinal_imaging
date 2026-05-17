import json
import os
import re

import pandas as pd
import pydicom
from ophthalmic_dicom_compliance.devices.cirrus import metadata as imaging_cirrus_metadata
from ophthalmic_dicom_compliance.devices.eidon import metadata as imaging_eidon_retinal_photography_metadata
from ophthalmic_dicom_compliance.devices.flio import metadata as imaging_flio_metadata
from ophthalmic_dicom_compliance.devices.optomed import metadata as imaging_optomed_retinal_photography_metadata
from ophthalmic_dicom_compliance.devices.spectralis import metadata as imaging_spectralis_metadata
from ophthalmic_dicom_compliance.devices.topcon import metadata as imaging_maestro2_triton_metadata
from ophthalmic_dicom_compliance.dicom import organize as organize_utils
from ophthalmic_dicom_compliance.dicom import utils as imaging_utils
from tqdm import tqdm


def replace_dots_with_underscores(sop_instance_uid):
    """
    Replace dots in SOP Instance UID with underscores.
    """
    return sop_instance_uid.replace(".", "_")


def find_matching_json_files(sop_instance_uid, imaging_type, files_list):
    """
    Find JSON files in the list that contain the modified SOP instance UID
    and include both 'segmentation' and 'cirrus' in their file name.
    """
    modified_uid = replace_dots_with_underscores(sop_instance_uid)
    pattern = rf".*{imaging_type}.*{modified_uid}.*\.json$"

    matching_files = [f for f in files_list if re.search(pattern, f, re.IGNORECASE)]

    return matching_files


def get_json_filenames(folder_path):
    json_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            # Check if the file ends with .json and doesn't start with a dot
            if file.endswith(".json") and not file.startswith("."):
                # Append the full path by joining root and file
                full_path = os.path.join(root, file)
                json_files.append(full_path)

    return json_files

# Function to read JSON file and get the 'file_path'
def get_item_from_json(file_path, item):
    with open(file_path, "r") as dic:
        json_data = json.load(dic)

        flattened_data = [value for key, value in json_data.items()]

        df = pd.DataFrame(flattened_data)
        item = str(df[f"{item}"].iloc[0])

        return item


def process_enface(file):
    file_path = get_item_from_json(file, "filepath")
    sop_instance = get_item_from_json(file, "sop_instance_uid")
    try:
        ophthalmic_image_type = get_item_from_json(file, "ophthalmic_image_type")

    except:
        ophthalmic_image_type = get_item_from_json(file, "Ophthalmic_image_type")

    if "cirrus" in file:
        surface1 = "Not reported"
        surface2 = "Not reported"

    else:
        surface1 = get_item_from_json(file, "en_face_retinal_segmentation_surface_1")
        surface2 = get_item_from_json(file, "en_face_retinal_segmentation_surface_2")
        if surface2 == "":
            surface2 = "Not reported"

    # Return a dictionary with the relevant keys and values
    return {
        "file_path": file_path,
        "sop_instance_uid": sop_instance,
        "ophthalmic_image_type": ophthalmic_image_type,
        "surface1": surface1,
        "surface2": surface2,
    }



def process_cirrus_file(file, imaging_folder, metadata_folder):

    files = get_json_filenames(f"{metadata_folder}/retinal_octa")
    op = f"{imaging_folder}/retinal_photography/manifest.tsv"
    opt = f"{imaging_folder}/retinal_oct/manifest.tsv"
    input_op_df = pd.read_csv(op, sep="\t")
    input_opt_df = pd.read_csv(opt, sep="\t")

    with open(file, "r") as dic:
        json_data = json.load(dic)

        flattened_data = [value for key, value in json_data.items()]

        # Convert the flattened data into a DataFrame
        df = pd.DataFrame(flattened_data)

        op_uid = str(df["op_reference_instance_uid"].iloc[0])
        opt_uid = str(df["oct_reference_instance_uid"].iloc[0])
        vol_uid = str(df["vol_reference_instance_uid"].iloc[0])
        seg_uid = str(df["seg_reference_instance_uid"].iloc[0])

        df.loc[:, "associated_flow_cube_sop_instance_uid"] = vol_uid
        df.loc[:, "associated_segmentation_sop_instance_uid"] = seg_uid
        df.loc[:, "associated_retinal_photography_sop_instance_uid"] = op_uid
        df.loc[:, "associated_structural_oct_sop_instance_uid"] = opt_uid

        # op
        op_filepath = (
            df["op_reference_instance_uid"]
            .map(input_op_df.set_index("sop_instance_uid")["filepath"])
            .iloc[0]
        )

        df.loc[:, "associated_retinal_photography_file_path"] = op_filepath

        # opt
        opt_filepath = (
            df["oct_reference_instance_uid"]
            .map(input_opt_df.set_index("sop_instance_uid")["filepath"])
            .iloc[0]
        )
        opt_anatomic_region = (
            df["oct_reference_instance_uid"]
            .map(input_opt_df.set_index("sop_instance_uid")["anatomic_region"])
            .iloc[0]
        )

        df.loc[:, "associated_structural_oct_file_path"] = opt_filepath
        df.loc[:, "anatomic_region"] = opt_anatomic_region

        # seg
        seg_file = find_matching_json_files(seg_uid, "segmentation", files)
        seg_file_path = get_item_from_json(seg_file[0], "filepath")
        seg_slices = get_item_from_json(seg_file[0], "number_of_frames")
        df.loc[:, "associated_segmentation_file_path"] = seg_file_path
        df.loc[:, "associated_segmentation_number_of_frames"] = seg_slices
        df.loc[:, "associated_segmentation_type"] = "Heightmap"

        # vol
        vol_file = find_matching_json_files(vol_uid, "flow_cube", files)
        vol_file_path = get_item_from_json(vol_file[0], "filepath")
        vol_file_participant_id = get_item_from_json(vol_file[0], "person_id")
        vol_file_manufacturer = get_item_from_json(vol_file[0], "manufacturer")
        vol_file_manufacturers_model_name = get_item_from_json(
            vol_file[0], "manufacturers_model_name"
        )

        vol_file_imaging = get_item_from_json(vol_file[0], "modality")
        vol_file_laterality = get_item_from_json(vol_file[0], "laterality")
        vol_file_height = get_item_from_json(vol_file[0], "height")
        vol_file_width = get_item_from_json(vol_file[0], "width")
        vol_file_number_of_frames = get_item_from_json(vol_file[0], "number_of_frames")

        df.loc[:, "flow_cube_file_path"] = vol_file_path
        df.loc[:, "flow_cube_sop_instance_uid"] = vol_uid
        df.loc[:, "person_id"] = vol_file_participant_id
        df.loc[:, "manufacturer"] = vol_file_manufacturer.capitalize()
        df.loc[:, "manufacturers_model_name"] = (
            vol_file_manufacturers_model_name.capitalize()
        )
        df.loc[:, "imaging"] = vol_file_imaging.upper()
        df.loc[:, "laterality"] = vol_file_laterality.capitalize()
        df.loc[:, "flow_cube_height"] = vol_file_height
        df.loc[:, "flow_cube_width"] = vol_file_width
        df.loc[:, "flow_cube_number_of_frames"] = vol_file_number_of_frames
        # df.loc[:, "associated_flow_cube_raw_data_sop_instance_uid"] = "Not reported"
        # df.loc[:, "associated_flow_cube_raw_data_file_path"] = "Not reported"

        # enface1
        enface1 = file
        result = process_enface(enface1)
        df.loc[:, "associated_enface_1_file_path"] = result["file_path"]
        df.loc[:, "associated_enface_1_sop_instance_uid"] = result["sop_instance_uid"]
        df.loc[:, "associated_enface_1_ophthalmic_image_type"] = result[
            "ophthalmic_image_type"
        ].capitalize()
        df.loc[:, "associated_enface_1_segmentation_surface_1"] = result[
            "surface1"
        ].capitalize()
        df.loc[:, "associated_enface_1_segmentation_surface_2"] = result[
            "surface2"
        ].capitalize()

        # enface2
        enface2 = file[:-10] + "2" + file[-9:]
        result = process_enface(enface2)
        df.loc[:, "associated_enface_2_file_path"] = result["file_path"]
        df.loc[:, "associated_enface_2_sop_instance_uid"] = result["sop_instance_uid"]
        df.loc[:, "associated_enface_2_ophthalmic_image_type"] = result[
            "ophthalmic_image_type"
        ].capitalize()
        df.loc[:, "associated_enface_2_segmentation_surface_1"] = result[
            "surface1"
        ].capitalize()
        df.loc[:, "associated_enface_2_segmentation_surface_2"] = result[
            "surface2"
        ].capitalize()

        enface2_projection = (file[:-10] + "3" + file[-9:]).replace(
            "enface", "enface_projection_removed"
        )
        result = process_enface(enface2_projection)
        df.loc[:, "associated_enface_2_projection_removed_filepath"] = result[
            "file_path"
        ]
        df.loc[:, "associated_enface_2_projection_removed_sop_instance_uid"] = result[
            "sop_instance_uid"
        ]

        # enface3file
        enface3 = file[:-10] + "6" + file[-9:]
        result = process_enface(enface3)
        df.loc[:, "associated_enface_3_file_path"] = result["file_path"]
        df.loc[:, "associated_enface_3_sop_instance_uid"] = result["sop_instance_uid"]
        df.loc[:, "associated_enface_3_ophthalmic_image_type"] = result[
            "ophthalmic_image_type"
        ].capitalize()
        df.loc[:, "associated_enface_3_segmentation_surface_1"] = result[
            "surface1"
        ].capitalize()
        df.loc[:, "associated_enface_3_segmentation_surface_2"] = result[
            "surface2"
        ].capitalize()

        enface3_projection = (file[:-10] + "7" + file[-9:]).replace(
            "enface", "enface_projection_removed"
        )

        result = process_enface(enface3_projection)
        df.loc[:, "associated_enface_3_projection_removed_filepath"] = result[
            "file_path"
        ]
        df.loc[:, "associated_enface_3_projection_removed_sop_instance_uid"] = result[
            "sop_instance_uid"
        ]

        # enface4
        enface4 = file[:-10] + "4" + file[-9:]
        result = process_enface(enface4)
        df.loc[:, "associated_enface_4_file_path"] = result["file_path"]
        df.loc[:, "associated_enface_4_sop_instance_uid"] = result["sop_instance_uid"]
        df.loc[:, "associated_enface_4_ophthalmic_image_type"] = result[
            "ophthalmic_image_type"
        ].capitalize()
        df.loc[:, "associated_enface_4_segmentation_surface_1"] = result[
            "surface1"
        ].capitalize()
        df.loc[:, "associated_enface_4_segmentation_surface_2"] = result[
            "surface2"
        ].capitalize()

        enface4_projection = (file[:-10] + "5" + file[-9:]).replace(
            "enface", "enface_projection_removed"
        )
        result = process_enface(enface4_projection)
        df.loc[:, "associated_enface_4_projection_removed_filepath"] = result[
            "file_path"
        ]
        df.loc[:, "associated_enface_4_projection_removed_sop_instance_uid"] = result[
            "sop_instance_uid"
        ]

        columns_to_keep = [
            "person_id",
            "manufacturer",
            "manufacturers_model_name",
            "anatomic_region",
            "imaging",
            "laterality",
            "flow_cube_height",
            "flow_cube_width",
            "flow_cube_number_of_frames",
            "associated_segmentation_type",
            "associated_segmentation_number_of_frames",
            "associated_enface_1_ophthalmic_image_type",
            "associated_enface_1_segmentation_surface_1",
            "associated_enface_1_segmentation_surface_2",
            "associated_enface_2_ophthalmic_image_type",
            "associated_enface_2_segmentation_surface_1",
            "associated_enface_2_segmentation_surface_2",
            "associated_enface_3_ophthalmic_image_type",
            "associated_enface_3_segmentation_surface_1",
            "associated_enface_3_segmentation_surface_2",
            "associated_enface_4_ophthalmic_image_type",
            "associated_enface_4_segmentation_surface_1",
            "associated_enface_4_segmentation_surface_2",
            "flow_cube_sop_instance_uid",
            "flow_cube_file_path",
            # "associated_flow_cube_raw_data_sop_instance_uid",
            # "associated_flow_cube_raw_data_file_path",
            "associated_retinal_photography_sop_instance_uid",
            "associated_retinal_photography_file_path",
            "associated_structural_oct_sop_instance_uid",
            "associated_structural_oct_file_path",
            "associated_segmentation_sop_instance_uid",
            "associated_segmentation_file_path",
            "associated_enface_1_sop_instance_uid",
            "associated_enface_1_file_path",
            "associated_enface_2_sop_instance_uid",
            "associated_enface_2_file_path",
            "associated_enface_2_projection_removed_sop_instance_uid",
            "associated_enface_2_projection_removed_filepath",
            "associated_enface_3_sop_instance_uid",
            "associated_enface_3_file_path",
            "associated_enface_3_projection_removed_sop_instance_uid",
            "associated_enface_3_projection_removed_filepath",
            "associated_enface_4_sop_instance_uid",
            "associated_enface_4_file_path",
            "associated_enface_4_projection_removed_sop_instance_uid",
            "associated_enface_4_projection_removed_filepath",
        ]

        # Filter DataFrame to keep only these columns
        df_filtered = df[columns_to_keep]

        return df_filtered
    
def process_topcon_file(seg, imaging_folder, metadata_folder):


    files = get_json_filenames(f"{metadata_folder}/retinal_octa")
    op = f"{imaging_folder}/retinal_photography/manifest.tsv"
    opt = f"{imaging_folder}/retinal_oct/manifest.tsv"
    input_op_df = pd.read_csv(op, sep="\t")
    input_opt_df = pd.read_csv(opt, sep="\t")

    with open(seg, "r") as dic:
        json_data = json.load(dic)
        flattened_data = [value for key, value in json_data.items()]
        df = pd.DataFrame(flattened_data)

        seg_uid = str(df["sop_instance_uid"].iloc[0])
        op_uid =  ".".join(seg_uid.split(".")[:-2] + ["2", "1"])
        opt_uid = ".".join(seg_uid.split(".")[:-2] + ["1", "1"])
        vol_uid = ".".join(seg_uid.split(".")[:-2] + ["3", "1"])


        df.loc[:, "associated_flow_cube_sop_instance_uid"] = vol_uid
        df.loc[:, "associated_segmentation_sop_instance_uid"] = seg_uid
        df.loc[:, "associated_retinal_photography_sop_instance_uid"] = op_uid
        df.loc[:, "associated_structural_oct_sop_instance_uid"] = opt_uid

        # op_filepath = input_op_df.set_index("sop_instance_uid").loc[op_uid, "filepath"]
        try:
            op_filepath = (
                input_op_df.set_index("sop_instance_uid")
                .loc[op_uid, "filepath"]
            )
        except KeyError:
            op_filepath = "Not Provided"
            print(f"{op_uid} unavailable")

        opt_filepath = input_opt_df.set_index("sop_instance_uid").loc[opt_uid, "filepath"]
        opt_anatomic_region = input_opt_df.set_index("sop_instance_uid").loc[opt_uid, "anatomic_region"]

        df.loc[:, "associated_retinal_photography_file_path"] = op_filepath
        df.loc[:, "associated_structural_oct_file_path"] = opt_filepath
        df.loc[:, "anatomic_region"] = opt_anatomic_region.capitalize()


        # seg
        seg_file = find_matching_json_files(seg_uid, "segmentation", files)
        seg_file_path = get_item_from_json(seg_file[0], "filepath")

        seg_slices = get_item_from_json(seg_file[0], "number_of_frames")
        df.loc[:, "associated_segmentation_file_path"] = seg_file_path
        df.loc[:, "associated_segmentation_number_of_frames"] = seg_slices
        df.loc[:, "associated_segmentation_type"] = "Heightmap"

        # vol
        vol_file = find_matching_json_files(vol_uid, "flow_cube", files)
        vol_file_path = get_item_from_json(vol_file[0], "filepath")
        vol_file_participant_id = get_item_from_json(vol_file[0], "person_id")
        vol_file_manufacturer = get_item_from_json(vol_file[0], "manufacturer")
        vol_file_manufacturers_model_name = get_item_from_json(
            vol_file[0], "manufacturers_model_name"
        )

        vol_file_imaging = get_item_from_json(vol_file[0], "modality")
        vol_file_laterality = get_item_from_json(vol_file[0], "laterality")
        vol_file_height = get_item_from_json(vol_file[0], "height")
        vol_file_width = get_item_from_json(vol_file[0], "width")
        vol_file_number_of_frames = get_item_from_json(vol_file[0], "number_of_frames")

        df.loc[:, "flow_cube_file_path"] = vol_file_path
        df.loc[:, "flow_cube_sop_instance_uid"] = vol_uid
        df.loc[:, "person_id"] = vol_file_participant_id
        df.loc[:, "manufacturer"] = vol_file_manufacturer.capitalize()
        df.loc[:, "manufacturers_model_name"] = (
            vol_file_manufacturers_model_name.capitalize()
        )
        df.loc[:, "imaging"] = vol_file_imaging.upper()
        df.loc[:, "laterality"] = vol_file_laterality.capitalize()
        df.loc[:, "flow_cube_height"] = vol_file_height
        df.loc[:, "flow_cube_width"] = vol_file_width
        df.loc[:, "flow_cube_number_of_frames"] = vol_file_number_of_frames

        enface4_uid = ".".join(seg_uid.split(".")[:-2] + ["6", "80"])
        try:
            enface4 = find_matching_json_files(enface4_uid, "enface", files)[0]
        except IndexError:
            enface4 = None

        enface3_uid = enface4_uid[:-2] + "5"
        try:
            enface3 = find_matching_json_files(enface3_uid, "enface", files)[0]
        except IndexError:
            enface3 = None

        enface1_uid = enface4_uid[:-2] + "3"
        try:
            enface1 = find_matching_json_files(enface1_uid, "enface", files)[0]
        except IndexError:
            enface1 = None

        enface2_uid = enface4_uid[:-2] + "4"
        try:
            enface2 = find_matching_json_files(enface2_uid, "enface", files)[0]
        except IndexError:
            enface2 = None

        if enface1:
            result = process_enface(enface1)
            df.loc[:, "associated_enface_1_file_path"] = result["file_path"]
            df.loc[:, "associated_enface_1_sop_instance_uid"] = result[
                "sop_instance_uid"
            ]
            df.loc[:, "associated_enface_1_ophthalmic_image_type"] = result[
                "ophthalmic_image_type"
            ].capitalize()
            df.loc[:, "associated_enface_1_segmentation_surface_1"] = result[
                "surface1"
            ].capitalize()
            df.loc[:, "associated_enface_1_segmentation_surface_2"] = result[
                "surface2"
            ].capitalize()

        else:  # This is the part that handles when enface1 is None or falsy
            df.loc[:, "associated_enface_1_file_path"] = "Not reported"
            df.loc[:, "associated_enface_1_sop_instance_uid"] = "Not reported"
            df.loc[:, "associated_enface_1_ophthalmic_image_type"] = "Not reported"
            df.loc[:, "associated_enface_1_segmentation_surface_1"] = "Not reported"
            df.loc[:, "associated_enface_1_segmentation_surface_2"] = "Not reported"

        # enface2
        if enface2:
            result = process_enface(enface2)
            df.loc[:, "associated_enface_2_file_path"] = result["file_path"]
            df.loc[:, "associated_enface_2_sop_instance_uid"] = result[
                "sop_instance_uid"
            ]
            df.loc[:, "associated_enface_2_ophthalmic_image_type"] = result[
                "ophthalmic_image_type"
            ].capitalize()
            df.loc[:, "associated_enface_2_segmentation_surface_1"] = result[
                "surface1"
            ].capitalize()
            df.loc[:, "associated_enface_2_segmentation_surface_2"] = result[
                "surface2"
            ].capitalize()

        else:
            df.loc[:, "associated_enface_2_file_path"] = "Not reported"
            df.loc[:, "associated_enface_2_sop_instance_uid"] = "Not reported"
            df.loc[:, "associated_enface_2_ophthalmic_image_type"] = "Not reported"
            df.loc[:, "associated_enface_2_segmentation_surface_1"] = "Not reported"
            df.loc[:, "associated_enface_2_segmentation_surface_2"] = "Not reported"

        df.loc[:, "associated_enface_2_projection_removed_filepath"] = "Not reported"
        df.loc[:, "associated_enface_2_projection_removed_sop_instance_uid"] = (
            "Not reported"
        )

        # enface3
        if enface3:

            result = process_enface(enface3)
            df.loc[:, "associated_enface_3_file_path"] = result["file_path"]
            df.loc[:, "associated_enface_3_sop_instance_uid"] = result[
                "sop_instance_uid"
            ]
            df.loc[:, "associated_enface_3_ophthalmic_image_type"] = result[
                "ophthalmic_image_type"
            ].capitalize()
            df.loc[:, "associated_enface_3_segmentation_surface_1"] = result[
                "surface1"
            ].capitalize()
            df.loc[:, "associated_enface_3_segmentation_surface_2"] = result[
                "surface2"
            ].capitalize()

        else:
            df.loc[:, "associated_enface_3_file_path"] = "Not reported"
            df.loc[:, "associated_enface_3_sop_instance_uid"] = "Not reported"
            df.loc[:, "associated_enface_3_ophthalmic_image_type"] = "Not reported"
            df.loc[:, "associated_enface_3_segmentation_surface_1"] = "Not reported"
            df.loc[:, "associated_enface_3_segmentation_surface_2"] = "Not reported"

        df.loc[:, "associated_enface_3_projection_removed_filepath"] = "Not reported"
        df.loc[:, "associated_enface_3_projection_removed_sop_instance_uid"] = (
            "Not reported"
        )

        # enface4
        if enface4:

            result = process_enface(enface4)
            df.loc[:, "associated_enface_4_file_path"] = result["file_path"]
            df.loc[:, "associated_enface_4_sop_instance_uid"] = result[
                "sop_instance_uid"
            ]
            df.loc[:, "associated_enface_4_ophthalmic_image_type"] = result[
                "ophthalmic_image_type"
            ].capitalize()
            df.loc[:, "associated_enface_4_segmentation_surface_1"] = result[
                "surface1"
            ].capitalize()
            df.loc[:, "associated_enface_4_segmentation_surface_2"] = result[
                "surface2"
            ].capitalize()

        else:

            df.loc[:, "associated_enface_4_file_path"] = "Not reported"
            df.loc[:, "associated_enface_4_sop_instance_uid"] = "Not reported"
            df.loc[:, "associated_enface_4_ophthalmic_image_type"] = "Not reported"
            df.loc[:, "associated_enface_4_segmentation_surface_1"] = "Not reported"
            df.loc[:, "associated_enface_4_segmentation_surface_2"] = "Not reported"

        df.loc[:, "associated_enface_4_projection_removed_filepath"] = "Not reported"
        df.loc[:, "associated_enface_4_projection_removed_sop_instance_uid"] = (
            "Not reported"
        )

        columns_to_keep = [
            "person_id",
            "manufacturer",
            "manufacturers_model_name",
            "anatomic_region",
            "imaging",
            "laterality",
            "flow_cube_height",
            "flow_cube_width",
            "flow_cube_number_of_frames",
            "associated_segmentation_type",
            "associated_segmentation_number_of_frames",
            "associated_enface_1_ophthalmic_image_type",
            "associated_enface_1_segmentation_surface_1",
            "associated_enface_1_segmentation_surface_2",
            "associated_enface_2_ophthalmic_image_type",
            "associated_enface_2_segmentation_surface_1",
            "associated_enface_2_segmentation_surface_2",
            "associated_enface_3_ophthalmic_image_type",
            "associated_enface_3_segmentation_surface_1",
            "associated_enface_3_segmentation_surface_2",
            "associated_enface_4_ophthalmic_image_type",
            "associated_enface_4_segmentation_surface_1",
            "associated_enface_4_segmentation_surface_2",
            "flow_cube_sop_instance_uid",
            "flow_cube_file_path",
            # "associated_flow_cube_raw_data_sop_instance_uid",
            # "associated_flow_cube_raw_data_file_path",
            "associated_retinal_photography_sop_instance_uid",
            "associated_retinal_photography_file_path",
            "associated_structural_oct_sop_instance_uid",
            "associated_structural_oct_file_path",
            "associated_segmentation_sop_instance_uid",
            "associated_segmentation_file_path",
            "associated_enface_1_sop_instance_uid",
            "associated_enface_1_file_path",
            "associated_enface_2_sop_instance_uid",
            "associated_enface_2_file_path",
            "associated_enface_2_projection_removed_sop_instance_uid",
            "associated_enface_2_projection_removed_filepath",
            "associated_enface_3_sop_instance_uid",
            "associated_enface_3_file_path",
            "associated_enface_3_projection_removed_sop_instance_uid",
            "associated_enface_3_projection_removed_filepath",
            "associated_enface_4_sop_instance_uid",
            "associated_enface_4_file_path",
            "associated_enface_4_projection_removed_sop_instance_uid",
            "associated_enface_4_projection_removed_filepath",
        ]

        # Filter DataFrame to keep only these columns
        df_filtered = df[columns_to_keep]

        return df_filtered
    
import math
import re

import pandas as pd
from joblib import Parallel, delayed
from tqdm import tqdm


# Split a list into 'n' equal parts
def split_list(lst, n):
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n)]


def process_sublist(sublist, sublist_index, imaging_folder):
    metadata_folder = f"{imaging_folder}_metadata"
    df_combined = pd.DataFrame()

    # Process each file in the sublist
    for file in tqdm(sublist, desc=f"Processing sublist {sublist_index}"):
        if "maestro2" in file or "triton" in file:
            df = process_topcon_file(file, imaging_folder, metadata_folder)
        elif "cirrus" in file:
            df = process_cirrus_file(file, imaging_folder, metadata_folder)
        else:
            print("Unknown file type", f"File: {file}")
            continue
        df_combined = pd.concat([df_combined, df], ignore_index=True)

    # Save the result as a TSV file
    df_combined.to_csv(
        f"{imaging_folder}/retinal_octa/manifest_{sublist_index}.tsv",
        sep="\t",
        index=False,
    )
    return f"Sublist {sublist_index} processed and saved."

import glob

import pandas as pd


def octa_manifest(imaging_folder):
    metadata_folder = f"{imaging_folder}_metadata"

    files = get_json_filenames(f"{metadata_folder}/retinal_octa")
    print(len(files))

    retinal_octa = "retinal_octa"

    # Patterns for Cirrus and Topcon (Maestro/Triton)
    cirrus_pattern = r".*cirrus.*enface.*1_dcm\.json$"
    topcon_pattern = r".*(maestro2|triton).*segmentation.*7_3_dcm\.json$"

    # Filter the list of files
    cirrus_filtered_files = [
        f for f in files if re.search(cirrus_pattern, f, re.IGNORECASE)
    ]
    topcon_filtered_files = [
        f for f in files if re.search(topcon_pattern, f, re.IGNORECASE)
    ]


    # Merge the two filtered lists
    merged_files = cirrus_filtered_files + topcon_filtered_files

    # Define number of sublists
    num_sublists = 5

    merged_split_lists = split_list(merged_files, num_sublists)

    # Print the length of each sublist
    for i in range(num_sublists):
        print(f"Sublist {i + 1}: {len(merged_split_lists[i])} files")

    Parallel(n_jobs=-1)(
        delayed(process_sublist)(sublist, sublist_index, imaging_folder)
        for sublist_index, sublist in enumerate(merged_split_lists)
    )
    all_files = glob.glob(f"{imaging_folder}/retinal_octa/manifest_*.tsv")
    df_list = [pd.read_csv(file, sep="\t") for file in all_files]
    final_df = pd.concat(df_list, ignore_index=True)

    for file in all_files:
        os.remove(file)

    col_to_insert_after = "associated_segmentation_file_path"

    # Find the insertion index (position after the given column)
    insert_idx =  final_df.columns.get_loc(col_to_insert_after) + 1

    # Insert columns with default value "Not reported"
    final_df.insert(insert_idx, "variant_segmentation_sop_instance_uid", "Not reported")
    final_df.insert(insert_idx + 1, "variant_segmentation_file_path", "Not reported")

    final_df = final_df.drop_duplicates()

    # Save the final combined DataFrame as a single TSV file
    final_df.to_csv(
        f"{imaging_folder}/retinal_octa/manifest.tsv", sep="\t", index=False
    )



def create_metadata(imaging_folder):
    metadata_folder = f"{imaging_folder}_metadata"
    os.makedirs(metadata_folder, exist_ok=True)
    print("foldermade")

    files = organize_utils.get_dcm_files(imaging_folder)
    print(len(files))

    for file in tqdm(files):

        if "spectralis" in file:
            imaging_spectralis_metadata.meta_data_save(file, metadata_folder)

        elif "cirrus" in file:
            imaging_cirrus_metadata.meta_data_save(file, metadata_folder)

        elif "flio" in file:
            imaging_flio_metadata.meta_data_save(file, metadata_folder)

        elif "optomed" in file:
            imaging_optomed_retinal_photography_metadata.meta_data_save(
                file, metadata_folder
            )

        elif "eidon" in file:
            imaging_eidon_retinal_photography_metadata.meta_data_save(file, metadata_folder)

        elif "maestro" in file or "triton" in file:
            imaging_maestro2_triton_metadata.meta_data_save(file, metadata_folder)

        else:
            print("file's device not identified")
            print(file)



def make_retinal_photography_manifest(imaging_folder):
    metadata_folder = f"{imaging_folder}_metadata"


    retinal_photography = "retinal_photography"

    files = get_json_filenames(f"{metadata_folder}/{retinal_photography}")

    data = []

    for json_file in tqdm(files):
        with open(json_file, "r") as file:
            json_data = json.load(file)

            flattened_data = [value for key, value in json_data.items()]

            df = pd.DataFrame(flattened_data)

            df_filtered = df[
                [
                    "person_id",
                    "manufacturer",
                    "manufacturers_model_name",
                    "laterality",
                    "anatomic_region",
                    "imaging",
                    "height",
                    "width",
                    "color_channel_dimension",
                    "sop_instance_uid",
                    "filepath",
                ]
            ]

            data.append(df_filtered)

    # Concatenate all DataFrames in the list into one large DataFrame
    final_df = pd.concat(data, ignore_index=True)
    final_df = final_df.sort_values(by=["person_id", "filepath"])
    op = f"{imaging_folder}/retinal_photography/manifest.tsv"
    final_df.to_csv(op, sep="\t", index=False)

    return op, metadata_folder

def make_retinal_oct_manifest(op, imaging_folder):

    metadata_folder = f"{imaging_folder}_metadata"

    retinal_oct = "retinal_oct"
    input_op = op

    # Load the input_op TSV file
    input_df = pd.read_csv(input_op, sep="\t")

    files = get_json_filenames(f"{metadata_folder}/{retinal_oct}")

    # Read JSON files and make a DataFrame
    data = []

    for json_file in tqdm(files):
        with open(json_file, "r") as file:
            json_data = json.load(file)

            flattened_data = [value for key, value in json_data.items()]

            # Convert the flattened data into a DataFrame
            df = pd.DataFrame(flattened_data)


            # Filter specific columns
            df_filtered = df[
                [
                    "person_id",
                    "manufacturer",
                    "manufacturers_model_name",
                    "anatomic_region",
                    "imaging",
                    "laterality",
                    "height",
                    "width",
                    "number_of_frames",
                    "pixel_spacing",
                    "slice_thickness",
                    "sop_instance_uid",
                    "filepath",
                    "reference_retinal_photography_image_instance_uid",
                ]
            ].copy()

            #  Add the "reference_filepath" by matching "reference_instance_uid" with the "sop_instance_uid" in input_op
            df_filtered.loc[:, "reference_filepath"] = df_filtered[
                "reference_retinal_photography_image_instance_uid"
            ].map(input_df.set_index("sop_instance_uid")["filepath"])

            df_filtered.rename(
                columns={
                    "reference_retinal_photography_image_instance_uid": "reference_instance_uid"
                },
                inplace=True,
            )

            data.append(df_filtered)

    final_df = pd.concat(data, ignore_index=True)
    final_df = final_df.sort_values(by=["person_id", "filepath"])

    opt = f"{imaging_folder}/retinal_oct/manifest.tsv"
    final_df.to_csv(
        opt,
        sep="\t",
        index=False,
    )


def make_flio_manifest(imaging_folder):
    metadata_folder = f"{imaging_folder}_metadata"
    retinal_flio = "retinal_flio"

    files = get_json_filenames(f"{metadata_folder}/{retinal_flio}")

    # Read JSON files and make a DataFrame
    data = []

    for json_file in tqdm(files):
        with open(json_file, "r") as file:
            json_data = json.load(file)

            flattened_data = [value for key, value in json_data.items()]

            # Step 2: Convert the flattened data into a DataFrame
            df = pd.DataFrame(flattened_data)

            df_filtered = df[
                [
                    "person_id",
                    "manufacturer",
                    "manufacturers_model_name",
                    "laterality",
                    "wavelength",
                    "height",
                    "width",
                    "number_of_frames",
                    "sop_instance_uid",
                    "filepath",
                ]
            ]

            # Step 4: Append the filtered DataFrame to the data list
            data.append(df_filtered)

    # Step 5: Concatenate all DataFrames in the list into one large DataFrame
    final_df = pd.concat(data, ignore_index=True)
    final_df = final_df.sort_values(by=["person_id", "filepath"])
    flio = f"{imaging_folder}/retinal_flio/manifest.tsv"
    final_df.to_csv(
        flio,
        sep="\t",
        index=False,
    )
