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

from tests.test_api.test_routes.osdu.storage_mock_objects import (
    OSDU_GENERIC_RECORD,
    TEST_SAMPLESANALYSIS_ID,
)

dir_path = os.path.dirname(os.path.abspath(__file__))

TEST_DATASET_RECORD_ID = "opendes:dataset--File.Generic:capillarypressuredata-12345:1234"
TEST_DDMS_URN = f"urn://rafs-v2/capillarypressuredata/{TEST_SAMPLESANALYSIS_ID}/{TEST_DATASET_RECORD_ID}"
TEST_SCHEMA_VERSION = "1.0.0"
TEST_DDMS_URN_WITH_VERSION = f"urn://rafs-v2/capillarypressuredata/{TEST_SAMPLESANALYSIS_ID}/{TEST_DATASET_RECORD_ID}/{TEST_SCHEMA_VERSION}"
RECORD_DATA = {
    **OSDU_GENERIC_RECORD.dict(exclude_none=True), **{
        "data": {
            "DDMSDatasets": [TEST_DDMS_URN],
        },
    },
}
RECORD_DATA_WITH_SCHEMA_VERSION = {
    **OSDU_GENERIC_RECORD.dict(exclude_none=True), **{
        "data": {
            "DDMSDatasets": [TEST_DDMS_URN_WITH_VERSION],
        },
    },
}
RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION = {
    **OSDU_GENERIC_RECORD.dict(exclude_none=True), **{
        "data": {
            "DDMSDatasets": [f"{TEST_DDMS_URN}/2.0.0"],
        },
    },
}
TEST_PARAMS_AGGREGATION = {
    "columns_aggregation": "SampleID,count",
}
TEST_PARAMS_FILTERS = {
    "columns_filter": "SamplesAnalysisID,SampleID,TestData",
    "rows_filter": "SamplesAnalysisID,eq,opendes:work-product-component--SamplesAnalysis:CapillaryPressure_WPC:",
}

with open(f"{dir_path}/cappressure_orient_split.json") as fp:
    TEST_DATA = json.load(fp)

TEST_AGGREGATED_DATA = {
    "columns": [
        "SampleID",
    ],
    "index": [
        "count",
    ],
    "data": [
        [
            1,
        ],
    ],
}

