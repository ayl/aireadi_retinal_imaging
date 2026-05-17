class ComplianceRules:
    def __init__(self, name, entities):
        self.name = name
        self.entities = entities

    def tags(self):
        tags = set()
        for entity in self.entities:
            for module in entity.modules:
                for element in module.elements:
                    tags.add(element.tag)

        return list(tags)


class Entity:
    def __init__(self, name, modules):
        self.name = name
        self.modules = modules


class Module:
    def __init__(self, name, reference, elements):
        self.name = name
        self.reference = reference
        self.elements = elements


class Element:
    def __init__(self, name, tag, vr, condition=0):
        self.tag = tag
        self.name = name
        self.vr = vr
        self.condition = condition

#value exist
MUST_EXIST = 0
ALLOW_EMPTY = 1
PREFERRED = 2

class MustTagExistIf:
    def __init__(self, premise, condition):
        self.premise = premise
        self.condition = condition

class MustExistIf:
    def __init__(self, premise, condition):
        self.premise = premise
        self.condition = condition


cfp_ir_rule = ComplianceRules(
    "CFP IR",
    [
        Entity(
            "Patient",
            [
                Module(
                    "Patient",
                    "C.7.1.1",
                    [
                        Element("PatientName", "00100010", "PN", ALLOW_EMPTY),
                        Element("PatientID", "00100020", "LO", ALLOW_EMPTY),
                        Element("PatientBirthDate", "00100030", "DA", ALLOW_EMPTY),
                        Element("PatientSex", "00100040", "CS", ALLOW_EMPTY),
                    ],
                )
            ],
        ),
        Entity(
            "Study",
            [
                Module(
                    "General Study",
                    "C.7.2.1",
                    [
                        Element("StudyInstanceUID", "0020000D", "UI"),
                        Element("StudyDate", "00080020", "DM", ALLOW_EMPTY),
                        Element("StudyTime", "00080030", "TM", ALLOW_EMPTY),
                        Element(
                            "ReferringPhysicianName", "00080090", "PN", ALLOW_EMPTY
                        ),
                        Element("StudyID", "00200010", "SH", ALLOW_EMPTY),
                        Element("AccessionNumber", "00080050", "SH", ALLOW_EMPTY),
                        
                    ],
                )
            ],
        ),
        Entity(
            "Series",
            [
                Module(
                    "General Series",
                    "C.7.3.1",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesInstanceUID", "0020000E", "UI"),
                        Element("SeriesNumber", "00200011", "IS", ALLOW_EMPTY),
                    ],
                ),
                Module(
                    "Ophthalmic Photography Series",
                    "C.8.17.1",
                    [
                        Element("Modality", "00080060", "CS"),
                    ],
                ),
            ],
        ),
        Entity(
            "Frame of Reference",
            [
                Module(
                    "Synchronization",
                    "C.7.4.2",
                    [
                        Element("SynchronizationFrameOfReferenceUID", "00200200", "UI"),
                        Element("SynchronizationTrigger", "0018106A", "CS"),
                        Element("AcquisitionTimeSynchronized", "00181800", "CS"),
                    ],
                ),
            ],
        ),
        Entity(
            "Equipment",
            [
                Module(
                    "General Equipment",
                    "7.5.1",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                    ],
                ),
                Module(
                    "Enhanced Equipment Module",
                    "C.7.5.2",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                        Element("ManufacturerModelName", "00081090", "LO"),
                        Element("DeviceSerialNumber", "00181000", "LO"),
                        Element("SoftwareVersions", "00181020", "LO"),
                    ],
                ),
            ],
        ),
        Entity(
            "Image",
            [
                Module(
                    "General Image",
                    "C.7.6.1",
                    [
                        Element("InstanceNumber", "00200013", "IS", ALLOW_EMPTY),
                        Element("PatientOrientation", "00200020", "CS", ALLOW_EMPTY),
                        Element("BurnedInAnnotation", "00280301", "CS"),
                    ],
                ),

                 Module(
                    "Image Pixel",
                    "C.7.6.3",
                    [
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("Rows", "00280010", "US"),
                        Element("Columns", "00280011", "US"),
                        Element("BitsAllocated", "00280100", "US"),
                        Element("BitsStored", "00280101", "US"),
                        Element("HighBit", "00280102", "US"),
                        Element("PixelRepresentation", "00280103", "US"),
                        Element("PixelData", "7FE00010", "OB or OW", ALLOW_EMPTY), 
                        Element(
                            "PlanarConfiguration",
                            "00280006",
                            "US",
                            MustExistIf(
                                "00280002",
                                lambda v: int(v[0]) > 1
                                if isinstance(v, list) and len(v) > 0 and int(v[0]) > 1
                                else False,
                            ),
                        ),   
                    ],
                ),

                Module(
                    "Multi-frame",
                    "C.7.6.6",
                    [
                        Element("NumberOfFrames", "00280008", "IS"),
                        Element("FrameIncrementPointer", "00280009", "AT"),
                    ],
                ),
                Module(
                    "Ophthalmic photography Image",
                    "C.8.17.2",
                    [
                        Element("ImageType", "00080008", "CS"),
                        Element("InstanceNumber", "00200013", "IS"),
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("PixelRepresentation", "00280103", "US"),
                        Element(
                            "PlanarConfiguration",
                            "00280006",
                            "US",
                            MustExistIf(
                                "00280002",
                                lambda v: int(v[0]) > 1
                                if isinstance(v, list) and len(v) > 0 and int(v[0]) > 1
                                else False,
                            ),
                        ),
                        Element("PixelSpacing", "00280030", "DS"),
                        Element("ContentTime", "00080033", "TM"),
                        Element("ContentDate", "00080023", "DA"),
                        Element(
                            "AcquisitionDateTime",
                            "0008002A",
                            "DT",
                            MustExistIf("00080008", lambda v: "ORIGINAL" in v),
                        ),
                        Element("LossyImageCompression", "00282110", "CS"),
                        Element(
                            "LossyImageCompressionRatio",
                            "00282112",
                            "DS",
                            MustExistIf("00282110", lambda v: v[0] == "01"),
                        ),
                        Element(
                            "LossyImageCompressionMethod",
                            "00282114",
                            "CS",
                            MustExistIf("00282110", lambda v: v[0] == "01"),
                        ),
                        Element(
                            "PresentationLUTShape",
                            "20500020",
                            "CS",
                            MustExistIf("00280004", lambda v: v[0] == "MONOCHROME2"),
                        ),
                        Element("BurnedInAnnotation", "00280301", "CS"),
                    ],
                ),
                Module(
                    "Ocular Region Imaged",
                    "C.8.17.5",
                    [
                        Element("ImageLaterality", "00200062", "CS"),
                        Element("AnatomicRegionSequence", "00082218", "SQ"),
                    ],
                ),
                Module(
                    "Ophthalmic Photography Acquisition Parameters",
                    "C.8.17.4",
                    [
                        Element(
                            "PatientEyeMovementCommanded", "00220005", "CS", ALLOW_EMPTY
                        ),
                        Element(
                            "PatientEyeMovementCommandCodeSequence",
                            "00220006",
                            "SQ",
                            MustExistIf(
                                "00220005", lambda v: v[0] == "YES" if v else False
                            ),
                        ),
                        Element(
                            "EmmetropicMagnification", "0022000A", "FL", ALLOW_EMPTY
                        ),
                        Element(
                            "IntraOcularPressure", "0022000B", "FL", ALLOW_EMPTY
                        ),
                        Element(
                            "HorizontalFieldofView", "0022000C", "FL", ALLOW_EMPTY
                        ),
                        Element(
                            "PupilDilated", "0022000D", "CS", ALLOW_EMPTY
                        ),
                        Element(
                            "DegreeOfDilation", "0022000E", "FL", MustTagExistIf(
                                "0022000D", lambda v: v[0] == "YES" if v else False
                            ),
                        ),
                        Element(
                            "RefractiveStateSequence", "0022001B", "SQ", ALLOW_EMPTY
                        ),
                        Element(
                            "MydriaticAgentSequence", "00220058", "SQ", MustTagExistIf(
                                "0022000D", lambda v: v[0] == "YES" if v else False
                            ),
                        ),
                    ],
                ),
                Module(
                    "Ophthalmic Photographic Parameters",
                    "C.8.17.3",
                    [
                        Element("AcquisitionDeviceTypeCodeSequence", "00220015", "SQ"),
                        Element(
                            "IlluminationTypeCodeSequence",
                            "00220016",
                            "SQ",
                            ALLOW_EMPTY,
                        ),
                        Element(
                            "LightPathFilterTypeStackCodeSequence",
                            "00220017",
                            "SQ",
                            ALLOW_EMPTY,
                        ),
                        Element(
                            "ImagePathFilterTypeStackCodeSequence",
                            "00220018",
                            "SQ",
                            ALLOW_EMPTY,
                        ),
                        Element("LensesCodeSequence", "00220019", "SQ", ALLOW_EMPTY),
                        Element("DetectorType", "00187004", "CS", ALLOW_EMPTY),
                        Element(
                            "ChannelDescriptionCodeSequence",
                            "0022001A",
                            "SQ",
                            PREFERRED,
                        ),
                    ],
                ),
                Module(
                    "SOP Common",
                    "C.12.1",
                    [
                        Element("SOPClassUID", "00080016", "UI"),
                        Element("SOPInstanceUID", "00080018", "UI"),
                        Element("SpecificCharacterSet", "00080005", "CS"),
                    ],
                ),
            ],
        ),
    ],
)


