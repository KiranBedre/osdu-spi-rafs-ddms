#  Copyright 2023 ExxonMobil Technology and Engineering Company
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import copy
import json
import os
from typing import NamedTuple

from app.models.data_schemas.base import (
    ALL_PATHS_TO_DATA_MODEL,
    SAMPLES_ANALYSIS,
)
from app.models.schemas.osdu_storage import Acl, Legal, OsduStorageRecord
from app.resources.paths import (
    RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR,
    SATURATION_FUNCTION_SET_STR,
    CommonRelativePathsV2,
)
from tests.test_api.api_version import API_VERSION_V2

dir_path = os.path.dirname(os.path.abspath(__file__))


class KindVersion:
    V_1_0_0: str = "1.0.0"
    V_1_1_0: str = "1.1.0"
    V_2_0_0: str = "2.0.0"


TEST_SERVER = "http://testserver"
TEST_HEADERS = {
    "content-type": "application/json",
    "data-partition-id": "opendes",
    "Authorization": "Bearer token",
}
TEST_HEADERS_NO_AUTH = {
    "data-partition-id": "opendes",
    "content-type": "application/json",
}
SCHEMA_AUTHORITY = os.getenv("SCHEMA_AUTHORITY", "osdu")
CUSTOM_SCHEMA_AUTHORITY = os.getenv("CUSTOM_SCHEMA_AUTHORITY", "rafsddms")
PARTITION = "partition"
GENERIC_FACILITY_TYPE = "master-data--GenericFacility"
GENERIC_FACILITY_ID = "generic_facility_test"
GENERIC_SITE_TYPE = "master-data--GenericSite"
GENERIC_SITE_ID = "generic_site_test"
RESERVOIR_SIMULATION_ROCK_PHYSICS_TYPE = "work-product-component--ReservoirSimulationRockPhysicsModel"
RESERVOIR_SIMULATION_ROCK_PHYSICS_ID = "reservoirsimulationrockphysics_test_id"
SAMPLE_TYPE = "master-data--Sample"
SAMPLE_ID = "sample_test"
SAMPLE_ACQUISITION_JOB_TYPE = "master-data--SampleAcquisitionJob"
SAMPLE_ACQUISITION_JOB_ID = "sample_acquisition_job_test"
SAMPLE_CHAIN_OF_CUSTODY_EVENT_TYPE = "master-data--SampleChainOfCustodyEvent"
SAMPLE_CHAIN_OF_CUSTODY_EVENT_ID = "sample_chain_of_custody_event_test"
SAMPLE_CONTAINER_TYPE = "master-data--SampleContainer"
SAMPLE_CONTAINER_ID = "sample_container_test"
SAMPLESANALYSESREPORT_TYPE = "work-product-component--SamplesAnalysesReport"
SAMPLESANALYSESREPORT_ID = "samplesanalysesreport_test_id"
SAMPLESANALYSIS_TYPE = "work-product-component--SamplesAnalysis"
SAMPLESANALYSIS_ID = "samplesanalysis_test"
SATURATION_FUNCTION_SET_TYPE = "work-product-component--SaturationFunctionSet"
SATURATION_FUNCTION_SET_ID = "saturation_function_set_test_id"
FLUID_MODEL_TYPE = "work-product-component--FluidModel"
FLUID_MODEL_ID = "fluid_model_test_id"
FILE_GENERIC_TYPE = "dataset--File.Generic"
TEST_DATASET_UID = "1"

