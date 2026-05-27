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
from typing import ClassVar

CONFIG = {}

WPC_VERSION = "1.0.0"
PARQUET_HEADERS = {"Content-Type": "application/x-parquet"}
ACCEPT_HEADERS = "*/*;version={version}"

DATA_DIR = Path("tests", "integration", "data")
TEST_DATA_STORE = {}


class SchemaVersions:
    V1_0_0 = "1.0.0"
    V1_1_0 = "1.1.0"
    V2_0_0 = "2.0.0"
    DEFAULT = V1_0_0


class DataFiles:
    # v2
    OSDU_GENERIC_RECORD = "v2/osdu_generic_record.json"
    SAMPLE = "v2/sample.json"
    SAR = "v2/sample_analyses/sar.json"
    SAMPLE_ANALYSIS = "v2/samples_analysis/samples_analysis.json"
    SAMPLE_ANALYSIS_TYPES = "v2/samples_analysis/samples_analysis_types.json"

    CAPILLARY_PRESSURE_DATA_V1_1 = "v2/samples_analysis/capillary_pressure_data.1.1.0.json"
    CAPILLARY_PRESSURE_SCHEMA_V1_1 = "v2/samples_analysis/capillary_pressure_schema.1.1.0.json"

    CAPILLARY_SUCTION_TIME_DATA_V1 = "v2/samples_analysis/capillary_suction_time_data.1.0.0.json"
    CAPILLARY_SUCTION_TIME_SCHEMA_V1 = "v2/samples_analysis/capillary_suction_time_schema.1.0.0.json"

    COMPOSITIONAL_ANALYSIS_DATA_V1_1 = "v2/samples_analysis/compositional_analysis_data.1.1.0.json"
    COMPOSITIONAL_ANALYSIS_SCHEMA_V1_1 = "v2/samples_analysis/compositional_analysis_schema.1.1.0.json"

    NMR_DATA_V1 = "v2/samples_analysis/nmr_data.1.0.0.json"
    NMR_DATA_V1_RECORDS_FORMAT = "v2/samples_analysis/nmr_data_records_format.1.0.0.json"
    NMR_SCHEMA_V1 = "v2/samples_analysis/nmr_schema.1.0.0.json"

    PROPPANT_EMBEDMENT_DATA_V1 = "v2/samples_analysis/proppant_embedment_data.1.0.0.json"
    PROPPANT_EMBEDMENT_SCHEMA_V1 = "v2/samples_analysis/proppant_embedment_schema.1.0.0.json"

    RELATIVE_PERMEABILITY_DATA_V1 = "v2/samples_analysis/relative_permeability_data.1.0.0.json"
    RELATIVE_PERMEABILITY_SCHEMA_V1 = "v2/samples_analysis/relative_permeability_schema.1.0.0.json"

    ROLLER_OVEN_TEST_DATA_V1 = "v2/samples_analysis/roller_oven_test_data.1.0.0.json"
    ROLLER_OVEN_TEST_SCHEMA_V1 = "v2/samples_analysis/roller_oven_test_schema.1.0.0.json"

    SATURATION_TEST_DATA_V1 = "v2/samples_analysis/saturation_test_data.1.0.0.json"
    SATURATION_TEST_SCHEMA_V1 = "v2/samples_analysis/saturation_test_schema.1.0.0.json"

    SLIM_TUBE_DATA_V1 = "v2/samples_analysis/slimtube_data.1.0.0.json"
    SLIM_TUBE_DATA_V2 = "v2/samples_analysis/slimtube_data.2.0.0.json"
    SLIM_TUBE_SCHEMA_V1 = "v2/samples_analysis/slimtube_schema.1.0.0.json"
    SLIM_TUBE_SCHEMA_V2 = "v2/samples_analysis/slimtube_schema.2.0.0.json"

    STOCK_TANK_OIL_DATA_V1_1 = "v2/samples_analysis/stock_tank_oil_data.1.1.0.json"
    STOCK_TANK_OIL_SCHEMA_V1_1 = "v2/samples_analysis/stock_tank_oil_schema.1.1.0.json"

    VLE_DATA_V2 = "v2/samples_analysis/vle_data.2.0.0.json"
    VLE_SCHEMA_V2 = "v2/samples_analysis/vle_schema.2.0.0.json"

    XRD_DATA_V1_1 = "v2/samples_analysis/xrd_data.1.1.0.json"
    XRD_SCHEMA_V1_1 = "v2/samples_analysis/xrd_schema.1.1.0.json"

    XRF_DATA_V1_1 = "v2/samples_analysis/xrf_data.1.1.0.json"
    XRF_SCHEMA_V1_1 = "v2/samples_analysis/xrf_schema.1.1.0.json"

    SATURATION_FUNCTION_SET = "v2/saturation_function_set/sfs.json"
    SATURATION_FUNCTION_SET_DATA_V1 = "v2/saturation_function_set/sfs_data.json"
    SATURATION_FUNCTION_SET_DATA_V1_RECORDS_FORMAT = "v2/saturation_function_set/sfs_data_records_format.json"
    SATURATION_FUNCTION_SET_SCHEMA = "v2/saturation_function_set/sfs_schema.json"

    SIMULATION_ROCK_PHYSICS = "v2/simulation_rock_physics/rsrp.json"
    SIMULATION_ROCK_PHYSICS_DATA1_V1 = "v2/simulation_rock_physics/rsrp_data_correlation_compressibility.json"
    SIMULATION_ROCK_PHYSICS_DATA2_V1 = "v2/simulation_rock_physics/rsrp_data_volume_multiplier.json"
    SIMULATION_ROCK_PHYSICS_DATA3_V1 = "v2/simulation_rock_physics/rsrp_data_vtp.json"
    SIMULATION_ROCK_PHYSICS_DATA1_V1_RECORDS_FORMAT = "v2/simulation_rock_physics/rsrp_data_records_format.json"
    SIMULATION_ROCK_PHYSICS_SCHEMA = "v2/simulation_rock_physics/rsrp_schema.json"

    FLUID_MODEL = "v2/fluid_model/fluid.json"


