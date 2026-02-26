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

from app.models.data_schemas.version import ContentSchemaVersion
from app.resources.paths import CommonRelativePathsV2
from app.models.data_schemas.sample_analysis_api_v2.routine_core_analysis_data_model_1_0_0 import RoutineCoreAnalysisModel100
from app.models.data_schemas.sample_analysis_api_v2.constant_composition_expansion_data_model_1_0_0 import ConstantCompositionExpansionModel100
from app.models.data_schemas.sample_analysis_api_v2.differential_liberation_data_model_1_0_0 import DifferentialLiberationModel100
from app.models.data_schemas.sample_analysis_api_v2.transport_data_model_1_0_0 import TransportModel100
from app.models.data_schemas.sample_analysis_api_v2.atmospheric_flash_and_compositional_analysis_data_model_1_0_0 import AtmosphericFlashAndCompositionalAnalysisModel100
from app.models.data_schemas.sample_analysis_api_v2.multi_stage_separator_data_model_1_0_0 import MultiStageSeparatorModel100
from app.models.data_schemas.sample_analysis_api_v2.swelling_data_model_1_0_0 import SwellingModel100
from app.models.data_schemas.sample_analysis_api_v2.constant_volume_depletion_data_model_1_0_0 import ConstantVolumeDepletionModel100
from app.models.data_schemas.sample_analysis_api_v2.water_analysis_data_model_1_0_0 import WaterAnalysisModel100
from app.models.data_schemas.sample_analysis_api_v2.interfacial_tension_data_model_1_0_0 import InterfacialTensionModel100
from app.models.data_schemas.sample_analysis_api_v2.vapor_liquid_equilibrium_data_model_1_0_0 import VaporLiquidEquilibriumModel100
from app.models.data_schemas.sample_analysis_api_v2.vapor_liquid_equilibrium_data_model_2_0_0 import VaporLiquidEquilibriumModel200
from app.models.data_schemas.sample_analysis_api_v2.multiple_contact_miscibility_data_model_1_0_0 import MultipleContactMiscibilityModel100
from app.models.data_schemas.sample_analysis_api_v2.slimtube_data_model_1_0_0 import SlimtubeModel100
from app.models.data_schemas.sample_analysis_api_v2.slimtube_data_model_2_0_0 import SlimtubeModel200
from app.models.data_schemas.sample_analysis_api_v2.extraction_data_model_1_0_0 import ExtractionModel100
from app.models.data_schemas.sample_analysis_api_v2.fractionation_data_model_1_0_0 import FractionationModel100
from app.models.data_schemas.sample_analysis_api_v2.relative_permeability_data_model_1_0_0 import RelativePermeabilityModel100
from app.models.data_schemas.sample_analysis_api_v2.rock_compressibility_data_model_1_0_0 import RockCompressibilityModel100
from app.models.data_schemas.sample_analysis_api_v2.electrical_properties_data_model_1_0_0 import ElectricalPropertiesModel100
from app.models.data_schemas.sample_analysis_api_v2.nmr_data_model_1_0_0 import NmrModel100
from app.models.data_schemas.sample_analysis_api_v2.multiple_salinity_tests_data_model_1_0_0 import MultipleSalinityTestsModel100
from app.models.data_schemas.sample_analysis_api_v2.gcms_alkanes_data_model_1_0_0 import GcmsAlkanesModel100
from app.models.data_schemas.sample_analysis_api_v2.gcms_aromatics_data_model_1_0_0 import GcmsAromaticsModel100
from app.models.data_schemas.sample_analysis_api_v2.gcms_ratios_data_model_1_0_0 import GcmsRatiosModel100
from app.models.data_schemas.sample_analysis_api_v2.gas_composition_analyses_data_model_1_0_0 import GasCompositionAnalysesModel100
from app.models.data_schemas.sample_analysis_api_v2.gas_chromatography_analyses_data_model_1_0_0 import GasChromatographyAnalysesModel100
from app.models.data_schemas.sample_analysis_api_v2.isotopes_data_model_1_0_0 import IsotopesModel100
from app.models.data_schemas.sample_analysis_api_v2.bulk_pyrolysis_analyses_data_model_1_0_0 import BulkPyrolysisAnalysesModel100
from app.models.data_schemas.sample_analysis_api_v2.core_gamma_data_model_1_0_0 import CoreGammaModel100
from app.models.data_schemas.sample_analysis_api_v2.uniaxial_data_model_1_0_0 import UniaxialModel100
from app.models.data_schemas.sample_analysis_api_v2.gcmsms_data_model_1_0_0 import GcmsmsModel100
from app.models.data_schemas.sample_analysis_api_v2.cec_data_model_1_0_0 import CecModel100
from app.models.data_schemas.sample_analysis_api_v2.triaxial_data_model_1_0_0 import TriaxialModel100
from app.models.data_schemas.sample_analysis_api_v2.wettability_index_data_model_1_0_0 import WettabilityIndexModel100
from app.models.data_schemas.sample_analysis_api_v2.tec_data_model_1_0_0 import TecModel100
from app.models.data_schemas.sample_analysis_api_v2.eds_mapping_data_model_1_0_0 import EdsMappingModel100
from app.models.data_schemas.sample_analysis_api_v2.xrf_data_model_1_0_0 import XrfModel100
from app.models.data_schemas.sample_analysis_api_v2.capillary_pressure_data_model_1_0_0 import CapillaryPressureModel100
from app.models.data_schemas.sample_analysis_api_v2.stock_tank_oil_analysis_data_model_1_0_0 import StockTankOilAnalysisModel100
from app.models.data_schemas.sample_analysis_api_v2.tensile_strength_data_model_1_0_0 import TensileStrengthModel100
from app.models.data_schemas.sample_analysis_api_v2.vitrinite_reflectance_data_model_1_0_0 import VitriniteReflectanceModel100
from app.models.data_schemas.sample_analysis_api_v2.xrd_data_model_1_0_0 import XrdModel100
from app.models.data_schemas.sample_analysis_api_v2.pdp_data_model_1_0_0 import PdpModel100
from app.models.data_schemas.sample_analysis_api_v2.crushed_rock_analysis_data_model_1_0_0 import CrushedRockAnalysisModel100
from app.models.data_schemas.sample_analysis_api_v2.mining_geotech_logging_data_model_1_0_0 import MiningGeotechLoggingModel100