TEST_GENERIC_FACILITY_ID = f"{PARTITION}:{GENERIC_FACILITY_TYPE}:{GENERIC_FACILITY_ID}"
TEST_GENERIC_FACILITY_KIND = f"{SCHEMA_AUTHORITY}:wks:{GENERIC_FACILITY_TYPE}:{KindVersion.V_1_0_0}"
TEST_GENERIC_SITE_ID = f"{PARTITION}:{GENERIC_SITE_TYPE}:{GENERIC_SITE_ID}"
TEST_GENERIC_SITE_KIND = f"{SCHEMA_AUTHORITY}:wks:{GENERIC_SITE_TYPE}:{KindVersion.V_1_0_0}"
TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID = (
    f"{PARTITION}:{RESERVOIR_SIMULATION_ROCK_PHYSICS_TYPE}:{RESERVOIR_SIMULATION_ROCK_PHYSICS_ID}"
)
TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_KIND = (
    f"{SCHEMA_AUTHORITY}:wks:{RESERVOIR_SIMULATION_ROCK_PHYSICS_TYPE}:{KindVersion.V_1_0_0}"
)
TEST_SAMPLE_ID = f"{PARTITION}:{SAMPLE_TYPE}:{SAMPLE_ID}"
TEST_SAMPLE_KIND = f"{SCHEMA_AUTHORITY}:wks:{SAMPLE_TYPE}:{KindVersion.V_2_0_0}"
TEST_SAMPLE_ACQUISITION_JOB_ID = f"{PARTITION}:{SAMPLE_ACQUISITION_JOB_TYPE}:{SAMPLE_ACQUISITION_JOB_ID}"
TEST_SAMPLE_ACQUISITION_JOB_KIND = f"{SCHEMA_AUTHORITY}:wks:{SAMPLE_ACQUISITION_JOB_TYPE}:{KindVersion.V_1_0_0}"
TEST_SAMPLE_CHAIN_OF_CUSTODY_EVENT_ID = (
    f"{PARTITION}:{SAMPLE_CHAIN_OF_CUSTODY_EVENT_TYPE}:{SAMPLE_CHAIN_OF_CUSTODY_EVENT_ID}"
)
TEST_SAMPLE_CHAIN_OF_CUSTODY_EVENT_KIND = (
    f"{SCHEMA_AUTHORITY}:wks:{SAMPLE_CHAIN_OF_CUSTODY_EVENT_TYPE}:{KindVersion.V_1_0_0}"
)
TEST_SAMPLE_CONTAINER_ID = f"{PARTITION}:{SAMPLE_CONTAINER_TYPE}:{SAMPLE_CONTAINER_ID}"
TEST_SAMPLE_CONTAINER_KIND = f"{SCHEMA_AUTHORITY}:wks:{SAMPLE_CONTAINER_TYPE}:{KindVersion.V_1_0_0}"
TEST_SAMPLESANALYSESREPORT_ID = f"{PARTITION}:{SAMPLESANALYSESREPORT_TYPE}:{SAMPLESANALYSESREPORT_ID}"
TEST_SAMPLESANALYSESREPORT_KIND_V2 = f"{SCHEMA_AUTHORITY}:wks:{SAMPLESANALYSESREPORT_TYPE}:{KindVersion.V_1_0_0}"
TEST_SAMPLESANALYSIS_ID = f"{PARTITION}:{SAMPLESANALYSIS_TYPE}:{SAMPLESANALYSIS_ID}"
TEST_SAMPLESANALYSIS_KIND_V2 = f"{SCHEMA_AUTHORITY}:wks:{SAMPLESANALYSIS_TYPE}:{KindVersion.V_1_0_0}"
TEST_SATURATION_FUNCTION_SET_ID = f"{PARTITION}:{SATURATION_FUNCTION_SET_TYPE}:{SATURATION_FUNCTION_SET_ID}"
TEST_SATURATION_FUNCTION_SET_KIND = f"{SCHEMA_AUTHORITY}:wks:{SATURATION_FUNCTION_SET_TYPE}:{KindVersion.V_1_0_0}"
TEST_FLUID_MODEL_ID = f"{PARTITION}:{FLUID_MODEL_TYPE}:{FLUID_MODEL_ID}"
TEST_FLUID_MODEL_KIND = f"{SCHEMA_AUTHORITY}:wks:{FLUID_MODEL_TYPE}:{KindVersion.V_1_0_0}"
TEST_ACL = Acl(viewers=["viewers@domain.com"], owners=["owners@domain.com"])
TEST_LEGAL = Legal(legaltags=["legaltag"], otherRelevantDataCountries=["US"], status="compliant")
TEST_WRONG_ID = "partition:entity-type:id"

OSDU_GENERIC_RECORD = OsduStorageRecord(
    id="partition:type:identifier",
    kind="partition:wks:type:type_version",
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data={"dummy": "data"},
)

GENERIC_FACILITY_RECORD = OsduStorageRecord(
    id=TEST_GENERIC_FACILITY_ID,
    kind=TEST_GENERIC_FACILITY_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data={},
)

GENERIC_SITE_RECORD = OsduStorageRecord(
    id=TEST_GENERIC_SITE_ID,
    kind=TEST_GENERIC_SITE_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data={
        "Name": "Name",
        "SiteTypeID": "partition:reference-data--SiteType:Coal:",
    },
)

