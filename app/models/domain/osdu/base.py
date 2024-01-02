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

from app.core.config import get_app_settings

from app.models.domain.osdu.MDCoring100 import Coring
from app.models.domain.osdu.MDGenericFacility100 import GenericFacility
from app.models.domain.osdu.MDGenericSite100 import GenericSite
from app.models.domain.osdu.MDRockSample100 import RockSample
from app.models.domain.osdu.MDSample200 import Sample as Sample200
from app.models.domain.osdu.MDSampleAcquisitionJob100 import SampleAcquisitionJob
from app.models.domain.osdu.MDSampleChainOfCustodyEvent100 import SampleChainOfCustodyEvent
from app.models.domain.osdu.MDSampleContainer100 import SampleContainer
from app.models.domain.osdu.WPCCompositionalAnalysis100 import CompositionalAnalysis
from app.models.domain.osdu.WPCCCE100 import ConstantCompositionExpansionTest
from app.models.domain.osdu.WPCConstantVolumeDepletionTest100 import ConstantVolumeDepletionTest
from app.models.domain.osdu.WPCDifLib100 import DifferentialLiberationTest
from app.models.domain.osdu.WPCMSS100 import MultiStageSeparatorTest
from app.models.domain.osdu.WPCPVT100 import PVT
from app.models.domain.osdu.WPCRockSampleAnalysis110 import RockSampleAnalysis
from app.models.domain.osdu.WPCSamplesAnalysis100 import SamplesAnalysis
from app.models.domain.osdu.WPCSamplesAnalysis100_V1 import SamplesAnalysis as SamplesAnalysisV1
from app.models.domain.osdu.WPCSlimTubeTest100 import SlimTubeTest
from app.models.domain.osdu.WPCTransportTest100 import TransportTest
from app.models.domain.osdu.WPCSwellingTest100 import SwellingTest
from app.models.domain.osdu.WPCWaterAnalysis100 import WaterAnalysisTest
from app.models.domain.osdu.WPCSTO100 import StockTankOilAnalysisTest
from app.models.domain.osdu.WPCInterfacialTension100 import InterfacialTensionTest
from app.models.domain.osdu.WPCVLE100 import VaporLiquidEquilibriumTest
from app.models.domain.osdu.WPCMCM100 import MultipleContactMiscibilityTest
from app.models.domain.osdu.WPCSamplesAnalysesReport100 import SamplesAnalysesReport
from app.models.domain.osdu.WPCSamplesAnalysesReport100_V1 import SamplesAnalysesReport as SamplesAnalysesReportV1

settings = get_app_settings()

CORING_100_KIND = f"{settings.schema_authority}:wks:master-data--Coring:1.0.0"
GENERIC_FACILITY_100_KIND = f"{settings.schema_authority}:wks:master-data--GenericFacility:1.0.0"
GENERIC_SITE_100_KIND = f"{settings.schema_authority}:wks:master-data--GenericSite:1.0.0"
SAMPLE_200_KIND = f"{settings.schema_authority}:wks:master-data--Sample:2.0.0"
SAMPLE_ACQUISITION_JOB_100_KIND = f"{settings.schema_authority}:wks:master-data--SampleAcquisitionJob:1.0.0"
SAMPLE_CHAIN_OF_CUSTODY_EVENT_100_KIND = f"{settings.schema_authority}:wks:master-data--SampleChainOfCustodyEvent:1.0.0"
SAMPLE_CONTAINER_100_KIND = f"{settings.schema_authority}:wks:master-data--SampleContainer:1.0.0"
ROCKSAMPLE_100_KIND = f"{settings.schema_authority}:wks:master-data--RockSample:1.0.0"
MASTER_DATA_KINDS_V2 = (
    GENERIC_FACILITY_100_KIND,
    GENERIC_SITE_100_KIND,
    SAMPLE_200_KIND,
    SAMPLE_ACQUISITION_JOB_100_KIND,
    SAMPLE_CHAIN_OF_CUSTODY_EVENT_100_KIND,
    SAMPLE_CONTAINER_100_KIND,
)