class DataTemplates:
    ID_DATASET = "{partition}:dataset--File.Generic:"
    ID_SAR = "{partition}:work-product-component--SamplesAnalysesReport:"
    ID_SAMPLE_ANALYSIS = "{partition}:work-product-component--SamplesAnalysis:"
    ID_SATURATION_FUNCTION_SET = "{partition}:work-product-component--SaturationFunctionSet:"
    ID_SIMULATION_ROCK_PHYSICS = "{partition}:work-product-component--ReservoirSimulationRockPhysicsModel:"
    ID_FLUID_MODEL = "{partition}:work-product-component--FluidModel:"


class DataTypes:
    """Values have to be equal to client/api/__init__.py keys for a specific
    data type client api."""

    # v2
    MASTER_DATA = "masterdata"
    SAMPLE_ANALYSIS = "sample_analysis"
    SAR = "sar"
    SAMPLE = "sample"
    SATURATION_FUNCTION_SET = "saturation_function_set"
    SIMULATION_ROCK_PHYSICS = "simulation_rock_physics"
    FLUID_MODEL = "fluid_model"


class SamplesAnalysisTypes:  # Custom values
    CAPILLARY_PRESSURE = "capillarypressure"
    CAPILLARY_SUCTION_TIME = "capillarysuctiontime"
    CCE = "constantcompositionexpansion"
    COMPOSITIONAL_ANALYSIS = "compositionalanalysis"
    FRACTIONATION = "fractionation"
    NMR = "nmr"
    PROPPANT_EMBEDMENT = "proppantembed"
    RELATIVE_PERMEABILITY = "relativepermeability"
    ROLLER_OVEN_TEST = "rolleroventest"
    SATURATION_TEST = "saturationtest"
    SLIM_TUBE = "slimtube"
    STOCK_TANK_OIL = "stocktankoilanalysis"
    VLE = "vaporliquidequilibrium"
    XRD = "xrd"
    XRF = "xrf"