oct_b_rule = ComplianceRules(
    "OCT B Scan",
    [
        Entity(
            "Patient",
            [
                Module(
                    "Patient",
                    "C.7.1.1",
                    [
                        Element("PatientName", "00100010", "PN", ALLOW_EMPTY),
                        Element("PatientID", "00100020", "LO", ALLOW_EMPTY),
                        Element("PatientBirthDate", "00100030", "DA", ALLOW_EMPTY),
                        Element("PatientSex", "00100040", "CS", ALLOW_EMPTY),
                    ],
                )
            ],
        ),
        Entity(
            "Study",
            [
                Module(
                    "General Study",
                    "C.7.2.1",
                    [
                        Element("StudyInstanceUID", "0020000D", "UI"),
                        Element("StudyDate", "00080020", "DM", ALLOW_EMPTY),
                        Element("StudyTime", "00080030", "TM", ALLOW_EMPTY),
                        Element(
                            "ReferringPhysicianName", "00080090", "PN", ALLOW_EMPTY
                        ),
                        Element("StudyID", "00200010", "SH", ALLOW_EMPTY),
                        Element("AccessionNumber", "00080050", "SH", ALLOW_EMPTY),
                    ],
                )
            ],
        ),
        Entity(
            "Series",
            [
                Module(
                    "General Series",
                    "C.7.3.1",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesInstanceUID", "0020000E", "UI"),
                        Element("SeriesNumber", "00200011", "IS"),
                    ],
                ),
                Module(
                    "Ophthalmic Tomogtaphy Series",
                    "C.8.17.6",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesNumber", "00200011", "IS"),
                    ],
                ),
            ],
        ),
        Entity(
            "Frame of Reference",
            [
                Module(
                    "Frame of Reference",
                    "C.7.4.1",
                    [
                        Element("FrameOfReferenceUID", "00200052", "UI"),
                        Element(
                            "PositionReferenceIndicator", "00201040", "LO", ALLOW_EMPTY
                        ),
                    ],
                ),
                Module(
                    "Synchronization",
                    "C.7.4.2",
                    [
                        Element("SynchronizationFrameOfReferenceUID", "00200200", "UI"),
                        Element("SynchronizationTrigger", "0018106A", "CS"),
                        Element("AcquisitionTimeSynchronized", "00181800", "CS"),
                    ],
                ),
            ],
        ),
        Entity(
            "Equipment",
            [
                Module(
                    "General Equipment",
                    "7.5.1",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                    ],
                ),
                Module(
                    "Enhanced Equipment Module",
                    "C.7.5.2",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                        Element("ManufacturerModelName", "00081090", "LO"),
                        Element("DeviceSerialNumber", "00181000", "LO"),
                        Element("SoftwareVersions", "00181020", "LO"),
                    ],
                ),
            ],
        ),
        Entity(
            "Image",
            [
                Module(
                    "Image Pixel",
                    "C.7.6.3",
                    [
                        Element("PixelData", "7FE00010", "OB or OW", ALLOW_EMPTY),
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("Rows", "00280010", "US"),
                        Element("Columns", "00280011", "US"),
                        Element("BitsAllocated", "00280100", "US"),
                        Element("BitsStored", "00280101", "US"),
                        Element("HighBit", "00280102", "US"),
                        Element("PixelRepresentation", "00280103", "US"),
                    ],
                ),
                Module(
                    "Multi-frame Functional Groups",
                    "C.7.6.16",
                    [
                        Element("SharedFunctionalGroupsSequence", "52009229", "SQ"),
                        Element("PerFrameFunctionalGroupsSequence", "52009230", "SQ"),
                        Element("InstanceNumber", "00200013", "IS"),
                        Element("ContentDate", "00080023", "DA"),
                        Element("ContentTime", "00080033", "TM"),
                        Element("NumberOfFrames", "00280008", "IS"),
                    ],
                ),
                Module(
                    "Multi-frame Dimension",
                    "C.7.6.17",
                    [
                        Element("Dimension Organization Sequence", "00209221", "SQ"),
                        Element("Dimension Index Sequence", "00209222", "SQ"),
                    ],
                ),
                Module(
                    "Acquisition Context",
                    "C.7.6.14",
                    [
                        Element(
                            "Acquisition Context Sequence",
                            "00400555",
                            "SQ",
                            ALLOW_EMPTY,
                        ),
                    ],
                ),
                Module(
                    "Ophthalmic Tomography Image",
                    "C.8.17.7",
                    [
                        Element("ImageType", "00080008", "CS"),
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element(
                            "AcquisitionDateTime",
                            "0008002A",
                            "DT"),
                            
                        Element("AcquisitionDuration", "00189073", "US", MustExistIf("00080008", lambda v: "ORIGINAL" in v),),
                        Element("AcquisitionNumber", "00200012", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("PixelRepresentation", "00280103", "US"),
                        Element("BitsAllocated", "00280100", "US"),
                        Element("BitsStored", "00280101", "US"),
                        Element("HighBit", "00280102", "US"),
                        Element("PresentationLUTShape", "20500020", "CS"),
                        Element("LossyImageCompression", "00282110", "CS"),
                        Element(
                            "LossyImageCompressionRatio",
                            "00282112",
                            "DS",
                            MustExistIf("00282110", lambda v: v[0] == "01"),
                        ),
                        Element(
                            "LossyImageCompressionMethod",
                            "00282114",
                            "CS",
                            MustExistIf("00282110", lambda v: v[0] == "01"),
                        ),
                        Element("BurnedInAnnotation", "00280301", "CS"),
                        Element("ConcatenationFrameOffsetNumber", "00209228", "UL"),
                        Element("InConcatenationNumber", "00209162", "US"),
                        Element("InConcatenationTotalNumber", "00209163", "US"),
                    ],
                ),
                Module(
                    "Ophthalmic Tomogrpahy Acquisition Parameters",
                    "C.8.17.8",
                    [
                        Element(
                            "AxialLengthoftheEye", "00220030", "FL", ALLOW_EMPTY
                        ),
                        Element(
                            "HorizontalFieldofView", "0022000C", "FL", ALLOW_EMPTY
                        ),
                        Element(
                            "RefractiveStateSequence", "0022001B", "SQ", ALLOW_EMPTY
                        ),
                        Element(
                            "EmmetropicMagnification", "0022000A", "FL", ALLOW_EMPTY
                        ),
                        Element("IntraOcularPressure", "0022000B", "FL", ALLOW_EMPTY),
                        Element("Pupil Dilated", "0022000D", "CS", ALLOW_EMPTY),
                        Element(
                            "Madriatic Agent Sequence",
                            "00220058",
                            "SQ",
                            MustExistIf("0022000", lambda v: "YES" in v),
                        ),
                        Element(
                            "Degree of Dilation",
                            "0022000E",
                            "FL",
                            MustExistIf("0022000", lambda v: "YES" in v),
                        ),
                    ],
                ),
                Module(
                    "Ophthalmic Tomogrpahy Parameters",
                    "C.8.17.9",
                    [
                        Element(
                            "AcquisitionDeviceTypeCodeSequence", "00220015", "SQ"
                        ),
                        Element(
                            "LightPathFilterTypeStackCodeSequence",
                            "00220017",
                            "SQ",
                            ALLOW_EMPTY,
                        ),
                        Element("DetectorType", "00187004", "CS"),
                        Element("IlluminationWaveLength", "00220055", "FL"),
                        Element("IlluminationPower", "00220056", "FL"),
                        Element("IlluminationBandwidth", "00220057", "FL"),
                        Element("DepthSpatialResolution", "00220035", "FL"),
                        Element("MaximumDepthDistortion", "00220036", "FL"),
                        Element("AlongScanSpatialResolution", "00220037", "FL"),
                        Element("MaximumAlongScanDistortion", "00220038", "FL"),
                        Element("Across-scanSpatialResolution", "00220048", "FL"),
                        Element("MaximumAcross-scanDistortion", "00220049", "FL"),
                    ],
                ),
                Module(
                    "Ocular Region Imaged",
                    "C.8.17.5",
                    [
                        Element("ImageLaterality", "00200062", "CS"),
                        Element("AnatomicRegionSequence", "00082218", "SQ"),
                    ],
                ),
                Module(
                    "SOP Common",
                    "C.12.1",
                    [
                        Element("SOPClassUID", "00080016", "UI"),
                        Element("SOPInstanceUID", "00080018", "UI"),
                        Element("SpecificCharacterSet", "00080005", "CS"),
                    ],
                ),
            ],
        ),
    ],
)