RESERVOIR_SIMULATION_ROCK_PHYSICS_RECORD = OsduStorageRecord(
    id=TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID,
    kind=TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data={
        "CompressibilityModelTypeID": "namespace:reference-data--CompressibilityModelType:SomeUniqueCompressibilityModelTypeID:",
        "ThermalModelTypeID": "namespace:reference-data--ThermalModelType:SomeUniqueThermalModelTypeID:",
        "BasisOfModelling": {
            "CompressibilityModelInputSampleAnalysisIDs": [
                "namespace:work-product-component--SamplesAnalysis:SamplesAnalysis-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
            ],
            "CompressibilityModelInputDataCollectionID": "namespace:work-product-component--PersistedCollection:PersistedCollection-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
            "ThermalModelInputSampleAnalysisIDs": [
                "namespace:work-product-component--SamplesAnalysis:SamplesAnalysis-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
            ],
            "ThermalModelInputDataCollectionID": "namespace:work-product-component--PersistedCollection:PersistedCollection-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
            "ModellingApplicationsUsed": [
                "Example ModellingApplicationsUsed",
            ],
            "IntendedWorkflowUsageIDs": [
                "namespace:reference-data--WorkflowUsageType:All:",
            ],
        },
        "ParentModelID": "namespace:work-product-component--ReservoirSimulationRockPhysicsModel:f3e451d1-9d49-559f-93d8-2e36722016fb:",
        "DatePublished": "2020-02-13T09:13:15.55Z",
    },
)

SAMPLE_RECORD = OsduStorageRecord(
    id=TEST_SAMPLE_ID,
    kind=TEST_SAMPLE_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data={
        "ResourceHomeRegionID": "partition:reference-data--OSDURegion:Region:",
    },
)

SAMPLE_ACQUISITION_JOB_RECORD = OsduStorageRecord(
    id=TEST_SAMPLE_ACQUISITION_JOB_ID,
    kind=TEST_SAMPLE_ACQUISITION_JOB_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data={
        "JobTypeID": "JobTypeID",
        "ReferenceJobNumber": "ReferenceJobNumber",
    },
)

SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD = OsduStorageRecord(
    id=TEST_SAMPLE_CHAIN_OF_CUSTODY_EVENT_ID,
    kind=TEST_SAMPLE_CHAIN_OF_CUSTODY_EVENT_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data={
        "CustodyEventLocationID": "partition:master-data--Organisation:Organisation:",
        "CustodyEventTypeID": "partition:reference-data--CustodyEventType:SubSampleLive:",
    },
)

SAMPLE_CONTAINER_RECORD = OsduStorageRecord(
    id=TEST_SAMPLE_CONTAINER_ID,
    kind=TEST_SAMPLE_CONTAINER_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data={
        "OperatingConditionRating": {
            "Temperature": 1.0,
            "Pressure": 1.0,
        },
        "SampleContainerServiceTypeIDs": ["partition:reference-data--SampleContainerServiceType:NonHydrocarbon:"],
        "ManufacturerID": "partition:master-data--Organisation:Organisation:",
        "SampleContainerTypeID": "partition:reference-data--SampleContainerType:Pressurized.NotPressureCompensated:",
        "ContainerIdentifier": "BTL-12345",
        "Capacity": 100,
    },
)

SAMPLESANALYSESREPORT_RECORD_V2 = OsduStorageRecord(
    id=TEST_SAMPLESANALYSESREPORT_ID,
    kind=TEST_SAMPLESANALYSESREPORT_KIND_V2,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data={
        "SampleIDs": [f"{PARTITION}:master-data--Sample:sample_test_id:"],
        "ReportSampleIdentifiers": ["45H", "49H"],
        "SampleAnalysisTypeIDs": [
            "partition:reference-data--SampleAnalysisType:CapillaryPressureGasOil:",
            "partition:reference-data--SampleAnalysisType:CentrifugeDrainageGasOil:",
        ],
        "SamplesAnalysisCategoryTagIDs": [
            "partition:reference-data--SamplesAnalysisCategoryTag:SCAL:",
        ],
    },
)


SAMPLESANALYSIS_RECORD_V2 = OsduStorageRecord(
    id=TEST_SAMPLESANALYSIS_ID,
    kind=TEST_SAMPLESANALYSIS_KIND_V2,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data={
        "ParentSamplesAnalysesReports": [
            {
                "ParentSamplesAnalysesReportID": f"{TEST_SAMPLESANALYSESREPORT_ID}:",
            },
        ],
        "SampleAnalysisTypeIDs": [
            "partition:reference-data--SampleAnalysisType:CapillaryPressureGasOil:",
            "partition:reference-data--SampleAnalysisType:CentrifugeDrainageGasOil:",
        ],
        "Parameters": [],
    },
)


