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

from pathlib import Path

CONFIG = {}

UPLOADED_FILES = [
    "opendes:dataset--File.Generic:File_1:",
    "opendes:dataset--File.Generic:File_2:",
    "opendes:dataset--File.Generic:File_3:",
]
SCHEMA_VERSION = "1.0.0"
PARQUET_HEADERS = {"Content-Type": "application/x-parquet"}
ACCEPT_HEADERS = "*/*;version={version}"

DATA_DIR = Path("tests", "integration", "data")
TEST_DATA_STORE = {}


class DataFiles:
    # v1
    RSA = "v1/rsa/rsa.json"
    RCA = "v1/rsa/rca.json"
    RCA_PARQUET = "v1/rsa/rca.parquet"
    RCA_WRONG_ID = "v1/rsa/rca_wrong_ids.json"
    RCA_MANDATORY_ATTRIBUTES_PARQUET = "v1/rsa/missing_attributes_rca.parquet"
    RS = "v1/rocksample.json"
    CORING = "v1/coring.json"
    SAR = "v1/samples_analyses_report/sar.json"

    # Sample Analyses tests
    CAP_PRESSURE = "v1/sample_analysis/cap_pressure/cap_pressure.json"
    CAP_PRESSURE_DATA = "v1/sample_analysis/cap_pressure/cap_pressure_data.json"
    CAP_PRESSURE_WRONG_ID = "v1/sample_analysis/cap_pressure/cap_pressure_wrong_ids.json"
    EXTRACTION = "v1/sample_analysis/extraction/extraction.json"
    EXTRACTION_DATA = "v1/sample_analysis/extraction/extraction_data.json"
    EXTRACTION_WRONG_ID = "v1/sample_analysis/extraction/extraction_wrong_ids.json"
    FRACTIONATION = "v1/sample_analysis/fractionation/fractionation.json"
    FRACTIONATION_DATA = "v1/sample_analysis/fractionation/fractionation_data.json"
    FRACTIONATION_WRONG_ID = "v1/sample_analysis/fractionation/fractionation_wrong_ids.json"
    PHYS_CHEM = "v1/sample_analysis/phys_chem/phys_chem.json"
    PHYS_CHEM_DATA = "v1/sample_analysis/phys_chem/phys_chem_data.json"
    PHYS_CHEM_WRONG_ID = "v1/sample_analysis/phys_chem/phys_chem_wrong_ids.json"
    RP = "v1/sample_analysis/relative_permeability/relative_permeability.json"
    RP_DATA = "v1/sample_analysis/relative_permeability/relative_permeability_data.json"
    RP_WRONG_ID = "v1/sample_analysis/relative_permeability/relative_permeability_wrong_ids.json"

    PVT = "v1/pvt.json"

    # PVT tests
    CCE = "v1/cce/cce.json"
    CCE_DATA = "v1/cce/cce_data.json"
    CCE_WRONG_ID = "v1/cce/cce_wrong_ids.json"
    DIF_LIB = "v1/dif_lib/dif_lib.json"
    DIF_LIB_DATA = "v1/dif_lib/dif_lib_data.json"
    DIF_LIB_WRONG_ID = "v1/dif_lib/dif_lib_wrong_ids.json"
    CA = "v1/compositional_analysis/ca.json"
    CA_DATA = "v1/compositional_analysis/ca_data.json"
    CA_WRONG_ID = "v1/compositional_analysis/ca_wrong_ids.json"
    CVD = "v1/constant_volume_depletion/cvd.json"
    CVD_DATA = "v1/constant_volume_depletion/cvd_data.json"
    CVD_WRONG_ID = "v1/constant_volume_depletion/cvd_wrong_ids.json"
    IT = "v1/interfacial_tension/it.json"
    IT_DATA = "v1/interfacial_tension/it_data.json"
    IT_WRONG_ID = "v1/interfacial_tension/it_wrong_ids.json"
    MSS = "v1/multi_stage_separator/mss.json"
    MSS_DATA = "v1/multi_stage_separator/mss_data.json"
    MSS_WRONG_ID = "v1/multi_stage_separator/mss_wrong_ids.json"
    MCM = "v1/multiple_contact_miscibility/mcm.json"
    MCM_DATA = "v1/multiple_contact_miscibility/mcm_data.json"
    MCM_WRONG_ID = "v1/multiple_contact_miscibility/mcm_wrong_ids.json"
    SLIM_TUBE = "v1/slim_tube/st.json"
    SLIM_TUBE_DATA = "v1/slim_tube/st_data.json"
    SLIM_TUBE_WRONG_ID = "v1/slim_tube/st_wrong_ids.json"
    STOA = "v1/stock_tank_oil_analysis/stoa.json"
    STOA_DATA = "v1/stock_tank_oil_analysis/stoa_data.json"
    STOA_WRONG_ID = "v1/stock_tank_oil_analysis/stoa_wrong_ids.json"
    ST = "v1/swelling_test/st.json"
    ST_DATA = "v1/swelling_test/st_data.json"
    ST_WRONG_ID = "v1/swelling_test/st_wrong_ids.json"
    TT = "v1/transport_test/tt.json"
    TT_DATA = "v1/transport_test/tt_data.json"
    TT_WRONG_ID = "v1/transport_test/tt_wrong_ids.json"
    VLE = "v1/vapor_liquid_equilibrium/vle.json"
    VLE_DATA = "v1/vapor_liquid_equilibrium/vle_data.json"
    VLE_WRONG_ID = "v1/vapor_liquid_equilibrium/vle_wrong_ids.json"
    WA = "v1/water_analysis/wa.json"
    WA_DATA = "v1/water_analysis/wa_data.json"
    WA_WRONG_ID = "v1/water_analysis/wa_wrong_ids.json"

    # v2
    SAMPLE_ANALYSIS = "v2/samplesanalysis.json"
    SAR_V2 = "v2/sar.json"
    NMR_DATA = "v2/NMR/nmr_data.json"
    NMR_WRONG_ID = "v2/NMR/nmr_wrong_ids.json"
    MULTIPLE_SALINITY_DATA = "v2/multiple_salinity/multiplesalinity_data.json"
    MULTIPLE_SALINITY_WRONG_ID = "v2/multiple_salinity/multiplesalinity_wrong_ids.json"
    AROMATICS_DATA = "v2/aromatics/aromatics_data.json"
    AROMATICS_WRONG_ID = "v2/aromatics/aromatics_wrong_ids.json"
    HPMI_DATA = "v2/HPMI/hpmi_data.json"
    HPMI_WRONG_ID = "v2/HPMI/hpmi_wrong_ids.json"
    ALKANES_DATA = "v2/alkanes/alkanes_data.json"
    ALKANES_WRONG_ID = "v2/alkanes/alkanes_wrong_ids.json"