RCA_MODELS = {
    ContentSchemaVersion.V_1_0_0: RoutineCoreAnalysisModel100,
}
CCE_MODELS = {
    ContentSchemaVersion.V_1_0_0: ConstantCompositionExpansionModel100,
}
DIFF_LIB_MODELS = {
    ContentSchemaVersion.V_1_0_0: DifferentialLiberationModel100,
}
TRANSPORT_TEST_MODELS = {
    ContentSchemaVersion.V_1_0_0: TransportModel100,
}
COMPOSITIONAL_ANALYSIS_MODELS = {
    ContentSchemaVersion.V_1_0_0: AtmosphericFlashAndCompositionalAnalysisModel100,
}
ATMOSPHERIC_FLASH_MODELS = {
    ContentSchemaVersion.V_1_0_0: AtmosphericFlashAndCompositionalAnalysisModel100,
}
MSS_MODELS = {
    ContentSchemaVersion.V_1_0_0: MultiStageSeparatorModel100,
}
SWELLING_MODELS = {
    ContentSchemaVersion.V_1_0_0: SwellingModel100,
}
CVD_MODELS = {
    ContentSchemaVersion.V_1_0_0: ConstantVolumeDepletionModel100,
}
WATER_ANALYSIS_MODELS = {
    ContentSchemaVersion.V_1_0_0: WaterAnalysisModel100,
}
INTERFACIAL_TENSION_MODELS = {
    ContentSchemaVersion.V_1_0_0: InterfacialTensionModel100,
}
VLE_MODELS = {
    ContentSchemaVersion.V_1_0_0: VaporLiquidEquilibriumModel100,
    ContentSchemaVersion.V_2_0_0: VaporLiquidEquilibriumModel200,
}
MCM_MODELS = {
    ContentSchemaVersion.V_1_0_0: MultipleContactMiscibilityModel100,
}
SLIMTUBE_MODELS = {
    ContentSchemaVersion.V_1_0_0: SlimtubeModel100,
    ContentSchemaVersion.V_2_0_0: SlimtubeModel200,
}
EXTRACTION_MODELS = {
    ContentSchemaVersion.V_1_0_0: ExtractionModel100,
}
FRACTIONATION_MODELS = {
    ContentSchemaVersion.V_1_0_0: FractionationModel100,
}
RELATIVE_PERMEABILITY_MODELS = {
    ContentSchemaVersion.V_1_0_0: RelativePermeabilityModel100,
}
ROCK_COMPRESSIBILITY_MODELS = {
    ContentSchemaVersion.V_1_0_0: RockCompressibilityModel100,
}
ELECTRICAL_PROPERTIES_MODELS = {
    ContentSchemaVersion.V_1_0_0: ElectricalPropertiesModel100,
}
NMR_MODELS = {
    ContentSchemaVersion.V_1_0_0: NmrModel100,
}
MULTIPLE_SALINITY_MODELS = {
    ContentSchemaVersion.V_1_0_0: MultipleSalinityTestsModel100,
}
GCMS_ALKANES_MODELS = {
    ContentSchemaVersion.V_1_0_0: GcmsAlkanesModel100,
}
GCMS_AROMATICS_MODELS = {
    ContentSchemaVersion.V_1_0_0: GcmsAromaticsModel100,
}
GCMS_RATIOS_MODELS = {
    ContentSchemaVersion.V_1_0_0: GcmsRatiosModel100,
}
GAS_CHROMATOGRAPHY_MODELS = {
    ContentSchemaVersion.V_1_0_0: GasChromatographyAnalysesModel100,
}
GAS_COMPOSITION_MODELS = {
    ContentSchemaVersion.V_1_0_0: GasCompositionAnalysesModel100,
}
ISOTOPE_ANALYSIS_MODELS = {
    ContentSchemaVersion.V_1_0_0: IsotopesModel100,
}
BULK_PYROLYSIS_MODELS = {
    ContentSchemaVersion.V_1_0_0: BulkPyrolysisAnalysesModel100,
}
CORE_GAMMA_MODELS = {
    ContentSchemaVersion.V_1_0_0: CoreGammaModel100,
}
UNIAXIAL_TEST_MODELS = {
    ContentSchemaVersion.V_1_0_0: UniaxialModel100,
}
GCMSMS_ANALYSIS_MODELS = {
    ContentSchemaVersion.V_1_0_0: GcmsmsModel100,
}
CEC_CONTENT_MODELS = {
    ContentSchemaVersion.V_1_0_0: CecModel100
}
TRIAXIAL_TEST_MODELS = {
    ContentSchemaVersion.V_1_0_0: TriaxialModel100
}
CAP_PRESSURE_MODELS = {
    ContentSchemaVersion.V_1_0_0: CapillaryPressureModel100
}
WETTABILITY_INDEX_MODELS = {
    ContentSchemaVersion.V_1_0_0: WettabilityIndexModel100
}
TEC_MODELS = {
    ContentSchemaVersion.V_1_0_0: TecModel100
}
EDS_MAPPING_MODELS = {
    ContentSchemaVersion.V_1_0_0: EdsMappingModel100
}
XRF_MODELS = {
    ContentSchemaVersion.V_1_0_0: XrfModel100
}
TENSILE_STRENGTH_MODELS = {
    ContentSchemaVersion.V_1_0_0: TensileStrengthModel100
}
VITRINITE_REFLECTANCE_MODELS = {
    ContentSchemaVersion.V_1_0_0: VitriniteReflectanceModel100,
}
XRD_MODELS = {
    ContentSchemaVersion.V_1_0_0: XrdModel100,
}
PDP_MODELS = {
    ContentSchemaVersion.V_1_0_0: PdpModel100,
}
STO_MODELS = {
    ContentSchemaVersion.V_1_0_0: StockTankOilAnalysisModel100,
}
CRUSHED_ROCK_ANALYSIS_MODELS = {
    ContentSchemaVersion.V_1_0_0: CrushedRockAnalysisModel100,
}
MINING_GEOTECH_LOGGING_MODELS = {
    ContentSchemaVersion.V_1_0_0: MiningGeotechLoggingModel100,
}