octa_enface_rule = ComplianceRules(
    "En Face",
    [
        Entity(
            "Patient",
            [
                Module(
                    "Patient",
                    "C.7.1.1",
                    [
                        Element("PatientName", "00100010", "PN", ALLOW_EMPTY),
                        Element("PatientID", "00100020", "LO", ALLOW_EMPTY),
                        Element("PatientBirthDate", "00100030", "DA", ALLOW_EMPTY),
                        Element("PatientSex", "00100040", "CS", ALLOW_EMPTY),
                    ],
                )
            ],
        ),
        Entity(
            "Study",
            [
                Module(
                    "General Study",
                    "C.7.2.1",
                    [
                        Element("StudyInstanceUID", "0020000D", "UI"),
                        Element("StudyDate", "00080020", "DM", ALLOW_EMPTY),
                        Element("StudyTime", "00080030", "TM", ALLOW_EMPTY),
                        Element(
                            "ReferringPhysicianName", "00080090", "PN", ALLOW_EMPTY
                        ),
                        Element("StudyID", "00200010", "SH", ALLOW_EMPTY),
                        Element("AccessionNumber", "00080050", "SH", ALLOW_EMPTY),
       
                    ],
                )
            ],
        ),
        Entity(
            "Series",
            [
                Module(
                    "General Series",
                    "C.7.3.1",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesInstanceUID", "0020000E", "UI"),
                    ],
                ),
                Module(
                    "Ophthalmic tomography En Face Series Module",
                    "C.8.17.17",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesNumber", "00200011", "IS"),
                    ],
                ),
            ],
        ),
        Entity(
            "Frame of Reference",
            [
                Module(
                    "Frame of Reference",
                    "C.7.4.1",
                    [
                        Element("FrameofReferenceUID", "00200052", "UI"),
                        Element(
                            "PositionReferenceIndicator", "00201040", "LO", ALLOW_EMPTY
                        ),
                    ],
                ),
            ],
        ),
        Entity(
            "Equipment",
            [
                Module(
                    "General Equipment",
                    "7.5.1",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                    ],
                ),
                Module(
                    "Enhanced Equipment Module",
                    "C.7.5.2",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                        Element("ManufacturerModelName", "00081090", "LO"),
                        Element("DeviceSerialNumber", "00181000", "LO"),
                        Element("SoftwareVersions", "00181020", "LO"),
                    ],
                ),
            ],
        ),
        Entity(
            "Image",
            [
                Module(
                    "General Image",
                    "C.7.6.1",
                    [
                        Element("InstanceNumber", "00200013", "IS", ALLOW_EMPTY),
                        Element("PatientOrientation", "00200020", "CS", ALLOW_EMPTY),
                        Element("BurnedInAnnotation", "00280301", "CS", PREFERRED),
                        Element("ImageComments", "00204000", "LT", PREFERRED),
                    ],
                ),
                Module(
                    "Image Pixel",
                    "C.7.6.1",
                    [
                        Element("PixelData", "7FE00010", "OB or OW", ALLOW_EMPTY),
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element("Rows", "00280010", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("Columns", "00280011", "US"),
                        Element("BitsAllocated", "00280100", "US"),
                        Element("BitsStored", "00280101", "US"),
                        Element("HighBit", "00280102", "US"),
                        Element("PixelRepresentation", "00280103", "US"),
                    ],
                ),
                Module(
                    "Ophthalmic Optical coherene Tomography En Face Image ",
                    "C.8.17.14",
                    [
                        Element("ImageType", "00080008", "CS"),
                        Element("InstanceNumber", "00200013", "IS"),
                        Element("BitsAllocated", "00280100", "US"),
                        Element("BitsStored", "00280101", "US"),
                        Element("HighBit", "00280102", "US"),
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("PixelRepresentation", "00280103", "US"),
                        Element("PixelSpacing", "00280030", "DS"),
                        ##
                        Element("ImageOrientation", "00200037", "DS"),
                        Element("OphthalmicFrameLocationSequence", "00220031", "SQ"),
                        ##
                        Element("ContentTime", "00080033", "TM"),
                        Element("ContentDate", "00080023", "DA"),
                        Element("SourceImageSequence", "00082112", "SQ"),
                        Element("DerivationAlgorithmSequence", "00221612", "SQ"),
                        Element("OphthalmicImageTypeCodeSequence", "00221615", "SQ"),
                        Element("OphthalmicImageTypeDescription", "00221616", "LO", PREFERRED),
                        Element("WindowCenter", "00281050", "DS"),
                        Element("WindowWidth", "00281051", "DS"),
                        ###########change this######
                        # Element(
                        #     "EnfaceVolumeDescriptorSequence",
                        #     "0022EEE0",
                        #     "SQ",
                        # ),
                        Element(
                            "OphthalmicEnFaceVolumeDescriptorSequence",
                            "00221627",
                            "SQ",
                        ),
                        Element("LossyImageCompression", "00282110", "CS"),
                        Element(
                            "LossyImageCompressionRatio",
                            "00282112",
                            "DS",
                            MustExistIf("00282110", lambda v: v[0] == "01"),
                        ),
                        Element(
                            "LossyImageCompressionMethod",
                            "00282114",
                            "CS",
                            MustExistIf("00282110", lambda v: v[0] == "01"),
                        ),
                        Element(
                            "PresentationLUTShape",
                            "20500020",
                            "CS",
                            MustExistIf("00280004", lambda v: v[0] == "MONOCHROME2"),
                        ),
                        Element("BurnedInAnnotation", "00280301", "CS"),
                        Element("RecognizableVisualFeatures", "00280302", "CS"),
                    ],
                ),
                Module(
                    "Ocular Region Imaged Module",
                    "C.8.17.5",
                    [
                        Element("ImageLaterality", "00200062", "CS"),
                        Element("AnatomicRegionSequence", "00082218", "SQ"),
                        Element(
                            "RelativeImagePositionCodeSequence",
                            "0022001D",
                            "SQ",
                            PREFERRED,
                        ),
                        Element(
                            "PrimaryAnatomicStructureSequence",
                            "00082228",
                            "SQ",
                            PREFERRED,
                        ),
                        Element(
                            "OphthalmicAnatomicReferencePointXCoordinate",
                            "00221624",
                            "FL",
                            PREFERRED,
                        ),
                        Element(
                            "OphthalmicAnatomicReferencePointYCoordinate",
                            "00221626",
                            "FL",
                            PREFERRED,
                        ),
                        Element(
                            "OphthalmicAnatomicReferencePointSequence",
                            "00221632",
                            "SQ",
                            PREFERRED,
                        ),
                    ],
                ),
                Module(
                    "SOP Common",
                    "C.7.6.1",
                    [
                        Element("SOPClassUID", "00080016", "UI"),
                        Element("SOPInstanceUID", "00080018", "UI"),
                        Element("SpecificCharacterSet", "00080005", "CS"),
                    ],
                ),
            ],
        ),
    ],
)