SATURATION_FUNCTION_SET_RECORD = OsduStorageRecord(
    id=TEST_SATURATION_FUNCTION_SET_ID,
    kind=TEST_SATURATION_FUNCTION_SET_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data={
        "SaturationFunctions": [
            {
                "FunctionName": "Example Function Name",
                "FunctionUsageTypeID": "partition:reference-data--SaturationFunctionUsageType:Imbibition:",
                "BasisOfModelling": {
                    "CapillaryPressureInputDataCollectionID": "partition:work-product-component--PersistedCollection:PersistedCollection-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
                    "CapillaryPressureInputSampleAnalysisIDs": [
                        "partition:work-product-component--SamplesAnalysis:SamplesAnalysis-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
                    ],
                    "RelativePermeabilityInputDataCollectionID": "partition:work-product-component--PersistedCollection:PersistedCollection-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
                    "RelativePermeabilityInputSampleAnalysisIDs": [
                        "partition:work-product-component--SamplesAnalysis:SamplesAnalysis-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
                    ],
                    "ModellingApplicationsUsed": [
                        "Example ModellingApplicationsUsed",
                    ],
                    "IntendedWorkflowUsageIDs": [
                        "partition:reference-data--WorkflowUsageType:All:",
                    ],
                },
                "DatePublished": "2020-02-13T09:13:15.55Z",
                "ModellingContacts": [
                    {
                        "EmailAddress": "support@company.com",
                        "PhoneNumber": "1-555-281-5555",
                        "RoleTypeID": "partition:reference-data--ContactRoleType:AccountOwner:",
                        "DataGovernanceRoleTypeID": "partition:reference-data--DataGovernanceRoleType:ExecutiveSponsor:",
                        "WorkflowPersonaTypeID": "partition:reference-data--WorkflowPersonaType:All:",
                        "Comment": "Example Comment",
                        "OrganisationID": "partition:master-data--Organisation:SomeUniqueOrganisationID:",
                        "Name": "Example Name",
                    },
                ],
                "ModelAreaOfInterestIDs": [
                    "partition:work-product-component--WellboreIntervalSet:WellboreIntervalSet-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
                ],
                "HasRelativePermeability": True,
                "HasCapillaryPressure": True,
            },
        ],
        "Remarks": [
            {
                "RemarkSequenceNumber": 1,
                "Remark": "Example Remark",
                "RemarkSource": "Example Remark Source",
                "RemarkDate": "2020-02-13",
            },
        ],
        "ParentModelID": "partition:work-product-component--SaturationFunctionSet:SaturationFunctionSet-911bb71f-06ab-4deb-8e68-b8c9229dc76b:",
        "ExtensionProperties": {},
    },
)

SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V2 = copy.deepcopy(SAMPLESANALYSIS_RECORD_V2)

FLUID_MODEL_RECORD = OsduStorageRecord(
    id=TEST_FLUID_MODEL_ID,
    kind=TEST_FLUID_MODEL_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data={
        "FluidModelTypeID": "namespace:reference-data--FluidModelType:BlackOil:",
        "BasisOfModelling": {
            "InputDataCollectionID": "namespace:work-product-component--PersistedCollection:f3e451d1-9d49-559f-93d8-2e36722016fb:",
            "ModelPropertyFormulationMethods": [
                {
                    "ModelPropertyTypeID": "namespace:reference-data--FluidModelPropertyType:Density:",
                    "ModelPropertyFormulationMethodID": "namespace:reference-data--FluidModelPropertyFormulationMethod:PengRobinson:",
                },
            ],
            "ModellingApplicationsUsed": [
                "PVTsim Nova 5.0",
            ],
            "IntendedWorkflowUsageIDs": [
                "namespace:reference-data--WorkflowUsageType:ReservoirSimulation:",
            ],
        },
        "ParentModelID": "namespace:work-product-component--FluidModel:parent-model-id:",
        "DatePublished": "2020-02-13T09:13:15.55Z",
    },
)


def build_storage_service_response_200(
    record_count: int = 1,
    record_ids: list = None,
    skipped_record_ids: list = None,
    record_id_versions: list = None,
):
    return {
        "recordCount": record_count,
        "recordIds": record_ids or ["partition:type:test"],
        "skippedRecordIds": skipped_record_ids or [],
        "recordIdVersions": record_id_versions or ["partition:type:test:1"],
    }


STORAGE_SERVICE_200_RESPONSE = {
    "recordCount": 1,
    "recordIds": ["partition:type:test"],
    "skippedRecordIds": [],
    "recordIdVersions": ["partition:type:test:1"],
}