TEST_FILTERED_DATA = {
    "columns": [
        "SamplesAnalysisID",
        "SampleID",
        "TestData",
    ],
    "index": [
        0,
    ],
    "data": [
        [
            "opendes:work-product-component--SamplesAnalysis:CapillaryPressure_WPC:",
            "opendes:master-data--Sample:CapillaryPressure_Sample:",
            [
                {
                    "Permeability": [
                        {
                            "Value": 52.2,
                            "Type": "opendes:reference-data--PermeabilityMeasurementType:Klinkenberg:",
                            "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:H%2Fm:",
                        },
                    ],
                    "Porosity": {
                        "Value": 40,
                        "Type": "opendes:reference-data--PorosityMeasurementType:BrineSaturation:",
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:%25%5Bvol%5D:",
                    },
                    "SaturationProcessMethod": {
                        "Value": "opendes:reference-data--SaturationProcessMethod:DrainageTwoPhase:",
                    },
                    "InitialWaterSaturation": {
                        "Value": 25,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:%25:",
                    },
                    "InitialOilSaturation": {
                        "Value": 34,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:%25:",
                    },
                    "InitialGasSaturation": {
                        "Value": 54,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:%25:",
                    },
                    "Pressure": [
                        {
                            "Value": 13,
                            "Type": "opendes:reference-data--PressureMeasurementType:Overburden:",
                            "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                        },
                    ],
                    "EntryPressure": [
                        {
                            "Value": 21,
                            "Type": "opendes:reference-data--FluidSystemType:AirMercury:",
                            "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                        },
                    ],
                    "NetConfiningStress": {
                        "Value": 321,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                    },
                    "Temperature": {
                        "Value": 75,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:degF:",
                    },
                    "WaterViscosity": {
                        "Value": 5,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:m2%2Fs:",
                    },
                    "WaterDensity": {
                        "Value": 6.4,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:g%2Fcm3:",
                    },
                    "OilViscosity": {
                        "Value": 3.7,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:m2%2Fs:",
                    },
                    "OilDensity": {
                        "Value": 4.7,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:g%2Fcm3:",
                    },
                    "GasViscosity": {
                        "Value": 12,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:m2%2Fs:",
                    },
                    "GasDensity": {
                        "Value": 7.4,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:g%2Fcm3:",
                    },
                    "InterfacialTension": {
                        "Value": 3.5,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:mN%2Fm:",
                    },
                    "BrineSalinity": {
                        "Value": 65,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:g%2FL:",
                    },
                    "Endpoints": {
                        "CapillaryPressureMax": {
                            "Value": 328,
                            "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                        },
                        "WettingPhaseSaturationAtCapillaryPressureMax": {
                            "Value": 236,
                            "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                        },
                        "NonwettingPhaseSaturationAtCapillaryPressureMax": {
                            "Value": 321,
                            "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                        },
                        "LowestWettingPhaseSaturationAVG": {
                            "Value": 43,
                            "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:%25:",
                        },
                        "LowestNonwettingPhaseSaturationAVG": {
                            "Value": 26,
                            "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:%25:",
                        },
                    },
                    "CapillaryPressureSteps": [
                        {
                            "StepNumber": "1",
                            "CapillaryPressure": {
                                "Value": 76,
                                "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                            },
                            "PhaseSaturation": [
                                {
                                    "Value": 55,
                                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:%25:",
                                    "DisplacingFluid": "opendes:reference-data--DisplacingFluidType:LiveBrine:",
                                    "DisplacedFluid": "opendes:reference-data--DisplacedFluidType:Soltrol:",
                                    "WettabilityPhaseType": "opendes:reference-data--WettabilityPhaseType:WettingAqueous:",
                                },
                            ],
                            "PhaseInjectedVolume": [
                                {
                                    "Value": 34,
                                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:cm3:",
                                    "DisplacingFluid": "opendes:reference-data--DisplacingFluidType:Tetradecane:",
                                    "DisplacedFluid": "opendes:reference-data--DisplacedFluidType:Decane:",
                                    "WettabilityPhaseType": "opendes:reference-data--WettabilityPhaseType:Wetting:",
                                },
                            ],
                            "Remark": "Success",
                            "CalculatedProperties": {
                                "PoreThroatRadius": {
                                    "Value": 34,
                                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:mm:",
                                },
                                "PoreThroatMedianRadius": {
                                    "Value": 12,
                                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:mm:",
                                },
                                "EndFaceEstimationMethod": "opendes:reference-data--EndFaceEstimationMethod:Forbes:",
                                "EndFacePhaseSaturation": {
                                    "Value": 12,
                                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:%25:",
                                },
                                "JFunction": {
                                    "Value": 3,
                                },
                                "GasWaterCapillaryPressure": {
                                    "Value": 31,
                                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                                },
                                "GasOilCapillaryPressure": {
                                    "Value": 44,
                                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                                },
                                "OilWaterCapillaryPressure": {
                                    "Value": 22,
                                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                                },
                                "AirMercuryCapillaryPressure": {
                                    "Value": 12,
                                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                                },
                                "GasWaterAboveFWL": {
                                    "Value": 33,
                                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:cm:",
                                },
                                "OilWaterAboveFWL": {
                                    "Value": 31,
                                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:cm:",
                                },
                            },
                            "PoreThroatSizeDistribution": [
                                {
                                    "PoreThroatSize": {
                                        "Value": 36,
                                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:um:",
                                    },
                                    "CumulativePhaseSaturation": {
                                        "Value": 34,
                                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:%25:",
                                        "DisplacingFluid": "opendes:reference-data--DisplacingFluidType:Mercury:",
                                        "DisplacedFluid": "opendes:reference-data--DisplacedFluidType:LiveCrudeOil:",
                                        "WettabilityPhaseType": "opendes:reference-data--WettabilityPhaseType:Nonwetting:",
                                    },
                                    "PhaseSaturationFrequency": {
                                        "Value": 32,
                                        "DisplacingFluid": "opendes:reference-data--DisplacingFluidType:Helium:",
                                        "DisplacedFluid": "opendes:reference-data--DisplacedFluidType:IsoparBlend:",
                                        "WettabilityPhaseType": "opendes:reference-data--WettabilityPhaseType:Wetting:",
                                    },
                                },
                            ],
                        },
                    ],
                },
            ],
        ],
    ],
}

INCORRECT_SCHEMA_TEST_DATA = {
    "columns": [
        "WrongField",  # Wrong field
        "data",
        # "MultiStageSeparatorTestSteps",  # Missing mandatory field
    ],
    "index": [0],
    "data": [
        [
            "opendes:work-product-component--SamplesAnalysis:cappressure-test:",
            "opendes:master-data--:1:",  # Incorrect master-data value
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA = copy.deepcopy(TEST_DATA)
INCORRECT_DATAFRAME_TEST_DATA["data"][0].pop()  # deleting TestData in index row 0
EXPECTED_ERROR_REASON = "Data error: 3 columns passed, passed data had 2 columns"