heightmap_rule = ComplianceRules(
    "Heightmap Segmentation",
    [
        Entity(
            "Patient",
            [
                Module(
                    "Patient",
                    "C.7.1.1",
                    [
                        Element("PatientName", "00100010", "PN", ALLOW_EMPTY),
                        Element("PatientID", "00100020", "LO", ALLOW_EMPTY),
                        Element("PatientBirthDate", "00100030", "DA", ALLOW_EMPTY),
                        Element("PatientSex", "00100040", "CS", ALLOW_EMPTY),
                    ],
                )
            ],
        ),
        Entity(
            "Study",
            [
                Module(
                    "General Study",
                    "C.7.2.1",
                    [
                        Element("StudyInstanceUID", "0020000D", "UI"),
                        Element("StudyDate", "00080020", "DM", ALLOW_EMPTY),
                        Element("StudyTime", "00080030", "TM", ALLOW_EMPTY),
                        Element(
                            "ReferringPhysicianName", "00080090", "PN", ALLOW_EMPTY
                        ),
                        Element("StudyID", "00200010", "SH", ALLOW_EMPTY),
                        Element("AccessionNumber", "00080050", "SH", ALLOW_EMPTY),
       
                    ],
                )
            ],
        ),
        Entity(
            "Series",
            [
                Module(
                    "General Series",
                    "C.7.3.1",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesInstanceUID", "0020000E", "UI"),
                    ],
                ),
                Module(
                    "Segmentation Series",
                    "C.8.20.1",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesNumber", "00200011", "IS"),
                    ],
                ),
            ],
        ),
        Entity(
            "Frame of Reference",
            [
                Module(
                    "Frame of Reference",
                    "C.7.4.1",
                    [
                        Element("FrameofReferenceUID", "00200052", "UI"),
                        Element(
                            "PositionReferenceIndicator", "00201040", "LO", ALLOW_EMPTY
                        ),
                    ],
                ),
            ],
        ),
        Entity(
            "Equipment",
            [
                Module(
                    "General Equipment",
                    "7.5.1",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                    ],
                ),
                Module(
                    "Enhanced Equipment Module",
                    "C.7.5.2",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                        Element("ManufacturerModelName", "00081090", "LO"),
                        Element("DeviceSerialNumber", "00181000", "LO"),
                        Element("SoftwareVersions", "00181020", "LO"),
                    ],
                ),
            ],
        ),
        Entity(
            "Image",
            [
                Module(
                    "General Image",
                    "C.7.6.1",
                    [
                        Element("InstanceNumber", "00200013", "IS"),
             
                    ],
                ),

                Module(
                    "Multi-frame Functional Groups",
                    "C.7.6.16",
                    [
                        Element("SharedFunctionalGroupsSequence", "52009229", "SQ"),
                        Element("PerFrameFunctionalGroupsSequence", "52009230", "SQ"),
                        Element("InstanceNumber", "00200013", "IS"),
                        Element("ContentDate", "00080023", "DA"),
                        Element("ContentTime", "00080033", "TM"),
                        Element("NumberOfFrames", "00280008", "IS"),
                    ],
                ),
                Module(
                    "Multi-frame Dimension",
                    "C.7.6.17",
                    [
                        Element("Dimension Organization Sequence", "00209221", "SQ"),
                        Element("Dimension Index Sequence", "00209222", "SQ"),
                    ],
                ),
                
                Module(
                    "Floating Point Image Pixel",
                    "C.7.6.24",
                    [
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element("Rows", "00280010", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("Columns", "00280011", "US"),
                        Element("BitsAllocated", "00280100", "US"),
                        Element("FloatPixelData", "7FE00008", "OF", ALLOW_EMPTY),
                        Element("FloatPixelPaddingValue", "00280122", "US or SS", PREFERRED),
                        Element("FloatPixelPaddingRangeLimit", "00280124", "US or SS", MustExistIf("00280122", lambda v: bool(v)))

                    ],
                ),

                Module(
                    "Heightmap Segmentation Image",
                    "8.20.5",
                    [   Element("ImageType", "00080008", "CS" ),
                        Element("InstanceNumber", "00200013", "IS"),
                        Element("ContentLabel", "00700080", "CS"),
                        Element("ContentDescription", "00700081", "LO", ALLOW_EMPTY),
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("Rows", "00280010", "US"),
                        Element("Columns", "00280011", "US"),
                        Element("SegmentationType", "00620001", "CS"),
                        Element("SegmentSequence", "00620002", "SQ"),

                    ],
                ),
                Module(
                    "SOP Common",
                    "C.7.6.1",
                    [
                        Element("SOPClassUID", "00080016", "UI"),
                        Element("SOPInstanceUID", "00080018", "UI"),
                        Element("SpecificCharacterSet", "00080005", "CS"),
                       
                    ],
                ),
                Module(
                    "Common Instance Reference",
                    "C.12.2",
                    [
                        Element("ReferencedSeriesSequence", "00081115", "SQ"),
                    ],
                ),
            ],
        ),
    ],
)