EXPECTED_404_RESPONSE = {"code": 404, "reason": str(b"test reason"), "message": "test txt"}
EXPECTED_422_NO_KIND_RESPONSE = {"code": 422, "reason": "Unprocessable entity.", "errors": ["kind field required"]}
EXPECTED_422_INVALID_KIND_REASON = "Kind `{}` not supported in RAFS-DDMS."
EXPECTED_422_WRONG_PATTERN = ["ValidationError", "string does not match regex"]
EXPECTED_422_TYPER_ERROR_LIST = "body value is not a valid list"
EXPECTED_200_CREATED_RESPONSE = {
    "recordCount": 1,
    "recordIdVersions": ["partition:type:test:1"],
    "skippedRecordCount": 0,
}

STORAGE_SERVICE_200_VERSIONS_RESPONSE = {
    "recordId": "partition:type:test",
    "versions": [1, 2],
}
EXPECTED_200_VERSIONS_RESPONSE = STORAGE_SERVICE_200_VERSIONS_RESPONSE

# V2 endpoint paths
RESERVOIR_SIMULATION_ROCK_PHYSICS_ENDPOINT_PATH_V2 = (
    f"/api/os-rafs-ddms/{API_VERSION_V2}/reservoirsimulationrockphysics"
)
SAMPLESANALYSES_REPORT_ENDPOINT_PATH_V2 = f"/api/os-rafs-ddms/{API_VERSION_V2}/samplesanalysesreport"
SAMPLESANALYSIS_ENDPOINT_PATH_V2 = f"/api/os-rafs-ddms/{API_VERSION_V2}/samplesanalysis"
SATURATION_FUNCTION_SET_ENDPOINT_PATH_V2 = f"/api/os-rafs-ddms/{API_VERSION_V2}/saturationfunctionset"
FLUID_MODEL_ENDPOINT_PATH_V2 = f"/api/os-rafs-ddms/{API_VERSION_V2}/fluidmodel"
MASTER_DATA_ENDPOINT_PATH_V2 = f"/api/os-rafs-ddms/{API_VERSION_V2}/masterdata"

# data endpoints v2
BASE_V2_PATH = f"api/os-rafs-ddms/{API_VERSION_V2}"

SAMPLESANALYSIS_ENDPOINT_PATH = f"{BASE_V2_PATH}/samplesanalysis"
BASE_DATA_V2_PATH = f"{SAMPLESANALYSIS_ENDPOINT_PATH}/{TEST_SAMPLESANALYSIS_ID}"

RES_SIM_ROCK_PHYSICS_ENDPOINT_PATH = f"{BASE_V2_PATH}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}"
RES_SIM_ROCK_PHYSICS_DATA_PATH = (
    f"{RES_SIM_ROCK_PHYSICS_ENDPOINT_PATH}/{TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID}/data"
)
SATURATION_FUNCTION_SET_ENDPOINT_PATH = f"{BASE_V2_PATH}/{SATURATION_FUNCTION_SET_STR}"
SATURATION_FUNCTION_SET_DATA_PATH = f"{SATURATION_FUNCTION_SET_ENDPOINT_PATH}/{TEST_SATURATION_FUNCTION_SET_ID}/data"

common_relative_paths_v2 = CommonRelativePathsV2()