common_relative_paths_api_v2 = CommonRelativePathsV2()
PATH_TO_DATA_MODEL_VERSIONS_API_V2 = {
    common_relative_paths_api_v2.ROUTINECOREANALYSIS: RCA_MODELS,
    common_relative_paths_api_v2.CCE: CCE_MODELS,
    common_relative_paths_api_v2.DIFF_LIB: DIFF_LIB_MODELS,
    common_relative_paths_api_v2.TRANSPORT_TEST: TRANSPORT_TEST_MODELS,
    common_relative_paths_api_v2.COMPOSITIONAL_ANALYSIS: COMPOSITIONAL_ANALYSIS_MODELS,
    common_relative_paths_api_v2.ATMOSPHERIC_FLASH: ATMOSPHERIC_FLASH_MODELS,
    common_relative_paths_api_v2.MSS: MSS_MODELS,
    common_relative_paths_api_v2.SWELLING: SWELLING_MODELS,
    common_relative_paths_api_v2.CVD: CVD_MODELS,
    common_relative_paths_api_v2.WATER_ANALYSIS: WATER_ANALYSIS_MODELS,
    common_relative_paths_api_v2.INTERFACIAL_TENSION: INTERFACIAL_TENSION_MODELS,
    common_relative_paths_api_v2.VLE: VLE_MODELS,
    common_relative_paths_api_v2.MCM: MCM_MODELS,
    common_relative_paths_api_v2.SLIMTUBE: SLIMTUBE_MODELS,
    common_relative_paths_api_v2.EXTRACTION: EXTRACTION_MODELS,
    common_relative_paths_api_v2.FRACTIONATION: FRACTIONATION_MODELS,
    common_relative_paths_api_v2.RELATIVE_PERMEABILITY: RELATIVE_PERMEABILITY_MODELS,
    common_relative_paths_api_v2.ROCK_COMPRESSIBILITY: ROCK_COMPRESSIBILITY_MODELS,
    common_relative_paths_api_v2.ELECTRICAL_PROPERTIES: ELECTRICAL_PROPERTIES_MODELS,
    common_relative_paths_api_v2.NMR: NMR_MODELS,
    common_relative_paths_api_v2.MULTIPLE_SALINITY: MULTIPLE_SALINITY_MODELS,
    common_relative_paths_api_v2.GCMS_ALKANES: GCMS_ALKANES_MODELS,
    common_relative_paths_api_v2.GCMS_AROMATICS: GCMS_AROMATICS_MODELS,
    common_relative_paths_api_v2.GCMS_RATIOS: GCMS_RATIOS_MODELS,
    common_relative_paths_api_v2.GAS_CHROMATOGRAPHY: GAS_CHROMATOGRAPHY_MODELS,
    common_relative_paths_api_v2.GAS_COMPOSITION: GAS_COMPOSITION_MODELS,
    common_relative_paths_api_v2.ISOTOPE_ANALYSIS: ISOTOPE_ANALYSIS_MODELS,
    common_relative_paths_api_v2.BULK_PYROLYSIS: BULK_PYROLYSIS_MODELS,
    common_relative_paths_api_v2.CORE_GAMMA: CORE_GAMMA_MODELS,
    common_relative_paths_api_v2.UNIAXIAL_TEST: UNIAXIAL_TEST_MODELS,
    common_relative_paths_api_v2.GCMSMS_ANALYSIS: GCMSMS_ANALYSIS_MODELS,
    common_relative_paths_api_v2.CEC_CONTENT: CEC_CONTENT_MODELS,
    common_relative_paths_api_v2.TRIAXIAL_TEST: TRIAXIAL_TEST_MODELS,
    common_relative_paths_api_v2.CAP_PRESSURE: CAP_PRESSURE_MODELS,
    common_relative_paths_api_v2.WETTABILITY_INDEX: WETTABILITY_INDEX_MODELS,
    common_relative_paths_api_v2.TEC: TEC_MODELS,
    common_relative_paths_api_v2.EDS_MAPPING: EDS_MAPPING_MODELS,
    common_relative_paths_api_v2.XRF: XRF_MODELS,
    common_relative_paths_api_v2.TENSILE_STRENGTH: TENSILE_STRENGTH_MODELS,
    common_relative_paths_api_v2.VITRINITE_REFLECTANCE: VITRINITE_REFLECTANCE_MODELS,
    common_relative_paths_api_v2.XRD: XRD_MODELS,
    common_relative_paths_api_v2.PDP: PDP_MODELS,
    common_relative_paths_api_v2.STO: STO_MODELS,
    common_relative_paths_api_v2.CRUSHED_ROCK_ANALYSIS: CRUSHED_ROCK_ANALYSIS_MODELS,
    common_relative_paths_api_v2.MINING_GEOTECH_LOGGING: MINING_GEOTECH_LOGGING_MODELS,
}