segmentation_rule = ComplianceRules(
    "Surface Segmentation",
    [
        Entity(
            "Patient",
            [
                Module(
                    "Patient",
                    "C.7.1.1",
                    [
                        Element("PatientName", "00100010", "PN", ALLOW_EMPTY),
                        Element("PatientID", "00100020", "LO", ALLOW_EMPTY),
                        Element("PatientBirthDate", "00100030", "DA", ALLOW_EMPTY),
                        Element("PatientSex", "00100040", "CS", ALLOW_EMPTY),
                    ],
                )
            ],
        ),
        Entity(
            "Study",
            [
                Module(
                    "General Study",
                    "C.7.2.1",
                    [
                        Element("StudyInstanceUID", "0020000D", "UI"),
                        Element("StudyDate", "00080020", "DM", ALLOW_EMPTY),
                        Element("StudyTime", "00080030", "TM", ALLOW_EMPTY),
                        Element(
                            "ReferringPhysicianName", "00080090", "PN", ALLOW_EMPTY
                        ),
                        Element("StudyID", "00200010", "SH", ALLOW_EMPTY),
                        Element("AccessionNumber", "00080050", "SH", ALLOW_EMPTY),
    
                    ],
                )
            ],
        ),
        Entity(
            "Series",
            [
                Module(
                    "General Series",
                    "C.7.3.1",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesInstanceUID", "0020000E", "UI"),
                        Element("SeriesNumber", "00200011", "IS", ALLOW_EMPTY),
                    ],
                ),
                Module(
                    "Segmentation Series",
                    "C.8.20.1",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesNumber", "00200011", "IS"),
                    ],
                ),
            ],
        ),
        Entity(
            "Frame of Reference",
            [
                Module(
                    "Frame of Reference",
                    "C.7.4.1",
                    [
                        Element("FrameofReferenceUID", "00200052", "UI"),
                        Element(
                            "PositionReferenceIndicator", "00201040", "LO", ALLOW_EMPTY
                        ),
                    ],
                ),
            ],
        ),
        Entity(
            "Equipment",
            [
                Module(
                    "General Equipment",
                    "7.5.1",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                    ],
                ),
                Module(
                    "Enhanced Equipment Module",
                    "C.7.5.2",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                        Element("ManufacturerModelName", "00081090", "LO"),
                        Element("DeviceSerialNumber", "00181000", "LO"),
                        Element("SoftwareVersions", "00181020", "LO"),
                    ],
                ),
            ],
        ),
        Entity(
            "Surface",
            [
                Module(
                    "Surface Segmentation",
                    "C.8.23.1",
                    [
                        Element("InstanceNumber", "00200013", "IS"),
                        Element("ContentLabel", "00700080", "CS"),
                        Element("ContentDescription", "00700081", "LO", ALLOW_EMPTY),
                        Element("ContentDate", "00080023", "DA"),
                        Element("ContentTime", "00080033", "TM"),
                        Element("SegmentSequence", "00620002", "SQ"),
                        ###ADDED AS NEEDED
                        Element("ImageLaterality", "00200062", "CS", PREFERRED),
                    ],
                ),
                Module(
                    "Surface Mesh",
                    "C.27.1",
                    [
                        Element("NumberOfSurface", "00660001", "UL"),
                        Element("SurfaceSequence", "00660002", "SQ"),
                    ],
                ),
                Module(
                    "Common Instance Reference",
                    "C.12.2",
                    [
                        Element("ReferencedSeriesSequence", "00081115", "SQ"),
                    ],
                ),
                Module(
                    "SOP Common",
                    "C.7.6.1",
                    [
                        Element("SOPClassUID", "00080016", "UI"),
                        Element("SOPInstanceUID", "00080018", "UI"),
                        Element("SpecificCharacterSet", "00080005", "CS"),
                    ],
                ),
            ],
        ),
    ],
)