ROCKSAMPLEANALYSIS_KIND = f"{settings.schema_authority}:wks:work-product-component--RockSampleAnalysis:1.1.0"
PVT_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--PVT:1.0.0"
CCE_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--ConstantCompositionExpansionTest:1.0.0"
DIF_LIB_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--DifferentialLiberationTest:1.0.0"
TRANSPORT_TEST_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--TransportTest:1.0.0"
COMPOSITIONAL_ANALYSIS_KIND = (
    f"{settings.custom_schema_authority}:wks:work-product-component--CompositionalAnalysisTest:1.0.0"
)
MSS_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--MultiStageSeparatorTest:1.0.0"
SWELLING_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--SwellingTest:1.0.0"
CVD_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--ConstantVolumeDepletionTest:1.0.0"
WATER_ANALYSYS_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--WaterAnalysisTest:1.0.0"
STO_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--StockTankOilAnalysisTest:1.0.0"
INTERFACIAL_TENSION_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--InterfacialTensionTest:1.0.0"
VLE_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--VaporLiquidEquilibriumTest:1.0.0"
MCM_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--MultipleContactMiscibilityTest:1.0.0"
SLIMTUBETEST_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--SlimTubeTest:1.0.0"

SAMPLESANALYSIS_V1_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--SamplesAnalysis:1.0.0"
SAMPLESANALYSIS_KIND = f"{settings.schema_authority}:wks:work-product-component--SamplesAnalysis:1.0.0"

SAMPLES_ANALYSES_REPORT_V1_KIND = f"{settings.custom_schema_authority}:wks:work-product-component--SamplesAnalysesReport:1.0.0"
SAMPLES_ANALYSES_REPORT_KIND = f"{settings.schema_authority}:wks:work-product-component--SamplesAnalysesReport:1.0.0"

IMPLEMENTED_MODELS = {
    CORING_100_KIND: Coring,
    GENERIC_FACILITY_100_KIND: GenericFacility,
    GENERIC_SITE_100_KIND: GenericSite,
    ROCKSAMPLE_100_KIND: RockSample,
    SAMPLE_200_KIND: Sample200,
    SAMPLE_ACQUISITION_JOB_100_KIND: SampleAcquisitionJob,
    SAMPLE_CHAIN_OF_CUSTODY_EVENT_100_KIND: SampleChainOfCustodyEvent,
    SAMPLE_CONTAINER_100_KIND: SampleContainer,
    PVT_KIND: PVT,
    ROCKSAMPLEANALYSIS_KIND: RockSampleAnalysis,
    CCE_KIND: ConstantCompositionExpansionTest,
    DIF_LIB_KIND: DifferentialLiberationTest,
    TRANSPORT_TEST_KIND: TransportTest,
    COMPOSITIONAL_ANALYSIS_KIND: CompositionalAnalysis,
    MSS_KIND: MultiStageSeparatorTest,
    SWELLING_KIND: SwellingTest,
    CVD_KIND: ConstantVolumeDepletionTest,
    WATER_ANALYSYS_KIND: WaterAnalysisTest,
    STO_KIND: StockTankOilAnalysisTest,
    INTERFACIAL_TENSION_KIND: InterfacialTensionTest,
    VLE_KIND: VaporLiquidEquilibriumTest,
    MCM_KIND: MultipleContactMiscibilityTest,
    SLIMTUBETEST_KIND: SlimTubeTest,
    SAMPLES_ANALYSES_REPORT_V1_KIND: SamplesAnalysesReportV1,
    SAMPLES_ANALYSES_REPORT_KIND: SamplesAnalysesReport,
    SAMPLESANALYSIS_V1_KIND: SamplesAnalysisV1,
    SAMPLESANALYSIS_KIND: SamplesAnalysis,
}