class VersionedDataFiles:
    VALUES = {
        (SamplesAnalysisTypes.CAPILLARY_PRESSURE, SchemaVersions.V1_1_0): DataFiles.CAPILLARY_PRESSURE_DATA_V1_1,
        (SamplesAnalysisTypes.CAPILLARY_SUCTION_TIME, SchemaVersions.V1_0_0): DataFiles.CAPILLARY_SUCTION_TIME_DATA_V1,
        (
            SamplesAnalysisTypes.COMPOSITIONAL_ANALYSIS,
            SchemaVersions.V1_1_0,
        ): DataFiles.COMPOSITIONAL_ANALYSIS_DATA_V1_1,
        (SamplesAnalysisTypes.NMR, SchemaVersions.V1_0_0): DataFiles.NMR_DATA_V1,
        (SamplesAnalysisTypes.PROPPANT_EMBEDMENT, SchemaVersions.V1_0_0): DataFiles.PROPPANT_EMBEDMENT_DATA_V1,
        (SamplesAnalysisTypes.RELATIVE_PERMEABILITY, SchemaVersions.V1_0_0): DataFiles.RELATIVE_PERMEABILITY_DATA_V1,
        (SamplesAnalysisTypes.ROLLER_OVEN_TEST, SchemaVersions.V1_0_0): DataFiles.ROLLER_OVEN_TEST_DATA_V1,
        (SamplesAnalysisTypes.SATURATION_TEST, SchemaVersions.V1_0_0): DataFiles.SATURATION_TEST_DATA_V1,
        (SamplesAnalysisTypes.SLIM_TUBE, SchemaVersions.V1_0_0): DataFiles.SLIM_TUBE_DATA_V1,
        (SamplesAnalysisTypes.SLIM_TUBE, SchemaVersions.V2_0_0): DataFiles.SLIM_TUBE_DATA_V2,
        (SamplesAnalysisTypes.STOCK_TANK_OIL, SchemaVersions.V1_1_0): DataFiles.STOCK_TANK_OIL_DATA_V1_1,
        (SamplesAnalysisTypes.VLE, SchemaVersions.V2_0_0): DataFiles.VLE_DATA_V2,
        (SamplesAnalysisTypes.XRD, SchemaVersions.V1_1_0): DataFiles.XRD_DATA_V1_1,
        (SamplesAnalysisTypes.XRF, SchemaVersions.V1_1_0): DataFiles.XRF_DATA_V1_1,
        (DataTypes.SATURATION_FUNCTION_SET, SchemaVersions.V1_0_0): DataFiles.SATURATION_FUNCTION_SET_DATA_V1,

        (DataTypes.SIMULATION_ROCK_PHYSICS, SchemaVersions.V1_0_0): DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1,
    }


