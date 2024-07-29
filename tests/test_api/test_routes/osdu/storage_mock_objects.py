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

from app.models.domain.osdu.MDCoring100 import Coring
from app.models.domain.osdu.MDCoring100 import Data as CoringData
from app.models.domain.osdu.MDGenericFacility100 import (
    Data as GenericFacitilyData,
)
from app.models.domain.osdu.MDGenericFacility100 import GenericFacility
from app.models.domain.osdu.MDGenericSite100 import Data as GenericSiteData
from app.models.domain.osdu.MDGenericSite100 import GenericSite
from app.models.domain.osdu.MDRockSample100 import Data as RockSampleData
from app.models.domain.osdu.MDRockSample100 import RockSample
from app.models.domain.osdu.MDSample200 import Data as SampleData
from app.models.domain.osdu.MDSample200 import Sample
from app.models.domain.osdu.MDSampleAcquisitionJob100 import (
    Data as SampleAcquisitionJobData,
)
from app.models.domain.osdu.MDSampleAcquisitionJob100 import (
    SampleAcquisitionJob,
)
from app.models.domain.osdu.MDSampleChainOfCustodyEvent100 import (
    Data as SCOCEData,
)
from app.models.domain.osdu.MDSampleChainOfCustodyEvent100 import (
    SampleChainOfCustodyEvent,
)
from app.models.domain.osdu.MDSampleContainer100 import (
    Data as SampleContainerData,
)
from app.models.domain.osdu.MDSampleContainer100 import SampleContainer
from app.models.domain.osdu.osdu_wks_AbstractPTCondition_1.field_0 import (
    Field0 as OperatingConditionRating,
)
from app.models.domain.osdu.WPCCCE100 import ConstantCompositionExpansionTest
from app.models.domain.osdu.WPCCCE100 import Data as CceData
from app.models.domain.osdu.WPCCompositionalAnalysis100 import (
    CompositionalAnalysis,
)
from app.models.domain.osdu.WPCCompositionalAnalysis100 import (
    Data as CompositionalAnalysisData,
)
from app.models.domain.osdu.WPCConstantVolumeDepletionTest100 import (
    ConstantVolumeDepletionTest,
)
from app.models.domain.osdu.WPCConstantVolumeDepletionTest100 import (
    Data as CVDData,
)
from app.models.domain.osdu.WPCDifLib100 import Data as DifLibData
from app.models.domain.osdu.WPCDifLib100 import DifferentialLiberationTest
from app.models.domain.osdu.WPCInterfacialTension100 import (
    Data as InterfacialTensionData,
)
from app.models.domain.osdu.WPCInterfacialTension100 import (
    InterfacialTensionTest,
)
from app.models.domain.osdu.WPCMCM100 import Data as MCMData
from app.models.domain.osdu.WPCMCM100 import MultipleContactMiscibilityTest
from app.models.domain.osdu.WPCMSS100 import Data as MSSData
from app.models.domain.osdu.WPCMSS100 import MultiStageSeparatorTest
from app.models.domain.osdu.WPCPVT100 import PVT
from app.models.domain.osdu.WPCPVT100 import Data as PVTData
from app.models.domain.osdu.WPCPVT100 import PVTTests
from app.models.domain.osdu.WPCRockSampleAnalysis110 import (
    Data as RockSampleAnalysisData,
)
from app.models.domain.osdu.WPCRockSampleAnalysis110 import RockSampleAnalysis
from app.models.domain.osdu.WPCSamplesAnalysesReport100 import (
    Data as SamplesAnalysesReportData,
)
from app.models.domain.osdu.WPCSamplesAnalysesReport100 import (
    SamplesAnalysesReport,
)
from app.models.domain.osdu.WPCSamplesAnalysis100 import (
    Data as SamplesAnalysisData,
)
from app.models.domain.osdu.WPCSamplesAnalysis100 import (
    ParentSamplesAnalysesReport,
    SamplesAnalysis,
)
from app.models.domain.osdu.WPCSamplesAnalysis100_V1 import (
    Data as SamplesAnalysisDataV1,
)
from app.models.domain.osdu.WPCSamplesAnalysis100_V1 import (
    SamplesAnalysis as SamplesAnalysisV1,
)
from app.models.domain.osdu.WPCSlimTubeTest100 import Data as SlimTubeTestData
from app.models.domain.osdu.WPCSlimTubeTest100 import SlimTubeTest
from app.models.domain.osdu.WPCSTO100 import Data as STOData
from app.models.domain.osdu.WPCSTO100 import StockTankOilAnalysisTest
from app.models.domain.osdu.WPCSwellingTest100 import Data as SwellingData
from app.models.domain.osdu.WPCSwellingTest100 import SwellingTest
from app.models.domain.osdu.WPCTransportTest100 import (
    Data as TransportTestData,
)
from app.models.domain.osdu.WPCTransportTest100 import TransportTest
from app.models.domain.osdu.WPCVLE100 import Data as VLEData
from app.models.domain.osdu.WPCVLE100 import VaporLiquidEquilibriumTest
from app.models.domain.osdu.WPCWaterAnalysis100 import (
    Data as WaterAnalysisData,
)
from app.models.domain.osdu.WPCWaterAnalysis100 import WaterAnalysisTest
from app.models.schemas.osdu_storage import Acl, Legal, OsduStorageRecord
from app.resources.paths import CommonRelativePathsV2, PVTModelRelativePaths
from tests.test_api.api_version import API_VERSION, API_VERSION_V2

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
CORING_TYPE = "master-data--Coring"
CORING_ID = "coring_test"
GENERIC_FACILITY_TYPE = "master-data--GenericFacility"
GENERIC_FACILITY_ID = "generic_facility_test"
GENERIC_SITE_TYPE = "master-data--GenericSite"
GENERIC_SITE_ID = "generic_site_test"
ROCKSAMPLE_TYPE = "master-data--RockSample"
ROCKSAMPLE_ID = "rocksample_test"
SAMPLE_TYPE = "master-data--Sample"
SAMPLE_ID = "sample_test"
SAMPLE_ACQUISITION_JOB_TYPE = "master-data--SampleAcquisitionJob"
SAMPLE_ACQUISITION_JOB_ID = "sample_acquisition_job_test"
SAMPLE_CHAIN_OF_CUSTODY_EVENT_TYPE = "master-data--SampleChainOfCustodyEvent"
SAMPLE_CHAIN_OF_CUSTODY_EVENT_ID = "sample_chain_of_custody_event_test"
SAMPLE_CONTAINER_TYPE = "master-data--SampleContainer"
SAMPLE_CONTAINER_ID = "sample_container_test"
ROCKSAMPLEANALYSIS_TYPE = "work-product-component--RockSampleAnalysis"
ROCKSAMPLEANALYSIS_ID = "rocksampleanalysis_test"
CCE_TYPE = "work-product-component--ConstantCompositionExpansionTest"
CCE_ID = "cce-test"
PVT_TYPE = "work-product-component--PVT"
PVT_ID = "pvt_test"
WELL_TYPE = "master-data--Well"
WELL_ID = "well_test"
WELLBORE_TYPE = "master-data--Wellbore"
WELLBORE_ID = "wellbore_test"
DL_TYPE = "work-product-component--DifferentialLiberationTest"
DL_ID = "dlt_test"
TRANSPORT_TYPE = "work-product-component--TransportTest"
TRANSPORT_ID = "transport_test"
COMPOSITIONALANALYSIS_TYPE = "work-product-component--CompositionalAnalysisTest"
COMPOSITIONALANALYSIS_ID = "compositionalanalysis_test"
FLUIDSAMPLE_TYPE = "master-data--FluidSample"
FLUIDSAMPLE_ID = "fluidsample_test"
MSS_TYPE = "work-product-component--MultiStageSeparatorTest"
MSS_ID = "multistageseparator_test"
SWELLING_TYPE = "work-product-component--SwellingTest"
SWELLING_ID = "swelling_test"
CVD_TYPE = "work-product-component--ConstantVolumeDepletionTest"
CVD_ID = "cvd_test"
WATER_ANALYSIS_TYPE = "work-product-component--WaterAnalysisTest"
WATER_ANALYSIS_ID = "wateranalysis_test"
STO_TYPE = "work-product-component--StockTankOilAnalysisTest"
STO_ID = "sto_test"
INTERFACIAL_TENSION_TYPE = "work-product-component--InterfacialTensionTest"
INTERFACIAL_TENSION_ID = "intefacialtension_test"
VLE_TYPE = "work-product-component--VaporLiquidEquilibriumTest"
VLE_ID = "vle_test"
MCM_TYPE = "work-product-component--MultipleContactMiscibilityTest"
MCM_ID = "mcm_test"
SLIMTUBETEST_TYPE = "work-product-component--SlimTubeTest"
SLIMTUBETEST_ID = "slimtubetest_test"
SAMPLESANALYSESREPORT_TYPE = "work-product-component--SamplesAnalysesReport"
SAMPLESANALYSESREPORT_ID = "samplesanalysesreport_test_id"
SAMPLESANALYSIS_TYPE = "work-product-component--SamplesAnalysis"
SAMPLESANALYSIS_ID = "samplesanalysis_test"
RELATIVE_PERMEABILITY_ID = "relative_permeability_test"
CAP_PRESSURE_ID = "cappressure_test"
FRACTIONATION_ID = "fractionation_test"
EXTRACTION_ID = "extraction_test"
PHYS_CHEM_ID = "physchem_test"
WATER_GAS_RELATIVE_PERMEABILITY_ID = "watergasrelativepermeability_test"
ROCK_COMPRESSIBILITY_ID = "rock_compressibility_test"
ELECTRICAL_PROPERTIES_ID = "electricalproperties_test"
FORMATION_RESISTIVITY_INDEX_ID = "formationresistivityindexes_test"
FILE_GENERIC_TYPE = "dataset--File.Generic"
TEST_DATASET_UID = "1"