class TestContentPathsApiV2:
    RCA = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.ROUTINECOREANALYSIS}"
    CCE = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.CCE}"
    DIFF_LIB = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.DIFF_LIB}"
    TRANSPORT_TEST = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.TRANSPORT_TEST}"
    COMPOSITIONAL_ANALYSIS = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.COMPOSITIONAL_ANALYSIS}"
    ATMOSPHERIC_FLASH = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.ATMOSPHERIC_FLASH}"
    MSS = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.MSS}"
    SWELLING = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.SWELLING}"
    CVD = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.CVD}"
    WATER_ANALYSIS = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.WATER_ANALYSIS}"
    INTERFACIAL_TENSION = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.INTERFACIAL_TENSION}"
    VLE = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.VLE}"
    MCM = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.MCM}"
    SLIMTUBE = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.SLIMTUBE}"
    EXTRACTION = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.EXTRACTION}"
    FRACTIONATION = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.FRACTIONATION}"
    RELATIVE_PERMEABILITY = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.RELATIVE_PERMEABILITY}"
    ROCK_COMPRESSIBILITY = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.ROCK_COMPRESSIBILITY}"
    NMR = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.NMR}"
    MULTIPLE_SALINITY = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.MULTIPLE_SALINITY}"
    GCMS_ALKANES = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.GCMS_ALKANES}"
    GCMS_AROMATICS = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.GCMS_AROMATICS}"
    GCMS_RATIOS = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.GCMS_RATIOS}"
    GAS_CHROMATOGRAPHY = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.GAS_CHROMATOGRAPHY}"
    GAS_COMPOSITION = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.GAS_COMPOSITION}"
    ISOTOPE_ANALYSIS = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.ISOTOPE_ANALYSIS}"
    BULK_PYROLYSIS = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.BULK_PYROLYSIS}"
    CORE_GAMMA = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.CORE_GAMMA}"
    MINING_GEOTECH_LOGGING = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.MINING_GEOTECH_LOGGING}"
    PROPPANT_EMBEDMENT = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.PROPPANT_EMBEDMENT}"
    UNIAXIAL_TEST = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.UNIAXIAL_TEST}"
    GCMSMS_ANALYSIS = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.GCMSMS_ANALYSIS}"
    CEC_CONTENT = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.CEC_CONTENT}"
    ELECTRICAL_PROPERTIES = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.ELECTRICAL_PROPERTIES}"
    TRIAXIAL_TEST = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.TRIAXIAL_TEST}"
    CAP_PRESSURE = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.CAP_PRESSURE}"
    CAP_SUCTION_TIME = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.CAP_SUCTION_TIME}"
    WETTABILITY_INDEX = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.WETTABILITY_INDEX}"
    TEC = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.TEC}"
    EDS_MAPPING = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.EDS_MAPPING}"
    XRF = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.XRF}"
    TENSILE_STRENGTH = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.TENSILE_STRENGTH}"
    VITRINITE_REFLECTANCE = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.VITRINITE_REFLECTANCE}"
    XRD = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.XRD}"
    PDP = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.PDP}"
    STO = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.STO}"
    CRUSHED_ROCK_ANALYSIS = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.CRUSHED_ROCK_ANALYSIS}"
    RES_SIM_ROCK_PHYSICS_MODEL = RES_SIM_ROCK_PHYSICS_DATA_PATH
    SATURATION_FUNCTION_SET_MODEL = SATURATION_FUNCTION_SET_DATA_PATH
    ROLLER_OVEN_TEST = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.ROLLER_OVEN_TEST}"
    SATURATION_TEST = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.SATURATION_TEST}"