volume_analysis_rule = ComplianceRules(
    "B scan volumne analysis",
    [
        Entity(
            "Patient",
            [
                Module(
                    "Patient",
                    "C.7.1.1",
                    [
                        Element("PatientName", "00100010", "PN", ALLOW_EMPTY),
                        Element("PatientID", "00100020", "LO", ALLOW_EMPTY),
                        Element("PatientBirthDate", "00100030", "DA", ALLOW_EMPTY),
                        Element("PatientSex", "00100040", "CS", ALLOW_EMPTY),
                    ],
                )
            ],
        ),
        Entity(
            "Study",
            [
                Module(
                    "General Study",
                    "C.7.2.1",
                    [
                        Element("StudyInstanceUID", "0020000D", "UI"),
                        Element("StudyDate", "00080020", "DM", ALLOW_EMPTY),
                        Element("StudyTime", "00080030", "TM", ALLOW_EMPTY),
                        Element(
                            "ReferringPhysicianName", "00080090", "PN", ALLOW_EMPTY
                        ),
                        Element("StudyID", "00200010", "SH", ALLOW_EMPTY),
                        Element("AccessionNumber", "00080050", "SH", ALLOW_EMPTY),
     
                    ],
                )
            ],
        ),
        Entity(
            "Series",
            [
                Module(
                    "General Series",
                    "C.7.3.1",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesInstanceUID", "0020000E", "UI"),
                    ],
                ),
                Module(
                    "Ophthalmic Tomography B scan Volume Analysis Series",
                    "C.8.17.18",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesNumber", "00200011", "IS"),
                    ],
                ),
            ],
        ),
        Entity(
            "Frame of Reference",
            [
                Module(
                    "Frame of Reference",
                    "C.7.4.1",
                    [
                        Element("FrameofReferenceUID", "00200052", "UI"),
                        Element(
                            "PositionReferenceIndicator", "00201040", "LO", ALLOW_EMPTY
                        ),
                    ],
                ),
            ],
        ),
        Entity(
            "Equipment",
            [
                Module(
                    "General Equipment",
                    "7.5.1",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                    ],
                ),
                Module(
                    "Enhanced Equipment Module",
                    "C.7.5.2",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                        Element("ManufacturerModelName", "00081090", "LO"),
                        Element("DeviceSerialNumber", "00181000", "LO"),
                        Element("SoftwareVersions", "00181020", "LO"),
                    ],
                ),
            ],
        ),
        Entity(
            "Image",
            [
                Module(
                    "Image Pixel",
                    "C.7.6.3",
                    [
                        Element("PixelData", "7FE00010", "OB or OW", ALLOW_EMPTY),
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("Rows", "00280010", "US"),
                        Element("Columns", "00280011", "US"),
                        Element("BitsAllocated", "00280100", "US"),
                        Element("BitsStored", "00280101", "US"),
                        Element("HighBit", "00280102", "US"),
                        Element("PixelRepresentation", "00280103", "US"),
                    ],
                ),
                Module(
                    "Ophthalmic Optical Coherence Tomography B scan Volume Analysis",
                    "C.8.17.16",
                    [
                        Element("ImageType", "00080008", "CS"),
                        Element("InstanceNumber", "00200013", "IS"),
                        Element("ContentDate", "00080023", "DA"),
                        Element("ContentTime", "00080033", "TM"),
                        Element("BitsAllocated", "00280100", "US"),
                        Element("BitsStored", "00280101", "US"),
                        Element("HighBit", "00280102", "US"),
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("PixelRepresentation", "00280103", "US"),
                        Element("PresentationLUTShape", "20500020", "CS"),
                        Element("LossyImageCompression", "00282110", "CS"),
                        Element(
                            "LossyImageCompressionRatio",
                            "00282112",
                            "DS",
                            MustExistIf("00282110", lambda v: v[0] == "01"),
                        ),
                        Element(
                            "LossyImageCompressionMethod",
                            "00282114",
                            "CS",
                            MustExistIf("00282110", lambda v: v[0] == "01"),
                        ),
                        Element("BurnedInAnnotation", "00280301", "CS"),
                        Element("RecognizableVisualFeatures", "00280302", "CS"),
                        Element("AcquisitionMethodAlgorithmSequence", "00221423", "SQ"),
                        Element(
                            "OCTBScanAnalysisAcquisitionParametersSequence",
                            "00221640",
                            "SQ",
                        ),
                        Element("ConcatenationFrameOffsetNumber", "00209228", "UL"),
                        Element("InConcatenationNumber", "00209162", "US"),
                        Element("InConcatenationTotalNumber", "00209163", "US"),
                    ],
                ),
                Module(
                    "Multi-frame Functional Groups",
                    "C.7.6.16",
                    [
                        Element("SharedFunctionalGroupsSequence", "52009229", "SQ"),
                        Element("PerFrameFunctionalGroupsSequence", "52009230", "SQ"),
                        Element("InstanceNumber", "00200013", "IS"),
                        Element("ContentDate", "00080023", "DA"),
                        Element("ContentTime", "00080033", "TM"),
                        Element("NumberOfFrames", "00280008", "IS"),
             
                    ],
                ),
                Module(
                    "Multi-frame Dimension",
                    "C.7.6.17",
                    [
                        Element("Dimension Organization Sequence", "00209221", "SQ"),
                        Element("Dimension Index Sequence", "00209222", "SQ"),
                    ],
                ),
                Module(
                    "SOP Common",
                    "C.7.6.1",
                    [
                        Element("SOPClassUID", "00080016", "UI"),
                        Element("SOPInstanceUID", "00080018", "UI"),
                        Element("SpecificCharacterSet", "00080005", "CS"),
                    ],
                ),
            ],
        ),
    ],
)