TEST_CORING_ID = f"{PARTITION}:{CORING_TYPE}:{CORING_ID}"
TEST_CORING_KIND = f"{SCHEMA_AUTHORITY}:wks:{CORING_TYPE}:{KindVersion.V_1_0_0}"
TEST_GENERIC_FACILITY_ID = f"{PARTITION}:{GENERIC_FACILITY_TYPE}:{GENERIC_FACILITY_ID}"
TEST_GENERIC_FACILITY_KIND = f"{SCHEMA_AUTHORITY}:wks:{GENERIC_FACILITY_TYPE}:{KindVersion.V_1_0_0}"
TEST_GENERIC_SITE_ID = f"{PARTITION}:{GENERIC_SITE_TYPE}:{GENERIC_SITE_ID}"
TEST_GENERIC_SITE_KIND = f"{SCHEMA_AUTHORITY}:wks:{GENERIC_SITE_TYPE}:{KindVersion.V_1_0_0}"
TEST_ROCKSAMPLE_ID = f"{PARTITION}:{ROCKSAMPLE_TYPE}:{ROCKSAMPLE_ID}"
TEST_ROCKSAMPLE_KIND = f"{SCHEMA_AUTHORITY}:wks:{ROCKSAMPLE_TYPE}:{KindVersion.V_1_0_0}"
TEST_SAMPLE_ID = f"{PARTITION}:{SAMPLE_TYPE}:{SAMPLE_ID}"
TEST_SAMPLE_KIND = f"{SCHEMA_AUTHORITY}:wks:{SAMPLE_TYPE}:{KindVersion.V_2_0_0}"
TEST_SAMPLE_ACQUISITION_JOB_ID = f"{PARTITION}:{SAMPLE_ACQUISITION_JOB_TYPE}:{SAMPLE_ACQUISITION_JOB_ID}"
TEST_SAMPLE_ACQUISITION_JOB_KIND = f"{SCHEMA_AUTHORITY}:wks:{SAMPLE_ACQUISITION_JOB_TYPE}:{KindVersion.V_1_0_0}"
TEST_SAMPLE_CHAIN_OF_CUSTODY_EVENT_ID = f"{PARTITION}:{SAMPLE_CHAIN_OF_CUSTODY_EVENT_TYPE}:{SAMPLE_CHAIN_OF_CUSTODY_EVENT_ID}"
TEST_SAMPLE_CHAIN_OF_CUSTODY_EVENT_KIND = f"{SCHEMA_AUTHORITY}:wks:{SAMPLE_CHAIN_OF_CUSTODY_EVENT_TYPE}:{KindVersion.V_1_0_0}"
TEST_SAMPLE_CONTAINER_ID = f"{PARTITION}:{SAMPLE_CONTAINER_TYPE}:{SAMPLE_CONTAINER_ID}"
TEST_SAMPLE_CONTAINER_KIND = f"{SCHEMA_AUTHORITY}:wks:{SAMPLE_CONTAINER_TYPE}:{KindVersion.V_1_0_0}"
TEST_ROCKSAMPLEANALYSIS_ID = f"{PARTITION}:{ROCKSAMPLEANALYSIS_TYPE}:{ROCKSAMPLEANALYSIS_ID}"
TEST_ROCKSAMPLEANALYSIS_KIND = f"{SCHEMA_AUTHORITY}:wks:{ROCKSAMPLEANALYSIS_TYPE}:{KindVersion.V_1_1_0}"
TEST_CCE_ID = f"{PARTITION}:{CCE_TYPE}:{CCE_ID}"
TEST_CCE_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{CCE_TYPE}:{KindVersion.V_1_0_0}"
TEST_PVT_ID = f"{PARTITION}:{PVT_TYPE}:{PVT_ID}"
TEST_PVT_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{PVT_TYPE}:{KindVersion.V_1_0_0}"
TEST_WELLBORE_ID = f"{PARTITION}:{WELLBORE_TYPE}:{WELLBORE_ID}"
TEST_DL_ID = f"{PARTITION}:{DL_TYPE}:{DL_ID}"
TEST_DL_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{DL_TYPE}:{KindVersion.V_1_0_0}"
TEST_TRANSPORT_ID = f"{PARTITION}:{TRANSPORT_TYPE}:{TRANSPORT_ID}"
TEST_TRANSPORT_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{TRANSPORT_TYPE}:{KindVersion.V_1_0_0}"
TEST_COMPOSITIONALANALYSIS_ID = f"{PARTITION}:{COMPOSITIONALANALYSIS_TYPE}:{COMPOSITIONALANALYSIS_ID}"
TEST_COMPOSITIONALANALYSIS_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{COMPOSITIONALANALYSIS_TYPE}:{KindVersion.V_1_0_0}"
TEST_MSS_ID = f"{PARTITION}:{MSS_TYPE}:{MSS_ID}"
TEST_MSS_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{MSS_TYPE}:{KindVersion.V_1_0_0}"
TEST_SWELLING_ID = f"{PARTITION}:{SWELLING_TYPE}:{SWELLING_ID}"
TEST_SWELLING_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{SWELLING_TYPE}:{KindVersion.V_1_0_0}"
TEST_CVD_ID = f"{PARTITION}:{CVD_TYPE}:{CVD_ID}"
TEST_CVD_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{CVD_TYPE}:{KindVersion.V_1_0_0}"
TEST_WATERANALYSIS_ID = f"{PARTITION}:{WATER_ANALYSIS_TYPE}:{WATER_ANALYSIS_ID}"
TEST_WATERANALYSIS_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{WATER_ANALYSIS_TYPE}:{KindVersion.V_1_0_0}"
TEST_STO_ID = f"{PARTITION}:{STO_TYPE}:{STO_ID}"
TEST_STO_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{STO_TYPE}:{KindVersion.V_1_0_0}"
TEST_INTERFACIAL_TENSION_ID = f"{PARTITION}:{INTERFACIAL_TENSION_TYPE}:{INTERFACIAL_TENSION_ID}"
TEST_INTERFACIAL_TENSION_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{INTERFACIAL_TENSION_TYPE}:{KindVersion.V_1_0_0}"
TEST_VLE_ID = f"{PARTITION}:{VLE_TYPE}:{VLE_ID}"
TEST_VLE_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{VLE_TYPE}:{KindVersion.V_1_0_0}"
TEST_MCM_ID = f"{PARTITION}:{MCM_TYPE}:{MCM_ID}"
TEST_MCM_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{MCM_TYPE}:{KindVersion.V_1_0_0}"
TEST_SLIMTUBETEST_ID = f"{PARTITION}:{SLIMTUBETEST_TYPE}:{SLIMTUBETEST_ID}"
TEST_SLIMTUBETEST_KIND = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{SLIMTUBETEST_TYPE}:{KindVersion.V_1_0_0}"
TEST_SAMPLESANALYSESREPORT_ID = f"{PARTITION}:{SAMPLESANALYSESREPORT_TYPE}:{SAMPLESANALYSESREPORT_ID}"
TEST_SAMPLESANALYSESREPORT_KIND_V1 = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{SAMPLESANALYSESREPORT_TYPE}:{KindVersion.V_1_0_0}"
TEST_SAMPLESANALYSESREPORT_KIND_V2 = f"{SCHEMA_AUTHORITY}:wks:{SAMPLESANALYSESREPORT_TYPE}:{KindVersion.V_1_0_0}"
TEST_SAMPLESANALYSIS_ID = f"{PARTITION}:{SAMPLESANALYSIS_TYPE}:{SAMPLESANALYSIS_ID}"
TEST_SAMPLESANALYSIS_KIND_V1 = f"{CUSTOM_SCHEMA_AUTHORITY}:wks:{SAMPLESANALYSIS_TYPE}:{KindVersion.V_1_0_0}"
TEST_SAMPLESANALYSIS_KIND_V2 = f"{SCHEMA_AUTHORITY}:wks:{SAMPLESANALYSIS_TYPE}:{KindVersion.V_1_0_0}"
TEST_CAP_PRESSURE_ID = f"{PARTITION}:{SAMPLESANALYSIS_TYPE}:{CAP_PRESSURE_ID}"
TEST_FLUIDSAMPLE_ID = f"{PARTITION}:{FLUIDSAMPLE_TYPE}:{FLUIDSAMPLE_ID}"
TEST_RELATIVE_PERMEABILITY_ID = f"{PARTITION}:{SAMPLESANALYSIS_TYPE}:{RELATIVE_PERMEABILITY_ID}"
TEST_FRACTIONATION_ID = f"{PARTITION}:{SAMPLESANALYSIS_TYPE}:{FRACTIONATION_ID}"
TEST_EXTRACTION_ID = f"{PARTITION}:{SAMPLESANALYSIS_TYPE}:{EXTRACTION_ID}"
TEST_PHYS_CHEM_ID = f"{PARTITION}:{SAMPLESANALYSIS_TYPE}:{PHYS_CHEM_ID}"
TEST_WATER_GAS_RELATIVE_PERMEABILITY_ID = f"{PARTITION}:{SAMPLESANALYSIS_TYPE}:{WATER_GAS_RELATIVE_PERMEABILITY_ID}"
TEST_ROCK_COMPRESSIBILITY_ID = f"{PARTITION}:{SAMPLESANALYSIS_TYPE}:{ROCK_COMPRESSIBILITY_ID}"
TEST_ELECTRICAL_PROPERTIES_ID = f"{PARTITION}:{SAMPLESANALYSIS_TYPE}:{ELECTRICAL_PROPERTIES_ID}"
TEST_FORMATION_RESISTIVITY_INDEX_ID = f"{PARTITION}:{SAMPLESANALYSIS_TYPE}:{FORMATION_RESISTIVITY_INDEX_ID}"
TEST_ACL = Acl(viewers=["viewers@domain.com"], owners=["owners@domain.com"])
TEST_LEGAL = Legal(legaltags=["legaltag"], otherRelevantDataCountries=["US"], status="compliant")
TEST_WRONG_ID = "partition:entity-type:id"