class BulkDatasetIdV2(NamedTuple):
    RCA = f"{PARTITION}:{FILE_GENERIC_TYPE}:routinecoreanalysis-{TEST_DATASET_UID}"
    CCE = f"{PARTITION}:{FILE_GENERIC_TYPE}:constantcompositionexpansion-{TEST_DATASET_UID}"
    DIFF_LIB = f"{PARTITION}:{FILE_GENERIC_TYPE}:differentialliberation-{TEST_DATASET_UID}"
    TRANSPORT_TEST = f"{PARTITION}:{FILE_GENERIC_TYPE}:transport-{TEST_DATASET_UID}"
    COMPOSITIONAL_ANALYSIS = f"{PARTITION}:{FILE_GENERIC_TYPE}:compositionalanalysis-{TEST_DATASET_UID}"
    ATMOSPHERIC_FLASH = f"{PARTITION}:{FILE_GENERIC_TYPE}:atmosphericflash-{TEST_DATASET_UID}"
    MSS = f"{PARTITION}:{FILE_GENERIC_TYPE}:multistageseparator-{TEST_DATASET_UID}"
    SWELLING = f"{PARTITION}:{FILE_GENERIC_TYPE}:swelling-{TEST_DATASET_UID}"
    CVD = f"{PARTITION}:{FILE_GENERIC_TYPE}:constantvolumedepletion-{TEST_DATASET_UID}"
    WATER_ANALYSIS = f"{PARTITION}:{FILE_GENERIC_TYPE}:wateranalysis-{TEST_DATASET_UID}"
    INTERFACIAL_TENSION = f"{PARTITION}:{FILE_GENERIC_TYPE}:interfacialtension-{TEST_DATASET_UID}"
    VLE = f"{PARTITION}:{FILE_GENERIC_TYPE}:vaporliquidequilibrium-{TEST_DATASET_UID}"
    MCM = f"{PARTITION}:{FILE_GENERIC_TYPE}:multiplecontactmiscibility-{TEST_DATASET_UID}"
    SLIMTUBE = f"{PARTITION}:{FILE_GENERIC_TYPE}:slimtube-{TEST_DATASET_UID}"
    EXTRACTION = f"{PARTITION}:{FILE_GENERIC_TYPE}:extraction-{TEST_DATASET_UID}"
    FRACTIONATION = f"{PARTITION}:{FILE_GENERIC_TYPE}:fractionation-{TEST_DATASET_UID}"
    RELATIVE_PERMEABILITY = f"{PARTITION}:{FILE_GENERIC_TYPE}:relativepermeability-{TEST_DATASET_UID}"
    ROCK_COMPRESSIBILITY = f"{PARTITION}:{FILE_GENERIC_TYPE}:rockcompressibility-{TEST_DATASET_UID}"
    ELECTRICAL_PROPERTIES = f"{PARTITION}:{FILE_GENERIC_TYPE}:electricalproperties-{TEST_DATASET_UID}"
    NMR = f"{PARTITION}:{FILE_GENERIC_TYPE}:nmr-{TEST_DATASET_UID}"
    MULTIPLE_SALINITY = f"{PARTITION}:{FILE_GENERIC_TYPE}:multiplesalinitytests-{TEST_DATASET_UID}"
    GCMS_ALKANES = f"{PARTITION}:{FILE_GENERIC_TYPE}:gcmsalkanes-{TEST_DATASET_UID}"
    GCMS_AROMATICS = f"{PARTITION}:{FILE_GENERIC_TYPE}:gcmsaromatics-{TEST_DATASET_UID}"
    GCMS_RATIOS = f"{PARTITION}:{FILE_GENERIC_TYPE}:gcmsratios-{TEST_DATASET_UID}"
    GAS_CHROMATOGRAPHY = f"{PARTITION}:{FILE_GENERIC_TYPE}:gaschromatographyanalyses-{TEST_DATASET_UID}"
    GAS_COMPOSITION = f"{PARTITION}:{FILE_GENERIC_TYPE}:gascompositionanalyses-{TEST_DATASET_UID}"
    ISOTOPE_ANALYSIS = f"{PARTITION}:{FILE_GENERIC_TYPE}:isotopes-{TEST_DATASET_UID}"
    BULK_PYROLYSIS = f"{PARTITION}:{FILE_GENERIC_TYPE}:bulkpyrolysisanalyses-{TEST_DATASET_UID}"
    CORE_GAMMA = f"{PARTITION}:{FILE_GENERIC_TYPE}:coregamma-{TEST_DATASET_UID}"
    MINING_GEOTECH_LOGGING = f"{PARTITION}:{FILE_GENERIC_TYPE}:mininggeotechlogging-{TEST_DATASET_UID}"
    PROPPANT_EMBEDMENT = f"{PARTITION}:{FILE_GENERIC_TYPE}:proppantembed-{TEST_DATASET_UID}"
    UNIAXIAL_TEST = f"{PARTITION}:{FILE_GENERIC_TYPE}:uniaxial-{TEST_DATASET_UID}"
    GCMSMS_ANALYSIS = f"{PARTITION}:{FILE_GENERIC_TYPE}:gcmsms-{TEST_DATASET_UID}"
    CEC_CONTENT = f"{PARTITION}:{FILE_GENERIC_TYPE}:cec-{TEST_DATASET_UID}"
    TRIAXIAL_TEST = f"{PARTITION}:{FILE_GENERIC_TYPE}:triaxial-{TEST_DATASET_UID}"
    CAP_PRESSURE = f"{PARTITION}:{FILE_GENERIC_TYPE}:capillarypressure-{TEST_DATASET_UID}"
    CAP_SUCTION_TIME = f"{PARTITION}:{FILE_GENERIC_TYPE}:capillarysuctiontime-{TEST_DATASET_UID}"
    WETTABILITY_INDEX = f"{PARTITION}:{FILE_GENERIC_TYPE}:wettabilityindex-{TEST_DATASET_UID}"
    TEC = f"{PARTITION}:{FILE_GENERIC_TYPE}:tec-{TEST_DATASET_UID}"
    EDS_MAPPING = f"{PARTITION}:{FILE_GENERIC_TYPE}:edsmapping-{TEST_DATASET_UID}"
    XRF = f"{PARTITION}:{FILE_GENERIC_TYPE}:xrf-{TEST_DATASET_UID}"
    TENSILE_STRENGTH = f"{PARTITION}:{FILE_GENERIC_TYPE}:tensilestrength-{TEST_DATASET_UID}"
    VITRINITE_REFLECTANCE = f"{PARTITION}:{FILE_GENERIC_TYPE}:vitrinitereflectance-{TEST_DATASET_UID}"
    XRD = f"{PARTITION}:{FILE_GENERIC_TYPE}:xrd-{TEST_DATASET_UID}"
    PDP = f"{PARTITION}:{FILE_GENERIC_TYPE}:pdp-{TEST_DATASET_UID}"
    STO = f"{PARTITION}:{FILE_GENERIC_TYPE}:stocktankoilanalysisreports-{TEST_DATASET_UID}"
    CRUSHED_ROCK_ANALYSIS = f"{PARTITION}:{FILE_GENERIC_TYPE}:crushedrockanalysis-{TEST_DATASET_UID}"
    RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL = (
        f"{PARTITION}:{FILE_GENERIC_TYPE}:{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}-{TEST_DATASET_UID}"
    )
    SATURATION_FUNCTION_SET_MODEL = f"{PARTITION}:{FILE_GENERIC_TYPE}:{SATURATION_FUNCTION_SET_STR}-{TEST_DATASET_UID}"
    ROLLER_OVEN_TEST = f"{PARTITION}:{FILE_GENERIC_TYPE}:rolleroventest-{TEST_DATASET_UID}"
    SATURATION_TEST = f"{PARTITION}:{FILE_GENERIC_TYPE}:saturationtest-{TEST_DATASET_UID}"