octa_old_enface_rule = ComplianceRules(
    "En Face",
    [
        Entity(
            "Patient",
            [
                Module(
                    "Patient",
                    "C.7.1.1",
                    [
                        Element("PatientName", "00100010", "PN", ALLOW_EMPTY),
                        Element("PatientID", "00100020", "LO", ALLOW_EMPTY),
                        Element("PatientBirthDate", "00100030", "DA", ALLOW_EMPTY),
                        Element("PatientSex", "00100040", "CS", ALLOW_EMPTY),
                    ],
                )
            ],
        ),
        Entity(
            "Study",
            [
                Module(
                    "General Study",
                    "C.7.2.1",
                    [
                        Element("StudyInstanceUID", "0020000D", "UI"),
                        Element("StudyDate", "00080020", "DM", ALLOW_EMPTY),
                        Element("StudyTime", "00080030", "TM", ALLOW_EMPTY),
                        Element(
                            "ReferringPhysicianName", "00080090", "PN", ALLOW_EMPTY
                        ),
                        Element("StudyID", "00200010", "SH", ALLOW_EMPTY),
                        Element("AccessionNumber", "00080050", "SH", ALLOW_EMPTY),
       
                    ],
                )
            ],
        ),
        Entity(
            "Series",
            [
                Module(
                    "General Series",
                    "C.7.3.1",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesInstanceUID", "0020000E", "UI"),
                    ],
                ),
                Module(
                    "Ophthalmic tomography En Face Series Module",
                    "C.8.17.17",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesNumber", "00200011", "IS"),
                    ],
                ),
            ],
        ),
        Entity(
            "Frame of Reference",
            [
                Module(
                    "Frame of Reference",
                    "C.7.4.1",
                    [
                        Element("FrameofReferenceUID", "00200052", "UI"),
                        Element(
                            "PositionReferenceIndicator", "00201040", "LO", ALLOW_EMPTY
                        ),
                    ],
                ),
            ],
        ),
        Entity(
            "Equipment",
            [
                Module(
                    "General Equipment",
                    "7.5.1",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                    ],
                ),
                Module(
                    "Enhanced Equipment Module",
                    "C.7.5.2",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                        Element("ManufacturerModelName", "00081090", "LO"),
                        Element("DeviceSerialNumber", "00181000", "LO"),
                        Element("SoftwareVersions", "00181020", "LO"),
                    ],
                ),
            ],
        ),
        Entity(
            "Image",
            [
                Module(
                    "General Image",
                    "C.7.6.1",
                    [
                        Element("InstanceNumber", "00200013", "IS", ALLOW_EMPTY),
                        Element("PatientOrientation", "00200020", "CS", ALLOW_EMPTY),
                        Element("BurnedInAnnotation", "00280301", "CS", PREFERRED),
                        Element("ImageComments", "00204000", "LT", PREFERRED),
                    ],
                ),
                Module(
                    "Image Pixel",
                    "C.7.6.1",
                    [
                        Element("PixelData", "7FE00010", "OB or OW", ALLOW_EMPTY),
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element("Rows", "00280010", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("Columns", "00280011", "US"),
                        Element("BitsAllocated", "00280100", "US"),
                        Element("BitsStored", "00280101", "US"),
                        Element("HighBit", "00280102", "US"),
                        Element("PixelRepresentation", "00280103", "US"),
                    ],
                ),
                Module(
                    "Ophthalmic Optical coherene Tomography En Face Image ",
                    "C.8.17.14",
                    [
                        Element("ImageType", "00080008", "CS"),
                        Element("InstanceNumber", "00200013", "IS"),
                        Element("BitsAllocated", "00280100", "US"),
                        Element("BitsStored", "00280101", "US"),
                        Element("HighBit", "00280102", "US"),
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("PixelRepresentation", "00280103", "US"),
                        Element("PixelSpacing", "00280030", "DS"),
                        Element("ContentTime", "00080033", "TM"),
                        Element("ContentDate", "00080023", "DA"),
                        ###################
                        Element("SourceImageSequence", "00082112", "SQ"),
                  
                        Element("DerivationAlgorithmSequence", "00221612", "SQ"),
                        Element("OphthalmicImageTypeCodeSequence", "00221615", "SQ"),
                        Element("ReferencedSurfaceMeshIdentificationSequence", "00221620", "SQ"),
              
                        Element("WindowCenter", "00281050", "DS"),
                        Element("WindowWidth", "00281051", "DS"),
                        ###########change this######
                        # Element(
                        #     "EnfaceVolumeDescriptorSequence",
                        #     "0022EEE0",
                        #     "SQ",
                        # ),
                        Element("LossyImageCompression", "00282110", "CS"),
                        Element(
                            "LossyImageCompressionRatio",
                            "00282112",
                            "DS",
                            MustExistIf("00282110", lambda v: v[0] == "01"),
                        ),
                        Element(
                            "LossyImageCompressionMethod",
                            "00282114",
                            "CS",
                            MustExistIf("00282110", lambda v: v[0] == "01"),
                        ),
                        Element(
                            "PresentationLUTShape",
                            "20500020",
                            "CS",
                            MustExistIf("00280004", lambda v: v[0] == "MONOCHROME2"),
                        ),
                        Element("BurnedInAnnotation", "00280301", "CS"),
                        Element("RecognizableVisualFeatures", "00280302", "CS"),
                    ],
                ),
                Module(
                    "Ocular Region Imaged Module",
                    "C.8.17.5",
                    [
                        Element("ImageLaterality", "00200062", "CS"),
                        Element("AnatomicRegionSequence", "00082218", "SQ"),
                        Element(
                            "RelativeImagePositionCodeSequence",
                            "0022001D",
                            "SQ",
                            PREFERRED,
                        ),
                        Element(
                            "PrimaryAnatomicStructureSequence",
                            "00082228",
                            "SQ",
                            PREFERRED,
                        ),
                        Element(
                            "OphthalmicAnatomicReferencePointXCoordinate",
                            "00221624",
                            "FL",
                            PREFERRED,
                        ),
                        Element(
                            "OphthalmicAnatomicReferencePointYCoordinate",
                            "00221626",
                            "FL",
                            PREFERRED,
                        ),
                    ],
                ),
                Module(
                    "SOP Common",
                    "C.7.6.1",
                    [
                        Element("SOPClassUID", "00080016", "UI"),
                        Element("SOPInstanceUID", "00080018", "UI"),
                        Element("SpecificCharacterSet", "00080005", "CS"),
                    ],
                ),
            ],
        ),
    ],
)