# PVTModel
TEST_MPFM_CALIBRATION_ID = f"{PARTITION}:work-product-component--MultiPhaseFlowMeterCalibration:{KindVersion.V_1_0_0}"
TEST_PVT_MODEL_ID = f"{PARTITION}:work-product-component--PVTModel:{KindVersion.V_1_0_0}"
TEST_COMPONENT_SCENARIO_ID = f"{PARTITION}:work-product-component--ComponentScenario:{KindVersion.V_1_0_0}"
TEST_BLACK_OIL_TABLE_ID = f"{PARTITION}:work-product-component--BlackOilTable:{KindVersion.V_1_0_0}"

OSDU_GENERIC_RECORD = OsduStorageRecord(
    id="partition:type:identifier",
    kind="partition:wks:type:type_version",
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data={"dummy": "data"},
)

CORING_RECORD = Coring(
    id=TEST_CORING_ID,
    kind=TEST_CORING_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=CoringData(CoreNumber="CoreNumber", WellboreID=f"{TEST_WELLBORE_ID}:"),
)

GENERIC_FACILITY_RECORD = GenericFacility(
    id=TEST_GENERIC_FACILITY_ID,
    kind=TEST_GENERIC_FACILITY_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=GenericFacitilyData(),
)

GENERIC_SITE_RECORD = GenericSite(
    id=TEST_GENERIC_SITE_ID,
    kind=TEST_GENERIC_SITE_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=GenericSiteData(
        Name="Name",
        SiteTypeID="opendes:reference-data--SiteType:Coal:",
    ),
)