with open(f"{dir_path}/schemas/wpc_definitions.json") as fp:
    WPC_DEFINITIONS = json.load(fp)

with open(f"{dir_path}/schemas/reservoir_simulation_rock_physics_model.json") as fp:
    RESERVOIR_SIMULATION_ROCK_PHYSICS_SCHEMA = json.load(fp)
    RESERVOIR_SIMULATION_ROCK_PHYSICS_SCHEMA["definitions"] = WPC_DEFINITIONS

with open(f"{dir_path}/schemas/samples_analyses_report.json") as fp:
    SAMPLES_ANALYSES_REPORT_SCHEMA = json.load(fp)
    SAMPLES_ANALYSES_REPORT_SCHEMA["definitions"] = WPC_DEFINITIONS

with open(f"{dir_path}/schemas/samples_analysis.json") as fp:
    SAMPLES_ANALYSIS_SCHEMA = json.load(fp)
    SAMPLES_ANALYSIS_SCHEMA["definitions"] = WPC_DEFINITIONS

with open(f"{dir_path}/schemas/saturation_function_set.json") as fp:
    SATURATION_FUNCTION_SET_SCHEMA = json.load(fp)
    SATURATION_FUNCTION_SET_SCHEMA["definitions"] = WPC_DEFINITIONS

with open(f"{dir_path}/schemas/fluid_model.json") as fp:
    FLUID_MODEL_SCHEMA = json.load(fp)
    FLUID_MODEL_SCHEMA["definitions"] = WPC_DEFINITIONS

with open(f"{dir_path}/schemas/md_definitions.json") as fp:
    MD_DEFINITIONS = json.load(fp)

with open(f"{dir_path}/schemas/sample.json") as fp:
    SAMPLE_SCHEMA = json.load(fp)
    SAMPLE_SCHEMA["definitions"] = MD_DEFINITIONS

with open(f"{dir_path}/schemas/sample_acquisition_job.json") as fp:
    SAMPLE_ACQUISITION_JOB_SCHEMA = json.load(fp)
    SAMPLE_ACQUISITION_JOB_SCHEMA["definitions"] = MD_DEFINITIONS

with open(f"{dir_path}/schemas/sample_chain_of_custody_event.json") as fp:
    SAMPLE_CHAIN_OF_CUSTODY_EVENT_SCHEMA = json.load(fp)
    SAMPLE_CHAIN_OF_CUSTODY_EVENT_SCHEMA["definitions"] = MD_DEFINITIONS

with open(f"{dir_path}/schemas/sample_container.json") as fp:
    SAMPLE_CONTAINER_SCHEMA = json.load(fp)
    SAMPLE_CONTAINER_SCHEMA["definitions"] = MD_DEFINITIONS

PREFIX_TO_STRIP = f"v2/{SAMPLES_ANALYSIS}/"

VALID_ANALYSIS_TYPES_V1_0_0 = [
    path.replace(PREFIX_TO_STRIP, "")
    for path, versions in ALL_PATHS_TO_DATA_MODEL.items()
    if path.startswith(PREFIX_TO_STRIP) and "1.0.0" in versions
]