class SamplesAnalysisConfig:
    _VALUES = {
        SamplesAnalysisTypes.CAPILLARY_SUCTION_TIME: {
            "samples_analysis_type": "FluidSensitivity.CapillarySuctionTime",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.CAPILLARY_PRESSURE: {
            "samples_analysis_type": "CapillaryPressure",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.CCE: {
            "samples_analysis_type": "PVT.ConstantCompositionExpansion",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.COMPOSITIONAL_ANALYSIS: {
            "samples_analysis_type": "PVT.CompositionalAnalysis",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.FRACTIONATION: {
            "samples_analysis_type": "Fractionation.SARA",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.NMR: {
            "samples_analysis_type": "NMR",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.PROPPANT_EMBEDMENT: {
            "samples_analysis_type": "Geomechanics.ProppantEmbedment",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.RELATIVE_PERMEABILITY: {
            "samples_analysis_type": "RelativePermeability.SteadyState",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.ROLLER_OVEN_TEST: {
            "samples_analysis_type": "FluidSensitivity.RollerOvenTest",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.SATURATION_TEST: {
            "samples_analysis_type": "PVT.SaturationTest",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.SLIM_TUBE: {
            "samples_analysis_type": "PVT.SlimTube",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.STOCK_TANK_OIL: {
            "samples_analysis_type": "PVT.StockTankOilCharacterization",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.VLE: {
            "samples_analysis_type": "PVT.VaporLiquidEquilibria",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.XRD: {
            "samples_analysis_type": "Mineralogy.XRD",
            "parent_report_id": "sar_record_id",
        },
        SamplesAnalysisTypes.XRF: {
            "samples_analysis_type": "ElementalComposition.XRF",
            "parent_report_id": "sar_record_id",
        },
    }

    @classmethod
    def get(cls, analysis_type):
        entry = cls._VALUES[analysis_type]
        parent_id = TEST_DATA_STORE.get(entry["parent_report_id"], "")
        if not parent_id:
            raise RuntimeError(f"Missing parent report ID for {analysis_type}")
        return {
            "samples_analysis_type": entry["samples_analysis_type"],
            "parent_report_id": parent_id,
        }


class BaseEndpoints:

    ALL_ENDPOINTS_ARGS: ClassVar[list] = []
    RECORD_ID_ENDPOINTS_ARGS: ClassVar[list]
    ENDPOINTS_WITH_FILTERS_ARGS: ClassVar[list]
    ORIENT_ENDPOINTS_ARGS: ClassVar[list]
    SEARCH_ENDPOINTS_ARGS: ClassVar[list]
    CONTENT_TYPE_ENDPOINTS_ARGS: ClassVar[list]
    ACCEPT_ENDPOINTS_ARGS: ClassVar[list]
    RETURN_DATA_ENDPOINTS_ARGS: ClassVar[list]
    SCHEMA_VERSION_ENDPOINTS_ARGS: ClassVar[list]

    RECORD_ID_ENDPOINTS = (
        "get_record",
        "get_record_versions",
        "get_record_version",
        "soft_delete_record",
        "post_data",
        "get_data",
    )

    ENDPOINTS_WITH_FILTERS = (
        "get_data",
        "search_records",
        "search_data",
    )

    ORIENT_ENDPOINTS = (
        "get_data",
        "search_data",
    )

    SEARCH_ENDPOINTS = (
        "search_records",
        "search_data",
    )

    CONTENT_TYPE_ENDPOINTS = (
        "post_record",
        "post_data",
    )

    ACCEPT_ENDPOINTS = (
        "get_schema",
        "get_data",
        "search_records",
        "search_data",
    )

    RETURN_DATA_ENDPOINTS = (
        "get_data",
        "search_data",
    )

    SCHEMA_VERSION_ENDPOINTS = (
        "get_schema",
        "post_data",
        "get_data",
        "search_records",
        "search_data",
    )

    _CATEGORIES = (
        "RECORD_ID_ENDPOINTS",
        "ENDPOINTS_WITH_FILTERS",
        "ORIENT_ENDPOINTS",
        "SEARCH_ENDPOINTS",
        "CONTENT_TYPE_ENDPOINTS",
        "ACCEPT_ENDPOINTS",
        "RETURN_DATA_ENDPOINTS",
        "SCHEMA_VERSION_ENDPOINTS",
    )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        args_by_name = dict(cls.ALL_ENDPOINTS_ARGS)
        for category in cls._CATEGORIES:
            names = getattr(cls, category)
            setattr(cls, f"{category}_ARGS", [(name, args_by_name[name]) for name in names])


class Endpoints(BaseEndpoints):
    ALL_ENDPOINTS_ARGS = [
        ("post_record", ()),
        ("get_record", ("record_id",)),
        ("get_record_versions", ("record_id",)),
        ("get_record_version", ("record_id", "version")),
        ("post_data", ("record_id",)),
        ("get_data", ("record_id", "dataset_id")),
        ("get_schema", ()),
        ("search_records", ()),
        ("search_data", ()),
        ("soft_delete_record", ("record_id",)),
    ]


class SamplesAnalysisEndpoints(BaseEndpoints):
    ALL_ENDPOINTS_ARGS = [
        ("get_analysis_types", ()),
        ("post_record", ()),
        ("get_record", ("record_id",)),
        ("get_record_versions", ("record_id",)),
        ("get_record_version", ("record_id", "version")),
        ("post_data", ("record_id", "analysis_type")),
        ("get_data", ("record_id", "dataset_id", "analysis_type")),
        ("get_schema", ("analysis_type",)),
        ("search_records", ("analysis_type",)),
        ("search_data", ("analysis_type",)),
        ("soft_delete_record", ("record_id",)),
    ]