ROCKSAMPLE_RECORD = RockSample(
    id=TEST_ROCKSAMPLE_ID,
    kind=TEST_ROCKSAMPLE_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=RockSampleData(
        CoringID=f"{TEST_CORING_ID}:",
        WellboreID=f"{TEST_WELLBORE_ID}:",
    ),
)

SAMPLE_RECORD = Sample(
    id=TEST_SAMPLE_ID,
    kind=TEST_SAMPLE_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=SampleData(
        ResourceHomeRegionID="opendes:reference-data--OSDURegion:Region:",
    ),
)

SAMPLE_ACQUISITION_JOB_RECORD = SampleAcquisitionJob(
    id=TEST_SAMPLE_ACQUISITION_JOB_ID,
    kind=TEST_SAMPLE_ACQUISITION_JOB_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=SampleAcquisitionJobData(
        JobTypeID="JobTypeID",
        ReferenceJobNumber="ReferenceJobNumber",
    ),
)

SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD = SampleChainOfCustodyEvent(
    id=TEST_SAMPLE_CHAIN_OF_CUSTODY_EVENT_ID,
    kind=TEST_SAMPLE_CHAIN_OF_CUSTODY_EVENT_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=SCOCEData(
        CustodyEventLocationID="opendes:master-data--Organisation:Organisation:",
        CustodyEventTypeID="opendes:reference-data--CustodyEventType:SubSampleLive:",
    ),
)

SAMPLE_CONTAINER_RECORD = SampleContainer(
    id=TEST_SAMPLE_CONTAINER_ID,
    kind=TEST_SAMPLE_CONTAINER_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=SampleContainerData(
        OperatingConditionRating=OperatingConditionRating(
            Temperature=1.0,
            Pressure=1.0,
        ),
        SampleContainerServiceTypeIDs=["opendes:reference-data--SampleContainerServiceType:NonHydrocarbon:"],
        ManufacturerID="opendes:master-data--Organisation:Organisation:",
        SampleContainerTypeID="opendes:reference-data--SampleContainerType:Pressurized.NotPressureCompensated:",
        ContainerIdentifier="BTL-12345",
        Capacity=100,
    ),
)

ROCKSAMPLEANALYSIS_RECORD = RockSampleAnalysis(
    id=TEST_ROCKSAMPLEANALYSIS_ID,
    kind=TEST_ROCKSAMPLEANALYSIS_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=RockSampleAnalysisData(
        CoringID=f"{TEST_CORING_ID}:",
        WellboreID=f"{TEST_WELLBORE_ID}:",
    ),
)

PVT_RECORD = PVT(
    id=TEST_PVT_ID,
    kind=TEST_PVT_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=PVTData(
        PVTTests=PVTTests(
            ConstantCompositionExpansionTestID=[f"{TEST_CCE_ID}:"],
            DifferentialLiberationTestID=[f"{TEST_DL_ID}:"],
        ),
    ),
)

CCE_RECORD = ConstantCompositionExpansionTest(
    id=TEST_CCE_ID,
    kind=TEST_CCE_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=CceData(
        PVTReportID=f"{TEST_PVT_ID}:",
        FluidSampleID=f"{TEST_FLUIDSAMPLE_ID}:",
        LabSampleIdentifier="20207905-20",
        LaboratoryName="CoreLab",
    ),
)

DL_RECORD = DifferentialLiberationTest(
    id=TEST_DL_ID,
    kind=TEST_DL_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=DifLibData(
        PVTReportID=f"{TEST_PVT_ID}:",
        FluidSampleID=f"{TEST_FLUIDSAMPLE_ID}:",
        LabSampleIdentifier="20207905-20",
        LaboratoryName="CoreLab",
    ),
)

TRANSPORT_RECORD = TransportTest(
    id=TEST_TRANSPORT_ID,
    kind=TEST_TRANSPORT_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=TransportTestData(
        PVTReportID=f"{TEST_PVT_ID}:",
        FluidSampleID=f"{TEST_FLUIDSAMPLE_ID}:",
        LabSampleIdentifier="20207905-20",
        LaboratoryName="CoreLab",
    ),
)

COMPOSITIONALANALYSIS_RECORD = CompositionalAnalysis(
    id=TEST_COMPOSITIONALANALYSIS_ID,
    kind=TEST_COMPOSITIONALANALYSIS_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=CompositionalAnalysisData(
        PVTReportID=f"{TEST_PVT_ID}:",
        FluidSampleID=f"{TEST_FLUIDSAMPLE_ID}:",
        LabSampleIdentifier="20207905-20",
        LaboratoryName="CoreLab",
    ),
)

MULTISTAGESEPARATOR_RECORD = MultiStageSeparatorTest(
    id=TEST_MSS_ID,
    kind=TEST_MSS_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=MSSData(
        PVTReportID=f"{TEST_PVT_ID}:",
        FluidSampleID=f"{TEST_FLUIDSAMPLE_ID}:",
        LabSampleIdentifier="20207905-20",
        LaboratoryName="CoreLab",
    ),
)

SWELLING_RECORD = SwellingTest(
    id=TEST_SWELLING_ID,
    kind=TEST_SWELLING_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=SwellingData(
        PVTReportID=f"{TEST_PVT_ID}:",
        FluidSampleID=f"{TEST_FLUIDSAMPLE_ID}:",
        LabSampleIdentifier="20207905-20",
        LaboratoryName="CoreLab",
    ),
)

CVD_RECORD = ConstantVolumeDepletionTest(
    id=TEST_CVD_ID,
    kind=TEST_CVD_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=CVDData(
        PVTReportID=f"{TEST_PVT_ID}:",
        FluidSampleID=f"{TEST_FLUIDSAMPLE_ID}:",
        LabSampleIdentifier="20207905-20",
        LaboratoryName="CoreLab",
    ),
)