class DataTemplates:
    ID_DATASET = "opendes:dataset--File.Generic:"
    ID_CORING = f"opendes:master-data--Coring:"
    ID_RS = "opendes:master-data--RockSample:"
    ID_RSA = "opendes:work-product-component--RockSampleAnalysis:"
    ID_SAR = "opendes:work-product-component--SamplesAnalysesReport:"
    ID_PVT = "opendes:work-product-component--PVT:"

    # PVT tests
    ID_CCE = "opendes:work-product-component--ConstantCompositionExpansionTest:"
    ID_DIF_LIB = "opendes:work-product-component--DifferentialLiberationTest:"
    ID_CA = "opendes:work-product-component--CompositionalAnalysisTest:"
    ID_CVD = "opendes:work-product-component--ConstantVolumeDepletionTest:"
    ID_IT = "opendes:work-product-component--InterfacialTensionTest:"
    ID_MSS = "opendes:work-product-component--MultiStageSeparatorTest:"
    ID_MCM = "opendes:work-product-component--MultipleContactMiscibilityTest:"
    ID_SLIM_TUBE = "opendes:work-product-component--SlimTubeTest:"
    ID_STOA = "opendes:work-product-component--StockTankOilAnalysisTest:"
    ID_ST = "opendes:work-product-component--SwellingTest:"
    ID_TT = "opendes:work-product-component--TransportTest:"
    ID_VLE = "opendes:work-product-component--VaporLiquidEquilibriumTest:"
    ID_WA = "opendes:work-product-component--WaterAnalysisTest:"
    ID_SAMPLE_ANALYSIS = "opendes:work-product-component--SamplesAnalysis:"


class DataTypes:
    """Values have to be equal to client/api/__init__.py keys for a specific
    data type client api."""
    # v1
    RSA = "rsa"
    RS = "rs"
    CORING = "coring"
    PVT = "pvt"
    DIF_LIB = "dif_lib"
    CCE = "cce"
    CA = "ca"
    CVD = "cvd"
    IT = "it"
    MSS = "mss"
    MCM = "mcm"
    SLIM_TUBE = "slim_tube"
    STOA = "stoa"
    ST = "st"
    TT = "tt"
    VLE = "vle"
    WA = "wa"
    SAR = "sar"
    CAP_PRESSURE = "cap_pressure"
    EXTRACTION = "extraction"
    FRACTIONATION = "fractionation"
    PHYS_CHEM = "phys_chem"
    RP = "rp"

    # v2
    SAMPLE_ANALYSIS = "sample_analysis"
    SAR_V2 = "sar_v2"


class SamplesAnalysisTypes:  # Custom values
    NMR = "nmr"
    MULTIPLE_SALINITY = "multiplesalinitytests"
    AROMATICS = "gcmsaromatics"
    ALKANES = "gcmsalkanes"


class DatasetPrefix:
    # v1
    RCA = "routine-core-analysis"
    DIF_LIB = "differential-liberation"
    CCE = "constant-composition-expansion"
    CA = "compositionalanalysis"
    CVD = "constantvolumedepletiontest"
    IT = "interfacialtension"
    MSS = "multi-stage-separator"
    MCM = "multiple-contact-miscibility"
    SLIM_TUBE = "slimtube-test"
    STOA = "stoanalysis"
    ST = "swelling"
    TT = "transport-test"
    VLE = "vaporliquidequilibriumtest"
    WA = "wateranalysis"
    SAR = "sar"
    CAP_PRESSURE = "capillary-pressure"
    EXTRACTION = "extraction"
    FRACTIONATION = "fractionation"
    PHYS_CHEM = "physical-chemistry"
    RP = "relative-permeability"

    # v2
    NMR = "nmr"
    MULTIPLE_SALINITY = "multiplesalinitytests"
    AROMATICS = "gcmsaromatics"
    ALKANES = "gcmsalkanes"