cfp_ir_16_rule = ComplianceRules(
    "CFP IR",
    [
        Entity(
            "Patient",
            [
                Module(
                    "Patient",
                    "C.7.1.1",
                    [
                        Element("PatientName", "00100010", "PN", ALLOW_EMPTY),
                        Element("PatientID", "00100020", "LO", ALLOW_EMPTY),
                        Element("PatientBirthDate", "00100030", "DA", ALLOW_EMPTY),
                        Element("PatientSex", "00100040", "CS", ALLOW_EMPTY),
                    ],
                )
            ],
        ),
        Entity(
            "Study",
            [
                Module(
                    "General Study",
                    "C.7.2.1",
                    [
                        Element("StudyInstanceUID", "0020000D", "UI"),
                        Element("StudyDate", "00080020", "DM", ALLOW_EMPTY),
                        Element("StudyTime", "00080030", "TM", ALLOW_EMPTY),
                        Element(
                            "ReferringPhysicianName", "00080090", "PN", ALLOW_EMPTY
                        ),
                        Element("StudyID", "00200010", "SH", ALLOW_EMPTY),
                        Element("AccessionNumber", "00080050", "SH", ALLOW_EMPTY),
                        
                    ],
                )
            ],
        ),
        Entity(
            "Series",
            [
                Module(
                    "General Series",
                    "C.7.3.1",
                    [
                        Element("Modality", "00080060", "CS"),
                        Element("SeriesInstanceUID", "0020000E", "UI"),
                        Element("SeriesNumber", "00200011", "IS", ALLOW_EMPTY),
                    ],
                ),
                Module(
                    "Ophthalmic Photography Series",
                    "C.8.17.1",
                    [
                        Element("Modality", "00080060", "CS"),
                    ],
                ),
            ],
        ),
        Entity(
            "Frame of Reference",
            [
                Module(
                    "Synchronization",
                    "C.7.4.2",
                    [
                        Element("SynchronizationFrameOfReferenceUID", "00200200", "UI"),
                        Element("SynchronizationTrigger", "0018106A", "CS"),
                        Element("AcquisitionTimeSynchronized", "00181800", "CS"),
                    ],
                ),
            ],
        ),
        Entity(
            "Equipment",
            [
                Module(
                    "General Equipment",
                    "7.5.1",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                    ],
                ),
                Module(
                    "Enhanced Equipment Module",
                    "C.7.5.2",
                    [
                        Element("Manufacturer", "00080070", "LO"),
                        Element("ManufacturerModelName", "00081090", "LO"),
                        Element("DeviceSerialNumber", "00181000", "LO"),
                        Element("SoftwareVersions", "00181020", "LO"),
                    ],
                ),
            ],
        ),
        Entity(
            "Image",
            [
                Module(
                    "General Image",
                    "C.7.6.1",
                    [
                        Element("InstanceNumber", "00200013", "IS", ALLOW_EMPTY),
                        Element("PatientOrientation", "00200020", "CS", ALLOW_EMPTY),
                        Element("BurnedInAnnotation", "00280301", "CS"),
                    ],
                ),

                 Module(
                    "Image Pixel",
                    "C.7.6.3",
                    [
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("Rows", "00280010", "US"),
                        Element("Columns", "00280011", "US"),
                        Element("BitsAllocated", "00280100", "US"),
                        Element("BitsStored", "00280101", "US"),
                        Element("HighBit", "00280102", "US"),
                        Element("PixelRepresentation", "00280103", "US"),
                        Element("PixelData", "7FE00010", "OB or OW", ALLOW_EMPTY), 
                        Element(
                            "PlanarConfiguration",
                            "00280006",
                            "US",
                            MustExistIf(
                                "00280002",
                                lambda v: len(v) > 0 and int(v[0]) > 1
                                if isinstance(v, list) and len(v) > 0 and int(v[0]) > 1
                                else False,
                            ),
                        ),   
                    ],
                ),
                Module(
                    "Cine",
                    "C.7.6.5",
                    [
                        Element("FrameTime", "00181063", "DS"),
                        Element("FrameTimeVector", "00181065", "DS"),
                        Element("StartTrim", "00082142", "IS"),
                        Element("StopTrim", "00082143", "IS"),
                    ],
                ),

                Module(
                    "Multi-frame",
                    "C.7.6.6",
                    [
                        Element("NumberOfFrames", "00280008", "IS"),
                        Element("FrameIncrementPointer", "00280009", "AT"),
                    ],
                ),
                Module(
                    "Ophthalmic photography Image",
                    "C.8.17.2",
                    [
                        Element("ImageType", "00080008", "CS"),
                        Element("InstanceNumber", "00200013", "IS"),
                        Element("SamplesPerPixel", "00280002", "US"),
                        Element("PhotometricInterpretation", "00280004", "CS"),
                        Element("PixelRepresentation", "00280103", "US"),
                        Element(
                            "PlanarConfiguration",
                            "00280006",
                            "US",
                            MustExistIf(
                                "00280002",
                                lambda v: len(v) > 0 and int(v[0]) > 1
                                if isinstance(v, list) and len(v) > 0 and int(v[0]) > 1
                                else False,
                            ),
                        ),
                        Element("PixelSpacing", "00280030", "DS"),
                        Element("ContentTime", "00080033", "TM"),
                        Element("ContentDate", "00080023", "DA"),
                        Element(
                            "AcquisitionDateTime",
                            "0008002A",
                            "DT",
                            MustExistIf("00080008", lambda v: len(v) > 0 and "ORIGINAL" in v),
                        ),
                        Element("LossyImageCompression", "00282110", "CS"),
                        Element(
                            "LossyImageCompressionRatio",
                            "00282112",
                            "DS",
                            MustExistIf("00282110", lambda v: len(v) > 0 and v[0] == "01"),
                        ),
                        Element(
                            "LossyImageCompressionMethod",
                            "00282114",
                            "CS",
                            MustExistIf("00282110", lambda v: len(v) > 0 and v[0] == "01"),
                        ),
                        Element(
                            "PresentationLUTShape",
                            "20500020",
                            "CS",
                            MustExistIf("00280004", lambda v: len(v) > 0 and v[0] == "MONOCHROME2"),
                        ),
                        Element("BurnedInAnnotation", "00280301", "CS"),
                    ],
                ),
                Module(
                    "Ocular Region Imaged",
                    "C.8.17.5",
                    [
                        Element("ImageLaterality", "00200062", "CS"),
                        Element("AnatomicRegionSequence", "00082218", "SQ"),
                    ],
                ),
                Module(
                    "Ophthalmic Photography Acquisition Parameters",
                    "C.8.17.4",
                    [
                        Element(
                            "PatientEyeMovementCommanded", "00220005", "CS", ALLOW_EMPTY
                        ),
                        Element(
                            "PatientEyeMovementCommandCodeSequence",
                            "00220006",
                            "SQ",
                            MustExistIf(
                                "00220005", lambda v: len(v) > 0 and v[0] == "YES" if v else False
                            ),
                        ),
                        Element(
                            "EmmetropicMagnification", "0022000A", "FL", ALLOW_EMPTY
                        ),
                        Element(
                            "IntraOcularPressure", "0022000B", "FL", ALLOW_EMPTY
                        ),
                        Element(
                            "HorizontalFieldofView", "0022000C", "FL", ALLOW_EMPTY
                        ),
                        Element(
                            "PupilDilated", "0022000D", "CS", ALLOW_EMPTY
                        ),
                        Element(
                            "DegreeOfDilation", "0022000E", "FL", MustTagExistIf(
                                "0022000D", lambda v: len(v) > 0 and v[0] == "YES" if v else False
                            ),
                        ),
                        Element(
                            "RefractiveStateSequence", "0022001B", "SQ", ALLOW_EMPTY
                        ),
                        Element(
                            "MydriaticAgentSequence", "00220058", "SQ", MustTagExistIf(
                                "0022000D", lambda v: len(v) > 0 and v[0] == "YES" if v else False
                            ),
                        ),
                    ],
                ),
                Module(
                    "Ophthalmic Photographic Parameters",
                    "C.8.17.3",
                    [
                        Element("AcquisitionDeviceTypeCodeSequence", "00220015", "SQ"),
                        Element(
                            "IlluminationTypeCodeSequence",
                            "00220016",
                            "SQ",
                            ALLOW_EMPTY,
                        ),
                        Element(
                            "LightPathFilterTypeStackCodeSequence",
                            "00220017",
                            "SQ",
                            ALLOW_EMPTY,
                        ),
                        ####
                        Element(
                            "LightPathFilterPassThroughWavelength",
                            "00220001",
                            "US",
                            ALLOW_EMPTY,
                        ),
                        Element(
                            "LightPathFilterPassBand",
                            "00220002",
                            "US",
                            ALLOW_EMPTY,
                        ),
                        Element(
                            "ImagePathFilterPassThroughWavelength",
                            "00220003",
                            "US",
                            ALLOW_EMPTY,
                        ),
                        Element(
                            "ImagePathFilterPassBand",
                            "00220004",
                            "US",
                            ALLOW_EMPTY,
                        ),
                        Element(
                            "CameraAngleOfView",
                            "0022001E",
                            "FL",
                            ALLOW_EMPTY,
                        ),
                        ###
                        Element(
                            "ImagePathFilterTypeStackCodeSequence",
                            "00220018",
                            "SQ",
                            ALLOW_EMPTY,
                        ),
                        Element("LensesCodeSequence", "00220019", "SQ", ALLOW_EMPTY),
                        Element("DetectorType", "00187004", "CS", ALLOW_EMPTY),
                        Element(
                            "ChannelDescriptionCodeSequence",
                            "0022001A",
                            "SQ",
                            PREFERRED,
                        ),
                    ],
                ),
                Module(
                    "SOP Common",
                    "C.12.1",
                    [
                        Element("SOPClassUID", "00080016", "UI"),
                        Element("SOPInstanceUID", "00080018", "UI"),
                        Element("SpecificCharacterSet", "00080005", "CS"),
                    ],
                ),
            ],
        ),
    ],
)