WATERANALYSIS_RECORD = WaterAnalysisTest(
    id=TEST_WATERANALYSIS_ID,
    kind=TEST_WATERANALYSIS_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=WaterAnalysisData(
        PVTReportID=f"{TEST_PVT_ID}:",
        FluidSampleID=f"{TEST_FLUIDSAMPLE_ID}:",
        LabSampleIdentifier="20207905-20",
        LaboratoryName="CoreLab",
    ),
)

STO_RECORD = StockTankOilAnalysisTest(
    id=TEST_STO_ID,
    kind=TEST_STO_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=STOData(
        PVTReportID=f"{TEST_PVT_ID}:",
        FluidSampleID=f"{TEST_FLUIDSAMPLE_ID}:",
        LabSampleIdentifier="20207905-20",
        LaboratoryName="CoreLab",
    ),
)

INTERFACIAL_TENSION_RECORD = InterfacialTensionTest(
    id=TEST_INTERFACIAL_TENSION_ID,
    kind=TEST_INTERFACIAL_TENSION_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=InterfacialTensionData(
        PVTReportID=f"{TEST_PVT_ID}:",
        FluidSampleID=f"{TEST_FLUIDSAMPLE_ID}:",
        LabSampleIdentifier="20207905-20",
        LaboratoryName="CoreLab",
    ),
)

VLE_RECORD = VaporLiquidEquilibriumTest(
    id=TEST_VLE_ID,
    kind=TEST_VLE_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=VLEData(
        PVTReportID=f"{TEST_PVT_ID}:",
        FluidSampleID=f"{TEST_FLUIDSAMPLE_ID}:",
        LabSampleIdentifier="20207905-20",
        LaboratoryName="CoreLab",
    ),
)

MCM_RECORD = MultipleContactMiscibilityTest(
    id=TEST_MCM_ID,
    kind=TEST_MCM_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=MCMData(
        PVTReportID=f"{TEST_PVT_ID}:",
        FluidSampleID=f"{TEST_FLUIDSAMPLE_ID}:",
        LabSampleIdentifier="20207905-20",
        LaboratoryName="CoreLab",
    ),
)

SLIMTUBETEST_RECORD = SlimTubeTest(
    id=TEST_SLIMTUBETEST_ID,
    kind=TEST_SLIMTUBETEST_KIND,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=SlimTubeTestData(
        PVTReportID=f"{TEST_PVT_ID}:",
        FluidSampleID=f"{TEST_FLUIDSAMPLE_ID}:",
        LabSampleIdentifier="20207905-20",
        LaboratoryName="CoreLab",
    ),
)

SAMPLESANALYSESREPORT_RECORD_V2 = SamplesAnalysesReport(
    id=TEST_SAMPLESANALYSESREPORT_ID,
    kind=TEST_SAMPLESANALYSESREPORT_KIND_V2,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=SamplesAnalysesReportData(
        SampleIDs=[f"{PARTITION}:master-data--Sample:sample_test_id:"],
        ReportSampleIdentifiers=["45H", "49H"],
        SampleAnalysisTypeIDs=[
            "opendes:reference-data--SampleAnalysisType:CapillaryPressureGasOil:",
            "opendes:reference-data--SampleAnalysisType:CentrifugeDrainageGasOil:",
        ],
        SamplesAnalysisCategoryTagIDs=[
            "opendes:reference-data--SamplesAnalysisCategoryTag:SCAL:",
        ],
    ),
)

SAMPLESANALYSESREPORT_RECORD_V1 = copy.deepcopy(SAMPLESANALYSESREPORT_RECORD_V2)
SAMPLESANALYSESREPORT_RECORD_V1.kind = TEST_SAMPLESANALYSESREPORT_KIND_V1

SAMPLESANALYSIS_RECORD_V1 = SamplesAnalysisV1(
    id=TEST_SAMPLESANALYSIS_ID,
    kind=TEST_SAMPLESANALYSIS_KIND_V1,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=SamplesAnalysisDataV1(
        ParentSamplesAnalysesReports=[f"{TEST_SAMPLESANALYSESREPORT_ID}:"],
    ),
)

SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V1 = copy.deepcopy(SAMPLESANALYSIS_RECORD_V1)
SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V1.data.ParentSamplesAnalysesReports = []

SAMPLESANALYSIS_RECORD_V2 = SamplesAnalysis(
    id=TEST_SAMPLESANALYSIS_ID,
    kind=TEST_SAMPLESANALYSIS_KIND_V2,
    acl=TEST_ACL,
    legal=TEST_LEGAL,
    data=SamplesAnalysisData(
        ParentSamplesAnalysesReports=[
            ParentSamplesAnalysesReport(
                ParentSamplesAnalysesReportID=f"{TEST_SAMPLESANALYSESREPORT_ID}:",
            ),
        ],
    ),
)

SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V2 = copy.deepcopy(SAMPLESANALYSIS_RECORD_V2)
SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V1.data.ParentSamplesAnalysesReports = []


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
PVT_STORAGE_SERVICE_200_RESPONSE = {
    "recordCount": 1,
    "recordIds": [TEST_PVT_ID],
    "skippedRecordIds": [],
    "recordIdVersions": [f"{TEST_PVT_ID}:1"],
}
PVT_QUERY_STORAGE_SERVICE_200_RESPONSE = {
    "records": [
        PVT_RECORD.dict(exclude_none=True),
    ],
    "invalidRecords": [],
    "retryRecords": [],
}
PVT_QUERY_STORAGE_SERVICE_INVALID_PVT_200_RESPONSE = {
    "records": [
        PVT_RECORD.dict(exclude_none=True),
    ],
    "invalidRecords": [],
    "retryRecords": [],
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
EXPECTED_200_CREATED_PVT_UPDATED_RESPONSE = {
    "recordCount": 2,
    "recordIdVersions": ["partition:type:test:1", "partition:pvt_type:test:1"],
    "skippedRecordCount": 0,
}

STORAGE_SERVICE_200_VERSIONS_RESPONSE = {
    "recordId": "partition:type:test",
    "versions": [1, 2],
}
EXPECTED_200_VERSIONS_RESPONSE = STORAGE_SERVICE_200_VERSIONS_RESPONSE
EXPECTED_400_RESPONSE_ON_INVALID_PARENT_PVT = {
    "code": 400, "reason": "Parent record is invalid. ['data.PVTTests: value is not a valid dict']",
}

ERROR_TITLE = "Request can't be processed due to missing referenced records."
ERROR_DETAILS = f"Fields checked: ['ParentSamplesAnalysesReports']. Records not found: ['{TEST_SAMPLESANALYSESREPORT_ID}']"
EXPECTED_422_RESPONSE_ON_MISSING_SAMPLESANALYSESREPORT = {
    "code": 422,
    "reason": f"{ERROR_TITLE} {ERROR_DETAILS}",
}

CORING_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/coringreports"
ROCKSAMPLE_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/rocksamples"
ROCKSAMPLEANALYSIS_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/rocksampleanalyses"
PVT_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/pvtreports"
CCE_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/ccereports"
PVT_SOURCE_ENDPOINT_PATH = f"{PVT_ENDPOINT_PATH}/{TEST_PVT_ID}/source"
DIF_LIB_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/difflibreports"
TRANSPORT_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/transporttests"
COMPOSITIONALANALYSIS_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/compositionalanalysisreports"
MSS_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/multistageseparatortests"
SWELLING_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/swellingtests"
CVD_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/constantvolumedepletiontests"
STO_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/stocktankoilanalysisreports"
INTERFACIAL_TENSION_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/interfacialtensiontests"
VLE_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/vaporliquidequilibriumtests"
MCM_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/multiplecontactmiscibilitytests"
SLIMTUBETEST_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/slimtubetests"
SAMPLESANALYSES_REPORT_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/samplesanalysesreport"
CAP_PRESSURE_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/capillarypressuretests"
RELATIVE_PERMEABILITY_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/relativepermeabilitytests"
FRACTIONATION_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/fractionationtests"
EXTRACTION_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/extractiontests"
PHYS_CHEM_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/physicalchemistrytests"
ELECTRICAL_PROPERTIES_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/electricalproperties"
ROCK_COMPRESSIBILITY_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/rockcompressibilities"
WATER_GAS_RELATIVE_PERMEABILITY_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/watergasrelativepermeabilities"
FORMATION_RESISTIVITY_INDEX_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/formationresistivityindexes"

# V2 endpoint paths
SAMPLESANALYSES_REPORT_ENDPOINT_PATH_V2 = f"/api/os-rafs-ddms/{API_VERSION_V2}/samplesanalysesreport"
SAMPLESANALYSIS_ENDPOINT_PATH_V2 = f"/api/os-rafs-ddms/{API_VERSION_V2}/samplesanalysis"
MASTER_DATA_ENDPOINT_PATH_V2 = f"/api/os-rafs-ddms/{API_VERSION_V2}/masterdata"

RCA_DATA_ENDPOINT_PATH = f"{ROCKSAMPLEANALYSIS_ENDPOINT_PATH}/{TEST_ROCKSAMPLEANALYSIS_ID}/rca/data"
RCA_SOURCE_ENDPOINT_PATH = f"{ROCKSAMPLEANALYSIS_ENDPOINT_PATH}/{TEST_ROCKSAMPLEANALYSIS_ID}/rca/source"
CCE_DATA_ENDPOINT_PATH = f"{CCE_ENDPOINT_PATH}/{TEST_CCE_ID}/data"
CCE_SOURCE_ENDPOINT_PATH = f"{CCE_ENDPOINT_PATH}/{TEST_CCE_ID}/source"
DIF_LIB_DATA_ENDPOINT_PATH = f"{DIF_LIB_ENDPOINT_PATH}/{TEST_DL_ID}/data"
DIF_LIB_SOURCE_ENDPOINT_PATH = f"{DIF_LIB_ENDPOINT_PATH}/{TEST_DL_ID}/source"
TRANSPORT_DATA_ENDPOINT_PATH = f"{TRANSPORT_ENDPOINT_PATH}/{TEST_TRANSPORT_ID}/data"
TRANSPORT_SOURCE_ENDPOINT_PATH = f"{TRANSPORT_ENDPOINT_PATH}/{TEST_TRANSPORT_ID}/source"
COMPOSITIONALANALYSIS_DATA_ENDPOINT_PATH = f"{COMPOSITIONALANALYSIS_ENDPOINT_PATH}/{TEST_COMPOSITIONALANALYSIS_ID}/data"
COMPOSITIONALANALYSIS_SOURCE_ENDPOINT_PATH = f"{COMPOSITIONALANALYSIS_ENDPOINT_PATH}/{TEST_COMPOSITIONALANALYSIS_ID}/source"
MCM_DATA_ENDPOINT_PATH = f"{MCM_ENDPOINT_PATH}/{TEST_MCM_ID}/data"
MCM_SOURCE_ENDPOINT_PATH = f"{MCM_ENDPOINT_PATH}/{TEST_MCM_ID}/source"
MSS_DATA_ENDPOINT_PATH = f"{MSS_ENDPOINT_PATH}/{TEST_MSS_ID}/data"
MSS_SOURCE_ENDPOINT_PATH = f"{MSS_ENDPOINT_PATH}/{TEST_MSS_ID}/source"
SWELLING_DATA_ENDPOINT_PATH = f"{SWELLING_ENDPOINT_PATH}/{TEST_SWELLING_ID}/data"
SWELLING_SOURCE_ENDPOINT_PATH = f"{SWELLING_ENDPOINT_PATH}/{TEST_SWELLING_ID}/source"
CVD_DATA_ENDPOINT_PATH = f"{CVD_ENDPOINT_PATH}/{TEST_CVD_ID}/data"
CVD_SOURCE_ENDPOINT_PATH = f"{CVD_ENDPOINT_PATH}/{TEST_CVD_ID}/source"
WATERANALYSIS_ENDPOINT_PATH = f"/api/os-rafs-ddms/{API_VERSION}/wateranalysisreports"
STO_DATA_ENDPOINT_PATH = f"{STO_ENDPOINT_PATH}/{TEST_STO_ID}/data"
STO_SOURCE_ENDPOINT_PATH = f"{STO_ENDPOINT_PATH}/{TEST_STO_ID}/source"
WATERANALYSIS_DATA_ENDPOINT_PATH = f"{WATERANALYSIS_ENDPOINT_PATH}/{TEST_WATERANALYSIS_ID}/data"
WATERANALYSIS_SOURCE_ENDPOINT_PATH = f"{WATERANALYSIS_ENDPOINT_PATH}/{TEST_WATERANALYSIS_ID}/source"
INTERFACIAL_TENSION_DATA_ENDPOINT_PATH = f"{INTERFACIAL_TENSION_ENDPOINT_PATH}/{TEST_INTERFACIAL_TENSION_ID}/data"
INTERFACIAL_TENSION_SOURCE_ENDPOINT_PATH = f"{INTERFACIAL_TENSION_ENDPOINT_PATH}/{TEST_INTERFACIAL_TENSION_ID}/source"
VLE_DATA_ENDPOINT_PATH = f"{VLE_ENDPOINT_PATH}/{TEST_VLE_ID}/data"
VLE_SOURCE_ENDPOINT_PATH = f"{VLE_ENDPOINT_PATH}/{TEST_VLE_ID}/source"
SLIMTUBE_DATA_ENDPOINT_PATH = f"{SLIMTUBETEST_ENDPOINT_PATH}/{TEST_SLIMTUBETEST_ID}/data"
SLIMTUBE_SOURCE_ENDPOINT_PATH = f"{SLIMTUBETEST_ENDPOINT_PATH}/{TEST_SLIMTUBETEST_ID}/source"
RELATIVE_PERMEABILITY_DATA_ENDPOINT_PATH = f"{RELATIVE_PERMEABILITY_ENDPOINT_PATH}/{TEST_RELATIVE_PERMEABILITY_ID}/data"
RELATIVE_PERMEABILITY_SOURCE_ENDPOINT_PATH = f"{RELATIVE_PERMEABILITY_ENDPOINT_PATH}/{TEST_RELATIVE_PERMEABILITY_ID}/source"
CAP_PRESSURE_DATA_ENDPOINT_PATH_API_V1 = f"{CAP_PRESSURE_ENDPOINT_PATH}/{TEST_CAP_PRESSURE_ID}/data"
FRACTIONATION_DATA_ENDPOINT_PATH = f"{FRACTIONATION_ENDPOINT_PATH}/{TEST_FRACTIONATION_ID}/data"
FRACTIONATION_SOURCE_ENDPOINT_PATH = f"{FRACTIONATION_ENDPOINT_PATH}/{TEST_FRACTIONATION_ID}/source"
EXTRACTION_DATA_ENDPOINT_PATH = f"{EXTRACTION_ENDPOINT_PATH}/{TEST_EXTRACTION_ID}/data"
EXTRACTION_SOURCE_ENDPOINT_PATH = f"{EXTRACTION_ENDPOINT_PATH}/{TEST_EXTRACTION_ID}/source"
PHYS_CHEM_DATA_ENDPOINT_PATH = f"{PHYS_CHEM_ENDPOINT_PATH}/{TEST_PHYS_CHEM_ID}/data"
PHYS_CHEM_SOURCE_ENDPOINT_PATH = f"{PHYS_CHEM_ENDPOINT_PATH}/{TEST_PHYS_CHEM_ID}/source"
WATER_GAS_REL_PERM_DATA_ENDPOINT_PATH = f"{WATER_GAS_RELATIVE_PERMEABILITY_ENDPOINT_PATH}/{TEST_WATER_GAS_RELATIVE_PERMEABILITY_ID}/data"
WATER_GAS_REL_PERM_SOURCE_ENDPOINT_PATH = f"{WATER_GAS_RELATIVE_PERMEABILITY_ENDPOINT_PATH}/{TEST_WATER_GAS_RELATIVE_PERMEABILITY_ID}/source"
ROCK_COMPRESSIBILITY_DATA_ENDPOINT_PATH = f"{ROCK_COMPRESSIBILITY_ENDPOINT_PATH}/{TEST_ROCK_COMPRESSIBILITY_ID}/data"
ROCK_COMPRESSIBILITY_SOURCE_ENDPOINT_PATH = f"{ROCK_COMPRESSIBILITY_ENDPOINT_PATH}/{TEST_ROCK_COMPRESSIBILITY_ID}/source"
ELECTRICAL_PROPERTIES_DATA_ENDPOINT_PATH_API_V1 = f"{ELECTRICAL_PROPERTIES_ENDPOINT_PATH}/{TEST_ELECTRICAL_PROPERTIES_ID}/data"
ELECTRICAL_PROPERTIES_SOURCE_ENDPOINT_PATH_API_V1 = f"{ELECTRICAL_PROPERTIES_ENDPOINT_PATH}/{TEST_ELECTRICAL_PROPERTIES_ID}/source"
FORMATION_RESISTIVITY_INDEX_DATA_ENDPOINT_PATH = f"{FORMATION_RESISTIVITY_INDEX_ENDPOINT_PATH}/{TEST_FORMATION_RESISTIVITY_INDEX_ID}/data"
FORMATION_RESISTIVITY_INDEX_SOURCE_ENDPOINT_PATH = f"{FORMATION_RESISTIVITY_INDEX_ENDPOINT_PATH}/{TEST_FORMATION_RESISTIVITY_INDEX_ID}/source"

# data endpoints v2
BASE_V2_PATH = f"api/os-rafs-ddms/{API_VERSION_V2}"

SAMPLESANALYSIS_ENDPOINT_PATH = f"{BASE_V2_PATH}/samplesanalysis"
BASE_DATA_V2_PATH = f"{SAMPLESANALYSIS_ENDPOINT_PATH}/{TEST_SAMPLESANALYSIS_ID}"

common_relative_paths_v2 = CommonRelativePathsV2()


class TestContentPathsApiV2:
    RCA = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.ROUTINECOREANALYSIS}"
    CCE = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.CCE}"
    DIFF_LIB = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.DIFF_LIB}"
    TRANSPORT_TEST = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.TRANSPORT_TEST}"
    COMPOSITIONAL_ANALYSIS = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.COMPOSITIONAL_ANALYSIS}"
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
    UNIAXIAL_TEST = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.UNIAXIAL_TEST}"
    GCMSMS_ANALYSIS = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.GCMSMS_ANALYSIS}"
    CEC_CONTENT = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.CEC_CONTENT}"
    ELECTRICAL_PROPERTIES = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.ELECTRICAL_PROPERTIES}"
    TRIAXIAL_TEST = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.TRIAXIAL_TEST}"
    CAP_PRESSURE = f"{BASE_DATA_V2_PATH}{common_relative_paths_v2.CAP_PRESSURE}"
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


class BulkDatasetIdV1(NamedTuple):
    RCA = f"{PARTITION}:{FILE_GENERIC_TYPE}:routine-core-analysis-{TEST_DATASET_UID}"
    CCE = f"{PARTITION}:{FILE_GENERIC_TYPE}:constant-composition-expansion-{TEST_DATASET_UID}"
    DIF_LIB = f"{PARTITION}:{FILE_GENERIC_TYPE}:differential-liberation-{TEST_DATASET_UID}"
    TRANSPORT = f"{PARTITION}:{FILE_GENERIC_TYPE}:transport-test-{TEST_DATASET_UID}"
    MCM = f"{PARTITION}:{FILE_GENERIC_TYPE}:multiple-contact-miscibility-{TEST_DATASET_UID}"
    MSS = f"{PARTITION}:{FILE_GENERIC_TYPE}:multi-stage-separator-{TEST_DATASET_UID}"
    CA = f"{PARTITION}:{FILE_GENERIC_TYPE}:compositionalanalysis-{TEST_DATASET_UID}"
    SWELLING = f"{PARTITION}:{FILE_GENERIC_TYPE}:swelling-{TEST_DATASET_UID}"
    CVD = f"{PARTITION}:{FILE_GENERIC_TYPE}:constantvolumedepletiontest-{TEST_DATASET_UID}"
    STO = f"{PARTITION}:{FILE_GENERIC_TYPE}:stoanalysis-{TEST_DATASET_UID}"
    WA = f"{PARTITION}:{FILE_GENERIC_TYPE}:wateranalysis-{TEST_DATASET_UID}"
    IT = f"{PARTITION}:{FILE_GENERIC_TYPE}:interfacialtension-{TEST_DATASET_UID}"
    VLE = f"{PARTITION}:{FILE_GENERIC_TYPE}:vaporliquidequilibriumtest-{TEST_DATASET_UID}"
    SLIMTUBE = f"{PARTITION}:{FILE_GENERIC_TYPE}:slimtube-test-{TEST_DATASET_UID}"
    RELATIVE_PERMEABILITY = f"{PARTITION}:{FILE_GENERIC_TYPE}:relative-permeability-{TEST_DATASET_UID}"
    CAP_PRESSURE = f"{PARTITION}:{FILE_GENERIC_TYPE}:capillary-pressure-test-{TEST_DATASET_UID}"
    FRACTIONATION = f"{PARTITION}:{FILE_GENERIC_TYPE}:fractionation-{TEST_DATASET_UID}"
    EXTRACTION = f"{PARTITION}:{FILE_GENERIC_TYPE}:extraction-{TEST_DATASET_UID}"
    PHYS_CHEM = f"{PARTITION}:{FILE_GENERIC_TYPE}:physical-chemistry-test-{TEST_DATASET_UID}"
    WATER_GAS_RELATIVE_PERMEABILITY = f"{PARTITION}:{FILE_GENERIC_TYPE}:water-gas-relative-permeability-test-{TEST_DATASET_UID}"
    ROCK_COMPRESSIBILITY = f"{PARTITION}:{FILE_GENERIC_TYPE}:rock-compressibility-{TEST_DATASET_UID}"
    ELECTRICAL_PROPERTIES = f"{PARTITION}:{FILE_GENERIC_TYPE}:electricalproperties-{TEST_DATASET_UID}"
    FORMATION_RESISTIVITY_INDEX = f"{PARTITION}:{FILE_GENERIC_TYPE}:formationresistivityindexes-{TEST_DATASET_UID}"


class BulkDatasetIdV2(NamedTuple):
    RCA = f"{PARTITION}:{FILE_GENERIC_TYPE}:routinecoreanalysis-{TEST_DATASET_UID}"
    CCE = f"{PARTITION}:{FILE_GENERIC_TYPE}:constantcompositionexpansion-{TEST_DATASET_UID}"
    DIFF_LIB = f"{PARTITION}:{FILE_GENERIC_TYPE}:differentialliberation-{TEST_DATASET_UID}"
    TRANSPORT_TEST = f"{PARTITION}:{FILE_GENERIC_TYPE}:transport-{TEST_DATASET_UID}"
    COMPOSITIONAL_ANALYSIS = f"{PARTITION}:{FILE_GENERIC_TYPE}:compositionalanalysis-{TEST_DATASET_UID}"
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
    UNIAXIAL_TEST = f"{PARTITION}:{FILE_GENERIC_TYPE}:uniaxial-{TEST_DATASET_UID}"
    GCMSMS_ANALYSIS = f"{PARTITION}:{FILE_GENERIC_TYPE}:gcmsms-{TEST_DATASET_UID}"
    CEC_CONTENT = f"{PARTITION}:{FILE_GENERIC_TYPE}:cec-{TEST_DATASET_UID}"
    TRIAXIAL_TEST = f"{PARTITION}:{FILE_GENERIC_TYPE}:triaxial-{TEST_DATASET_UID}"
    CAP_PRESSURE = f"{PARTITION}:{FILE_GENERIC_TYPE}:capillarypressure-{TEST_DATASET_UID}"
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


with open(f"{dir_path}/schemas/wpc_definitions.json") as fp:
    WPC_DEFINITIONS = json.load(fp)

with open(f"{dir_path}/schemas/samplesanalysesreport.json") as fp:
    SAMPLES_ANALYSES_REPORT_SCHEMA = json.load(fp)
    SAMPLES_ANALYSES_REPORT_SCHEMA["definitions"] = WPC_DEFINITIONS

with open(f"{dir_path}/schemas/samplesanalysis.json") as fp:
    SAMPLES_ANALYSIS_SCHEMA = json.load(fp)
    SAMPLES_ANALYSIS_SCHEMA["definitions"] = WPC_DEFINITIONS

with open(f"{dir_path}/schemas/sample.json") as fp:
    SAMPLE_SCHEMA = json.load(fp)


# PVT Model
PVT_MODEL_ENDPOINT_PATH = f"{BASE_V2_PATH}/pvtmodel"
BASE_MPFM_CALIBRATION_CONTENT_PATH = f"{PVT_MODEL_ENDPOINT_PATH}/{TEST_MPFM_CALIBRATION_ID}"
BASE_PVT_MODEL_CONTENT_PATH = f"{PVT_MODEL_ENDPOINT_PATH}/{TEST_PVT_MODEL_ID}"
BASE_COMPONENT_SCENARIO_CONTENT_PATH = f"{PVT_MODEL_ENDPOINT_PATH}/{TEST_COMPONENT_SCENARIO_ID}"
BASE_BLACK_OIL_TABLE_CONTENT_PATH = f"{PVT_MODEL_ENDPOINT_PATH}/{TEST_BLACK_OIL_TABLE_ID}"

pvt_model_relative_paths = PVTModelRelativePaths()


class TestContentPathsPVTModel:
    MPFM_CALIBRATION = f"{BASE_MPFM_CALIBRATION_CONTENT_PATH}{pvt_model_relative_paths.MPFM_CALIBRATION}"
    EOS = f"{BASE_PVT_MODEL_CONTENT_PATH}{pvt_model_relative_paths.EOS}"
    COMPONENT_SCENARIO = f"{BASE_COMPONENT_SCENARIO_CONTENT_PATH}{pvt_model_relative_paths.COMPONENT_SCENARIO}"
    BLACK_OIL_TABLE = f"{BASE_BLACK_OIL_TABLE_CONTENT_PATH}{pvt_model_relative_paths.BLACK_OIL_TABLE}"


class BulkDatasetIdPVTModel(NamedTuple):
    MPFM_CALIBRATION = f"{PARTITION}:{FILE_GENERIC_TYPE}:mpfmcalibrationdata-{TEST_DATASET_UID}"
    EOS = f"{PARTITION}:{FILE_GENERIC_TYPE}:equationofstatedata-{TEST_DATASET_UID}"
    COMPONENT_SCENARIO = f"{PARTITION}:{FILE_GENERIC_TYPE}:componentscenariodata-{TEST_DATASET_UID}"
    BLACK_OIL_TABLE = f"{PARTITION}:{FILE_GENERIC_TYPE}:blackoiltabledata-{TEST_DATASET_UID}"
