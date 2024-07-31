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

import json
from contextlib import contextmanager
from unittest.mock import create_autospec, patch

import pandas as pd
import pyarrow as pa
import pytest
from httpx import AsyncClient
from pyarrow import parquet as pq
from starlette import status

from app.api.dependencies.services import (
    get_async_dataset_service,
    get_async_storage_service,
)
from app.api.routes.utils.query import find_osdu_ids_from_string
from app.main import app
from app.services import dataset, storage
from tests.test_api.test_routes import dependencies
from tests.test_api.test_routes.api_v2.cappressure import (
    cappressure_mock_objects,
)
from tests.test_api.test_routes.api_v2.cce import cce_mock_objects
from tests.test_api.test_routes.api_v2.compositionalanalysis import (
    compositional_analysis_mock_objects,
)
from tests.test_api.test_routes.api_v2.constantvolumedepletion import (
    cvd_mock_objects,
)
from tests.test_api.test_routes.api_v2.crushed_rock_analysis import (
    crushed_rock_analysis_mock_objects,
)
from tests.test_api.test_routes.api_v2.differentialliberation import (
    diff_lib_mock_objects,
)
from tests.test_api.test_routes.api_v2.eds_mapping_data import (
    eds_mapping_mock_objects,
)
from tests.test_api.test_routes.api_v2.electricalproperties import (
    electricalproperties_mock_objects,
)
from tests.test_api.test_routes.api_v2.extraction import (
    extraction_mock_objects,
)
from tests.test_api.test_routes.api_v2.fractionation import (
    fractionation_mock_objects,
)
from tests.test_api.test_routes.api_v2.interfacialtension import (
    interfacial_tension_mock_objects,
)
from tests.test_api.test_routes.api_v2.mininggeotechlogging import (
    mining_geotech_logging_mock_objects,
)
from tests.test_api.test_routes.api_v2.multiplecontactmiscibility import (
    mcm_mock_objects,
)
from tests.test_api.test_routes.api_v2.multistageseparator import (
    mss_mock_objects,
)
from tests.test_api.test_routes.api_v2.nmr import nmr_mock_objects
from tests.test_api.test_routes.api_v2.pdp import pdp_mock_objects
from tests.test_api.test_routes.api_v2.pvtmodel import (
    black_oil_table_mock_objects,
    component_scenario_mock_objects,
    eos_content_mock_objects,
    mpfm_calibration_mock_objects,
)
from tests.test_api.test_routes.api_v2.relative_permeability import (
    relative_permeability_mock_objects,
)
from tests.test_api.test_routes.api_v2.rock_compressibility import (
    rock_compressibility_mock_objects,
)
from tests.test_api.test_routes.api_v2.routinecoreanalysis import (
    rca_mock_objects,
)
from tests.test_api.test_routes.api_v2.slimtube import slimtube_mock_objects
from tests.test_api.test_routes.api_v2.sto import sto_mock_objects
from tests.test_api.test_routes.api_v2.swelling import swelling_mock_objects
from tests.test_api.test_routes.api_v2.tec import tec_data_mock_objects
from tests.test_api.test_routes.api_v2.tensile_strength import (
    tensile_strength_mock_objects,
)
from tests.test_api.test_routes.api_v2.transport import (
    transport_test_mock_objects,
)
from tests.test_api.test_routes.api_v2.vaporliquidequilibrium import (
    vle_mock_objects,
)
from tests.test_api.test_routes.api_v2.vitrinitereflectance import (
    vitrinite_reflectance_mock_objects,
)
from tests.test_api.test_routes.api_v2.water_analysis import (
    water_analysis_data_mock_objects,
)
from tests.test_api.test_routes.api_v2.wettability_index import (
    wettability_index_mock_objects,
)
from tests.test_api.test_routes.api_v2.xrd import xrd_mock_objects
from tests.test_api.test_routes.api_v2.xrf import xrf_mock_objects
from tests.test_api.test_routes.bulk_pyrolysis import (
    bulk_pyrolysis_mock_objects,
)
from tests.test_api.test_routes.cec_content import cec_content_mock_objects
from tests.test_api.test_routes.core_gamma import core_gamma_mock_objects
from tests.test_api.test_routes.data import data_mock_objects
from tests.test_api.test_routes.data.data_mock_objects import (
    INVALID_DATA_WITH_NAN,
    ORIENT_SPLIT_400_PAYLOADS,
    TEST_HEADERS_IMPROPER_SCHEMA_VERSION,
    TEST_HEADERS_JSON,
    TEST_HEADERS_NO_AUTH,
    TEST_HEADERS_PARQUET,
    TEST_HEADERS_WITHOUT_SCHEMA_VERSION,
    TEST_SERVER,
    build_get_test_data,
    build_mock_get_dataset_service,
    build_mock_get_storage_service,
)
from tests.test_api.test_routes.gas_chromatography import (
    gas_chromatography_mock_objects,
)
from tests.test_api.test_routes.gas_composition import (
    gas_composition_mock_objects,
)
from tests.test_api.test_routes.gcms_alkanes import gcms_alkanes_mock_objects
from tests.test_api.test_routes.gcms_aromatics import (
    gcms_aromatics_mock_objects,
)
from tests.test_api.test_routes.gcms_ratios import gcms_ratios_mock_objects
from tests.test_api.test_routes.gcmsms_analysis import (
    gcmsms_analysis_mock_objects,
)
from tests.test_api.test_routes.isotope_analysis import (
    isotope_analysis_mock_objects,
)
from tests.test_api.test_routes.multiple_salinity import (
    multiple_salinity_mock_objects,
)
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    BulkDatasetIdPVTModel,
    BulkDatasetIdV2,
    TestContentPathsApiV2,
    TestContentPathsPVTModel,
)
from tests.test_api.test_routes.triaxial_test import triaxial_test_mock_objects
from tests.test_api.test_routes.uniaxial_test import uniaxial_test_mock_objects

async_storage_record_service_mock = create_autospec(storage.StorageService, spec_set=True, instance=True)
async_dataset_service_mock = create_autospec(dataset.DatasetService, spec_set=True, instance=True)


async def mock_get_async_dataset_service():
    yield async_dataset_service_mock


async def mock_get_storage_service():
    yield async_storage_record_service_mock


async def mock_get_async_storage_service():
    yield async_storage_record_service_mock


@contextmanager
def services_overrides():
    overrides = {
        get_async_storage_service: mock_get_async_storage_service,
        get_async_dataset_service: mock_get_async_dataset_service,
    }
    with dependencies.DependencyOverrider(app, overrides) as mock_dependencies:
        yield mock_dependencies


@pytest.fixture
def with_patched_storage_failed_integrity_validation(missed_records):
    """Patch storage query_records failure."""
    query_response = {
        "invalidRecords": missed_records,
    }
    with patch.object(async_storage_record_service_mock, "query_records", return_value=query_response):
        yield


@pytest.fixture
def with_patched_services_success(storage_method, osdu_records, dataset_method, blobs):
    """Patch storage and datasets to 200 success."""
    with patch.object(async_storage_record_service_mock, storage_method, side_effect=osdu_records):
        with patch.object(async_dataset_service_mock, dataset_method, side_effect=blobs):
            yield


@contextmanager
def post_overrides(record_data=None, test_dataset_record_id=data_mock_objects.TEST_DATASET_RECORD_ID, data_payload=None):
    mock_get_storage_service = build_mock_get_storage_service(record_data, data_payload)
    mock_get_dataset_service = build_mock_get_dataset_service(test_dataset_record_id=test_dataset_record_id)
    overrides = {
        get_async_storage_service: mock_get_storage_service,
        get_async_dataset_service: mock_get_dataset_service,
    }
    with dependencies.DependencyOverrider(app, overrides) as mock_dependencies:
        yield mock_dependencies


@pytest.mark.parametrize(
    "data_endpoint_path,dataset_id", [
        (TestContentPathsApiV2.RCA, BulkDatasetIdV2.RCA),
        (TestContentPathsApiV2.CCE, BulkDatasetIdV2.CCE),
        (TestContentPathsApiV2.DIFF_LIB, BulkDatasetIdV2.DIFF_LIB),
        (TestContentPathsApiV2.TRANSPORT_TEST, BulkDatasetIdV2.TRANSPORT_TEST),
        (TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS, BulkDatasetIdV2.COMPOSITIONAL_ANALYSIS),
        (TestContentPathsApiV2.MSS, BulkDatasetIdV2.MSS),
        (TestContentPathsApiV2.SWELLING, BulkDatasetIdV2.SWELLING),
        (TestContentPathsApiV2.CVD, BulkDatasetIdV2.CVD),
        (TestContentPathsApiV2.WATER_ANALYSIS, BulkDatasetIdV2.WATER_ANALYSIS),
        (TestContentPathsApiV2.INTERFACIAL_TENSION, BulkDatasetIdV2.INTERFACIAL_TENSION),
        (TestContentPathsApiV2.VLE, BulkDatasetIdV2.VLE),
        (TestContentPathsApiV2.MCM, BulkDatasetIdV2.MCM),
        (TestContentPathsApiV2.SLIMTUBE, BulkDatasetIdV2.SLIMTUBE),
        (TestContentPathsApiV2.EXTRACTION, BulkDatasetIdV2.EXTRACTION),
        (TestContentPathsApiV2.FRACTIONATION, BulkDatasetIdV2.FRACTIONATION),
        (TestContentPathsApiV2.RELATIVE_PERMEABILITY, BulkDatasetIdV2.RELATIVE_PERMEABILITY),
        (TestContentPathsApiV2.ROCK_COMPRESSIBILITY, BulkDatasetIdV2.ROCK_COMPRESSIBILITY),
        (TestContentPathsApiV2.NMR, BulkDatasetIdV2.NMR),
        (TestContentPathsApiV2.MULTIPLE_SALINITY, BulkDatasetIdV2.MULTIPLE_SALINITY),
        (TestContentPathsApiV2.GCMS_ALKANES, BulkDatasetIdV2.GCMS_ALKANES),
        (TestContentPathsApiV2.GCMS_AROMATICS, BulkDatasetIdV2.GCMS_AROMATICS),
        (TestContentPathsApiV2.GCMS_RATIOS, BulkDatasetIdV2.GCMS_RATIOS),
        (TestContentPathsApiV2.GAS_CHROMATOGRAPHY, BulkDatasetIdV2.GAS_CHROMATOGRAPHY),
        (TestContentPathsApiV2.GAS_COMPOSITION, BulkDatasetIdV2.GAS_COMPOSITION),
        (TestContentPathsApiV2.ISOTOPE_ANALYSIS, BulkDatasetIdV2.ISOTOPE_ANALYSIS),
        (TestContentPathsApiV2.BULK_PYROLYSIS, BulkDatasetIdV2.BULK_PYROLYSIS),
        (TestContentPathsApiV2.CORE_GAMMA, BulkDatasetIdV2.CORE_GAMMA),
        (TestContentPathsApiV2.MINING_GEOTECH_LOGGING, BulkDatasetIdV2.MINING_GEOTECH_LOGGING),
        (TestContentPathsApiV2.UNIAXIAL_TEST, BulkDatasetIdV2.UNIAXIAL_TEST),
        (TestContentPathsApiV2.GCMSMS_ANALYSIS, BulkDatasetIdV2.GCMSMS_ANALYSIS),
        (TestContentPathsApiV2.CEC_CONTENT, BulkDatasetIdV2.CEC_CONTENT),
        (TestContentPathsApiV2.ELECTRICAL_PROPERTIES, BulkDatasetIdV2.ELECTRICAL_PROPERTIES),
        (TestContentPathsApiV2.TRIAXIAL_TEST, BulkDatasetIdV2.TRIAXIAL_TEST),
        (TestContentPathsApiV2.CAP_PRESSURE, BulkDatasetIdV2.CAP_PRESSURE),
        (TestContentPathsApiV2.WETTABILITY_INDEX, BulkDatasetIdV2.WETTABILITY_INDEX),
        (TestContentPathsApiV2.TEC, BulkDatasetIdV2.TEC),
        (TestContentPathsApiV2.EDS_MAPPING, BulkDatasetIdV2.EDS_MAPPING),
        (TestContentPathsApiV2.XRF, BulkDatasetIdV2.XRF),
        (TestContentPathsApiV2.TENSILE_STRENGTH, BulkDatasetIdV2.TENSILE_STRENGTH),
        (TestContentPathsApiV2.VITRINITE_REFLECTANCE, BulkDatasetIdV2.VITRINITE_REFLECTANCE),
        (TestContentPathsApiV2.XRD, BulkDatasetIdV2.XRD),
        (TestContentPathsApiV2.PDP, BulkDatasetIdV2.PDP),
        (TestContentPathsApiV2.STO, BulkDatasetIdV2.STO),
        (TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS, BulkDatasetIdV2.CRUSHED_ROCK_ANALYSIS),
        (TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS, BulkDatasetIdV2.CRUSHED_ROCK_ANALYSIS),
        (TestContentPathsPVTModel.MPFM_CALIBRATION, BulkDatasetIdPVTModel.MPFM_CALIBRATION),
        (TestContentPathsPVTModel.EOS, BulkDatasetIdPVTModel.EOS),
        (TestContentPathsPVTModel.COMPONENT_SCENARIO, BulkDatasetIdPVTModel.COMPONENT_SCENARIO),
        (TestContentPathsPVTModel.BLACK_OIL_TABLE, BulkDatasetIdPVTModel.BLACK_OIL_TABLE),
    ],
)
@pytest.mark.asyncio
async def test_get_content_data_no_data(data_endpoint_path, dataset_id):
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{data_endpoint_path}/{dataset_id}",
                headers=TEST_HEADERS_PARQUET,
            )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    expected = {"message": f"{dataset_id} does not exist in current record.", "reason": "Not found."}
    assert response.json() == expected


@pytest.mark.parametrize(
    "data_endpoint_path,dataset_id", [
        (TestContentPathsApiV2.RCA, BulkDatasetIdV2.RCA),
        (TestContentPathsApiV2.CCE, BulkDatasetIdV2.CCE),
        (TestContentPathsApiV2.DIFF_LIB, BulkDatasetIdV2.DIFF_LIB),
        (TestContentPathsApiV2.TRANSPORT_TEST, BulkDatasetIdV2.TRANSPORT_TEST),
        (TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS, BulkDatasetIdV2.COMPOSITIONAL_ANALYSIS),
        (TestContentPathsApiV2.MSS, BulkDatasetIdV2.MSS),
        (TestContentPathsApiV2.SWELLING, BulkDatasetIdV2.SWELLING),
        (TestContentPathsApiV2.CVD, BulkDatasetIdV2.CVD),
        (TestContentPathsApiV2.WATER_ANALYSIS, BulkDatasetIdV2.WATER_ANALYSIS),
        (TestContentPathsApiV2.INTERFACIAL_TENSION, BulkDatasetIdV2.INTERFACIAL_TENSION),
        (TestContentPathsApiV2.VLE, BulkDatasetIdV2.VLE),
        (TestContentPathsApiV2.MCM, BulkDatasetIdV2.MCM),
        (TestContentPathsApiV2.SLIMTUBE, BulkDatasetIdV2.SLIMTUBE),
        (TestContentPathsApiV2.EXTRACTION, BulkDatasetIdV2.EXTRACTION),
        (TestContentPathsApiV2.FRACTIONATION, BulkDatasetIdV2.FRACTIONATION),
        (TestContentPathsApiV2.RELATIVE_PERMEABILITY, BulkDatasetIdV2.RELATIVE_PERMEABILITY),
        (TestContentPathsApiV2.ROCK_COMPRESSIBILITY, BulkDatasetIdV2.ROCK_COMPRESSIBILITY),
        (TestContentPathsApiV2.NMR, BulkDatasetIdV2.NMR),
        (TestContentPathsApiV2.MULTIPLE_SALINITY, BulkDatasetIdV2.MULTIPLE_SALINITY),
        (TestContentPathsApiV2.GCMS_ALKANES, BulkDatasetIdV2.GCMS_ALKANES),
        (TestContentPathsApiV2.GCMS_AROMATICS, BulkDatasetIdV2.GCMS_AROMATICS),
        (TestContentPathsApiV2.GCMS_RATIOS, BulkDatasetIdV2.GCMS_RATIOS),
        (TestContentPathsApiV2.GAS_CHROMATOGRAPHY, BulkDatasetIdV2.GAS_CHROMATOGRAPHY),
        (TestContentPathsApiV2.GAS_COMPOSITION, BulkDatasetIdV2.GAS_COMPOSITION),
        (TestContentPathsApiV2.ISOTOPE_ANALYSIS, BulkDatasetIdV2.ISOTOPE_ANALYSIS),
        (TestContentPathsApiV2.BULK_PYROLYSIS, BulkDatasetIdV2.BULK_PYROLYSIS),
        (TestContentPathsApiV2.CORE_GAMMA, BulkDatasetIdV2.CORE_GAMMA),
        (TestContentPathsApiV2.MINING_GEOTECH_LOGGING, BulkDatasetIdV2.MINING_GEOTECH_LOGGING),
        (TestContentPathsApiV2.UNIAXIAL_TEST, BulkDatasetIdV2.UNIAXIAL_TEST),
        (TestContentPathsApiV2.GCMSMS_ANALYSIS, BulkDatasetIdV2.GCMSMS_ANALYSIS),
        (TestContentPathsApiV2.CEC_CONTENT, BulkDatasetIdV2.CEC_CONTENT),
        (TestContentPathsApiV2.ELECTRICAL_PROPERTIES, BulkDatasetIdV2.ELECTRICAL_PROPERTIES),
        (TestContentPathsApiV2.TRIAXIAL_TEST, BulkDatasetIdV2.TRIAXIAL_TEST),
        (TestContentPathsApiV2.CAP_PRESSURE, BulkDatasetIdV2.CAP_PRESSURE),
        (TestContentPathsApiV2.WETTABILITY_INDEX, BulkDatasetIdV2.WETTABILITY_INDEX),
        (TestContentPathsApiV2.TEC, BulkDatasetIdV2.TEC),
        (TestContentPathsApiV2.EDS_MAPPING, BulkDatasetIdV2.EDS_MAPPING),
        (TestContentPathsApiV2.XRF, BulkDatasetIdV2.XRF),
        (TestContentPathsApiV2.TENSILE_STRENGTH, BulkDatasetIdV2.TENSILE_STRENGTH),
        (TestContentPathsApiV2.VITRINITE_REFLECTANCE, BulkDatasetIdV2.VITRINITE_REFLECTANCE),
        (TestContentPathsApiV2.XRD, BulkDatasetIdV2.XRD),
        (TestContentPathsApiV2.PDP, BulkDatasetIdV2.PDP),
        (TestContentPathsApiV2.STO, BulkDatasetIdV2.STO),
        (TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS, BulkDatasetIdV2.CRUSHED_ROCK_ANALYSIS),
        (TestContentPathsPVTModel.MPFM_CALIBRATION, BulkDatasetIdPVTModel.MPFM_CALIBRATION),
        (TestContentPathsPVTModel.EOS, BulkDatasetIdPVTModel.EOS),
        (TestContentPathsPVTModel.COMPONENT_SCENARIO, BulkDatasetIdPVTModel.COMPONENT_SCENARIO),
        (TestContentPathsPVTModel.BLACK_OIL_TABLE, BulkDatasetIdPVTModel.BLACK_OIL_TABLE),
    ],
)
@pytest.mark.asyncio
async def test_get_data_no_content_header(data_endpoint_path, dataset_id):
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{data_endpoint_path}/{dataset_id}",
                headers=None,
            )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    expected = {"code": status.HTTP_400_BAD_REQUEST, "reason": "Content-Type header is required, but was not provided"}
    assert response.json() == expected


@pytest.mark.parametrize(
    "data_endpoint_path,dataset_id", [
        (TestContentPathsApiV2.RCA, BulkDatasetIdV2.RCA),
        (TestContentPathsApiV2.CCE, BulkDatasetIdV2.CCE),
        (TestContentPathsApiV2.DIFF_LIB, BulkDatasetIdV2.DIFF_LIB),
        (TestContentPathsApiV2.TRANSPORT_TEST, BulkDatasetIdV2.TRANSPORT_TEST),
        (TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS, BulkDatasetIdV2.COMPOSITIONAL_ANALYSIS),
        (TestContentPathsApiV2.MSS, BulkDatasetIdV2.MSS),
        (TestContentPathsApiV2.SWELLING, BulkDatasetIdV2.SWELLING),
        (TestContentPathsApiV2.CVD, BulkDatasetIdV2.CVD),
        (TestContentPathsApiV2.WATER_ANALYSIS, BulkDatasetIdV2.WATER_ANALYSIS),
        (TestContentPathsApiV2.INTERFACIAL_TENSION, BulkDatasetIdV2.INTERFACIAL_TENSION),
        (TestContentPathsApiV2.VLE, BulkDatasetIdV2.VLE),
        (TestContentPathsApiV2.MCM, BulkDatasetIdV2.MCM),
        (TestContentPathsApiV2.SLIMTUBE, BulkDatasetIdV2.SLIMTUBE),
        (TestContentPathsApiV2.EXTRACTION, BulkDatasetIdV2.EXTRACTION),
        (TestContentPathsApiV2.FRACTIONATION, BulkDatasetIdV2.FRACTIONATION),
        (TestContentPathsApiV2.RELATIVE_PERMEABILITY, BulkDatasetIdV2.RELATIVE_PERMEABILITY),
        (TestContentPathsApiV2.ROCK_COMPRESSIBILITY, BulkDatasetIdV2.ROCK_COMPRESSIBILITY),
        (TestContentPathsApiV2.NMR, BulkDatasetIdV2.NMR),
        (TestContentPathsApiV2.MULTIPLE_SALINITY, BulkDatasetIdV2.MULTIPLE_SALINITY),
        (TestContentPathsApiV2.GCMS_ALKANES, BulkDatasetIdV2.GCMS_ALKANES),
        (TestContentPathsApiV2.GCMS_AROMATICS, BulkDatasetIdV2.GCMS_AROMATICS),
        (TestContentPathsApiV2.GCMS_RATIOS, BulkDatasetIdV2.GCMS_RATIOS),
        (TestContentPathsApiV2.GAS_CHROMATOGRAPHY, BulkDatasetIdV2.GAS_CHROMATOGRAPHY),
        (TestContentPathsApiV2.GAS_COMPOSITION, BulkDatasetIdV2.GAS_COMPOSITION),
        (TestContentPathsApiV2.ISOTOPE_ANALYSIS, BulkDatasetIdV2.ISOTOPE_ANALYSIS),
        (TestContentPathsApiV2.BULK_PYROLYSIS, BulkDatasetIdV2.BULK_PYROLYSIS),
        (TestContentPathsApiV2.CORE_GAMMA, BulkDatasetIdV2.CORE_GAMMA),
        (TestContentPathsApiV2.MINING_GEOTECH_LOGGING, BulkDatasetIdV2.MINING_GEOTECH_LOGGING),
        (TestContentPathsApiV2.UNIAXIAL_TEST, BulkDatasetIdV2.UNIAXIAL_TEST),
        (TestContentPathsApiV2.GCMSMS_ANALYSIS, BulkDatasetIdV2.GCMSMS_ANALYSIS),
        (TestContentPathsApiV2.CEC_CONTENT, BulkDatasetIdV2.CEC_CONTENT),
        (TestContentPathsApiV2.ELECTRICAL_PROPERTIES, BulkDatasetIdV2.ELECTRICAL_PROPERTIES),
        (TestContentPathsApiV2.TRIAXIAL_TEST, BulkDatasetIdV2.TRIAXIAL_TEST),
        (TestContentPathsApiV2.CAP_PRESSURE, BulkDatasetIdV2.CAP_PRESSURE),
        (TestContentPathsApiV2.WETTABILITY_INDEX, BulkDatasetIdV2.WETTABILITY_INDEX),
        (TestContentPathsApiV2.TEC, BulkDatasetIdV2.TEC),
        (TestContentPathsApiV2.EDS_MAPPING, BulkDatasetIdV2.EDS_MAPPING),
        (TestContentPathsApiV2.XRF, BulkDatasetIdV2.XRF),
        (TestContentPathsApiV2.TENSILE_STRENGTH, BulkDatasetIdV2.TENSILE_STRENGTH),
        (TestContentPathsApiV2.VITRINITE_REFLECTANCE, BulkDatasetIdV2.VITRINITE_REFLECTANCE),
        (TestContentPathsApiV2.XRD, BulkDatasetIdV2.XRD),
        (TestContentPathsApiV2.PDP, BulkDatasetIdV2.PDP),
        (TestContentPathsApiV2.STO, BulkDatasetIdV2.STO),
        (TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS, BulkDatasetIdV2.CRUSHED_ROCK_ANALYSIS),
        (TestContentPathsPVTModel.MPFM_CALIBRATION, BulkDatasetIdPVTModel.MPFM_CALIBRATION),
        (TestContentPathsPVTModel.EOS, BulkDatasetIdPVTModel.EOS),
        (TestContentPathsPVTModel.COMPONENT_SCENARIO, BulkDatasetIdPVTModel.COMPONENT_SCENARIO),
        (TestContentPathsPVTModel.BLACK_OIL_TABLE, BulkDatasetIdPVTModel.BLACK_OIL_TABLE),
    ],
)
@pytest.mark.asyncio
async def test_get_data_wrong_content_header(data_endpoint_path, dataset_id):
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{data_endpoint_path}/{dataset_id}",
                headers={"Content-Type": "wrong-type"},
            )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    expected = {
        "code": status.HTTP_400_BAD_REQUEST,
        "reason": "The provided content-type is not supported. Please provide one of the next supported content types: ['application/json', 'application/x-parquet']",
    }
    assert response.json() == expected


@pytest.mark.parametrize(
    "data_endpoint_path,dataset_id,storage_method,osdu_records,dataset_method,blobs",
    [
        (
            TestContentPathsApiV2.RCA,
            rca_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", rca_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.CCE,
            cce_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                cce_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", cce_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.DIFF_LIB,
            diff_lib_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                diff_lib_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", diff_lib_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.TRANSPORT_TEST,
            transport_test_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                transport_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", transport_test_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS,
            compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                compositional_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", compositional_analysis_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.MSS,
            mss_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                mss_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", mss_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.SWELLING,
            swelling_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                swelling_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", swelling_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.CVD,
            cvd_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                cvd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", cvd_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.WATER_ANALYSIS,
            water_analysis_data_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                water_analysis_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", water_analysis_data_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.INTERFACIAL_TENSION,
            interfacial_tension_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                interfacial_tension_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", interfacial_tension_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.VLE,
            vle_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", vle_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.MCM,
            mcm_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                mcm_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", mcm_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.SLIMTUBE,
            slimtube_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", slimtube_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.EXTRACTION,
            extraction_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                extraction_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", extraction_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.FRACTIONATION,
            fractionation_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                fractionation_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", fractionation_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", relative_permeability_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.ROCK_COMPRESSIBILITY,
            rock_compressibility_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                rock_compressibility_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", rock_compressibility_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.NMR,
            nmr_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                nmr_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", nmr_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.MULTIPLE_SALINITY,
            multiple_salinity_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                multiple_salinity_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", multiple_salinity_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.GCMS_ALKANES,
            gcms_alkanes_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                gcms_alkanes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", gcms_alkanes_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.GCMS_AROMATICS,
            gcms_aromatics_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                gcms_aromatics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", gcms_aromatics_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.GCMS_RATIOS,
            gcms_ratios_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                gcms_ratios_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", gcms_ratios_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.GAS_CHROMATOGRAPHY,
            gas_chromatography_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                gas_chromatography_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", gas_chromatography_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.GAS_COMPOSITION,
            gas_composition_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                gas_composition_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", gas_composition_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.ISOTOPE_ANALYSIS,
            isotope_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                isotope_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", isotope_analysis_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.BULK_PYROLYSIS,
            bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                bulk_pyrolysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", bulk_pyrolysis_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.CORE_GAMMA,
            core_gamma_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                core_gamma_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", core_gamma_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.MINING_GEOTECH_LOGGING,
            mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                mining_geotech_logging_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", mining_geotech_logging_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.UNIAXIAL_TEST,
            uniaxial_test_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                uniaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_test_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.GCMSMS_ANALYSIS,
            gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                gcmsms_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", gcmsms_analysis_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.CEC_CONTENT,
            cec_content_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                cec_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", cec_content_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.ELECTRICAL_PROPERTIES,
            electricalproperties_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                electricalproperties_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", electricalproperties_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.TRIAXIAL_TEST,
            triaxial_test_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                triaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_test_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", cappressure_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.WETTABILITY_INDEX,
            wettability_index_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                wettability_index_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", wettability_index_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.TEC,
            tec_data_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                tec_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", tec_data_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.EDS_MAPPING,
            eds_mapping_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                eds_mapping_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", eds_mapping_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.XRF,
            xrf_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", xrf_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.TENSILE_STRENGTH,
            tensile_strength_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                tensile_strength_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", tensile_strength_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.VITRINITE_REFLECTANCE,
            vitrinite_reflectance_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                vitrinite_reflectance_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", vitrinite_reflectance_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.XRD,
            xrd_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", xrd_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.PDP,
            pdp_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                pdp_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", pdp_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
            crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", crushed_rock_analysis_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
            sto_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", sto_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsPVTModel.MPFM_CALIBRATION,
            mpfm_calibration_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                mpfm_calibration_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", mpfm_calibration_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsPVTModel.EOS,
            eos_content_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                eos_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", eos_content_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsPVTModel.COMPONENT_SCENARIO,
            component_scenario_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                component_scenario_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", component_scenario_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsPVTModel.BLACK_OIL_TABLE,
            black_oil_table_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                black_oil_table_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_table_mock_objects.TEST_DATA)],
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_content_parquet_data(
    data_endpoint_path,
    dataset_id,
    storage_method,
    osdu_records,
    dataset_method,
    blobs,
    with_patched_services_success,
):
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{data_endpoint_path}/{dataset_id}",
                headers=TEST_HEADERS_PARQUET,
            )
    arrow_table = pq.read_table(pa.BufferReader(blobs[0]))
    assert response.status_code == status.HTTP_200_OK
    assert pq.read_table(pa.BufferReader(response.content)).equals(arrow_table)


@pytest.mark.parametrize(
    "data_endpoint_path,params,storage_method,osdu_records,dataset_method,blobs,returned_data", [
        (
            f"{TestContentPathsApiV2.RCA}/{rca_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", rca_mock_objects.TEST_DATA)],
            rca_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CCE}/{cce_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [cce_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cce_mock_objects.TEST_DATA)],
            cce_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.DIFF_LIB}/{diff_lib_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [diff_lib_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", diff_lib_mock_objects.TEST_DATA)],
            diff_lib_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TRANSPORT_TEST}/{transport_test_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [transport_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", transport_test_mock_objects.TEST_DATA)],
            transport_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS}/{compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [compositional_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", compositional_analysis_mock_objects.TEST_DATA)],
            compositional_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MSS}/{mss_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [mss_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mss_mock_objects.TEST_DATA)],
            mss_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SWELLING}/{swelling_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [swelling_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", swelling_mock_objects.TEST_DATA)],
            swelling_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CVD}/{cvd_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [cvd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cvd_mock_objects.TEST_DATA)],
            cvd_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.WATER_ANALYSIS}/{water_analysis_data_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [water_analysis_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", water_analysis_data_mock_objects.TEST_DATA)],
            water_analysis_data_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.INTERFACIAL_TENSION}/{interfacial_tension_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [interfacial_tension_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", interfacial_tension_mock_objects.TEST_DATA)],
            interfacial_tension_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.VLE}/{vle_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", vle_mock_objects.TEST_DATA)],
            vle_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MCM}/{mcm_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [mcm_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mcm_mock_objects.TEST_DATA)],
            mcm_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SLIMTUBE}/{slimtube_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", slimtube_mock_objects.TEST_DATA)],
            slimtube_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.EXTRACTION}/{extraction_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [extraction_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", extraction_mock_objects.TEST_DATA)],
            extraction_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.FRACTIONATION}/{fractionation_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [fractionation_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", fractionation_mock_objects.TEST_DATA)],
            fractionation_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.RELATIVE_PERMEABILITY}/{relative_permeability_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", relative_permeability_mock_objects.TEST_DATA)],
            relative_permeability_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ROCK_COMPRESSIBILITY}/{rock_compressibility_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [rock_compressibility_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", rock_compressibility_mock_objects.TEST_DATA)],
            rock_compressibility_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.NMR}/{nmr_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [nmr_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", nmr_mock_objects.TEST_DATA)],
            nmr_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MULTIPLE_SALINITY}/{multiple_salinity_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [multiple_salinity_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", multiple_salinity_mock_objects.TEST_DATA)],
            multiple_salinity_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_ALKANES}/{gcms_alkanes_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [gcms_alkanes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_alkanes_mock_objects.TEST_DATA)],
            gcms_alkanes_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_AROMATICS}/{gcms_aromatics_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [gcms_aromatics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_aromatics_mock_objects.TEST_DATA)],
            gcms_aromatics_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_RATIOS}/{gcms_ratios_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [gcms_ratios_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_ratios_mock_objects.TEST_DATA)],
            gcms_ratios_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GAS_CHROMATOGRAPHY}/{gas_chromatography_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [gas_chromatography_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gas_chromatography_mock_objects.TEST_DATA)],
            gas_chromatography_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GAS_COMPOSITION}/{gas_composition_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [gas_composition_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gas_composition_mock_objects.TEST_DATA)],
            gas_composition_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotope_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [isotope_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", isotope_analysis_mock_objects.TEST_DATA)],
            isotope_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.BULK_PYROLYSIS}/{bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [bulk_pyrolysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", bulk_pyrolysis_mock_objects.TEST_DATA)],
            bulk_pyrolysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CORE_GAMMA}/{core_gamma_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [core_gamma_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", core_gamma_mock_objects.TEST_DATA)],
            core_gamma_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MINING_GEOTECH_LOGGING}/{mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [mining_geotech_logging_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mining_geotech_logging_mock_objects.TEST_DATA)],
            mining_geotech_logging_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [uniaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_test_mock_objects.TEST_DATA)],
            uniaxial_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMSMS_ANALYSIS}/{gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [gcmsms_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcmsms_analysis_mock_objects.TEST_DATA)],
            gcmsms_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ELECTRICAL_PROPERTIES}/{electricalproperties_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [electricalproperties_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", electricalproperties_mock_objects.TEST_DATA)],
            electricalproperties_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CEC_CONTENT}/{cec_content_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [cec_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cec_content_mock_objects.TEST_DATA)],
            cec_content_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [triaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_test_mock_objects.TEST_DATA)],
            triaxial_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CAP_PRESSURE}/{cappressure_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cappressure_mock_objects.TEST_DATA)],
            cappressure_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.WETTABILITY_INDEX}/{wettability_index_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [wettability_index_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", wettability_index_mock_objects.TEST_DATA)],
            wettability_index_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TEC}/{tec_data_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [tec_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", tec_data_mock_objects.TEST_DATA)],
            tec_data_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.EDS_MAPPING}/{eds_mapping_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [eds_mapping_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", eds_mapping_mock_objects.TEST_DATA)],
            eds_mapping_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.XRF}/{xrf_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", xrf_mock_objects.TEST_DATA)],
            xrf_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.RCA}/{rca_mock_objects.TEST_DATASET_RECORD_ID}",
            rca_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", rca_mock_objects.TEST_DATA)],
            rca_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CCE}/{cce_mock_objects.TEST_DATASET_RECORD_ID}",
            cce_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [cce_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cce_mock_objects.TEST_DATA)],
            cce_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.DIFF_LIB}/{diff_lib_mock_objects.TEST_DATASET_RECORD_ID}",
            diff_lib_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [diff_lib_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", diff_lib_mock_objects.TEST_DATA)],
            diff_lib_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TRANSPORT_TEST}/{transport_test_mock_objects.TEST_DATASET_RECORD_ID}",
            transport_test_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [transport_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", transport_test_mock_objects.TEST_DATA)],
            transport_test_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS}/{compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            compositional_analysis_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [compositional_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", compositional_analysis_mock_objects.TEST_DATA)],
            compositional_analysis_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MSS}/{mss_mock_objects.TEST_DATASET_RECORD_ID}",
            mss_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [mss_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mss_mock_objects.TEST_DATA)],
            mss_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SWELLING}/{swelling_mock_objects.TEST_DATASET_RECORD_ID}",
            swelling_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [swelling_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", swelling_mock_objects.TEST_DATA)],
            swelling_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CVD}/{cvd_mock_objects.TEST_DATASET_RECORD_ID}",
            cvd_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [cvd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cvd_mock_objects.TEST_DATA)],
            cvd_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.WATER_ANALYSIS}/{water_analysis_data_mock_objects.TEST_DATASET_RECORD_ID}",
            water_analysis_data_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [water_analysis_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", water_analysis_data_mock_objects.TEST_DATA)],
            water_analysis_data_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.INTERFACIAL_TENSION}/{interfacial_tension_mock_objects.TEST_DATASET_RECORD_ID}",
            interfacial_tension_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [interfacial_tension_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", interfacial_tension_mock_objects.TEST_DATA)],
            interfacial_tension_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.VLE}/{vle_mock_objects.TEST_DATASET_RECORD_ID}",
            vle_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", vle_mock_objects.TEST_DATA)],
            vle_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MCM}/{mcm_mock_objects.TEST_DATASET_RECORD_ID}",
            mcm_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [mcm_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mcm_mock_objects.TEST_DATA)],
            mcm_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SLIMTUBE}/{slimtube_mock_objects.TEST_DATASET_RECORD_ID}",
            slimtube_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", slimtube_mock_objects.TEST_DATA)],
            slimtube_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.EXTRACTION}/{extraction_mock_objects.TEST_DATASET_RECORD_ID}",
            extraction_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [extraction_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", extraction_mock_objects.TEST_DATA)],
            extraction_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.FRACTIONATION}/{fractionation_mock_objects.TEST_DATASET_RECORD_ID}",
            fractionation_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [fractionation_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", fractionation_mock_objects.TEST_DATA)],
            fractionation_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.RELATIVE_PERMEABILITY}/{relative_permeability_mock_objects.TEST_DATASET_RECORD_ID}",
            relative_permeability_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", relative_permeability_mock_objects.TEST_DATA)],
            relative_permeability_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ROCK_COMPRESSIBILITY}/{rock_compressibility_mock_objects.TEST_DATASET_RECORD_ID}",
            rock_compressibility_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [rock_compressibility_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", rock_compressibility_mock_objects.TEST_DATA)],
            rock_compressibility_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.NMR}/{nmr_mock_objects.TEST_DATASET_RECORD_ID}",
            nmr_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [nmr_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", nmr_mock_objects.TEST_DATA)],
            nmr_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MULTIPLE_SALINITY}/{multiple_salinity_mock_objects.TEST_DATASET_RECORD_ID}",
            multiple_salinity_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [multiple_salinity_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", multiple_salinity_mock_objects.TEST_DATA)],
            multiple_salinity_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_ALKANES}/{gcms_alkanes_mock_objects.TEST_DATASET_RECORD_ID}",
            gcms_alkanes_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [gcms_alkanes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_alkanes_mock_objects.TEST_DATA)],
            gcms_alkanes_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_AROMATICS}/{gcms_aromatics_mock_objects.TEST_DATASET_RECORD_ID}",
            gcms_aromatics_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [gcms_aromatics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_aromatics_mock_objects.TEST_DATA)],
            gcms_aromatics_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_RATIOS}/{gcms_ratios_mock_objects.TEST_DATASET_RECORD_ID}",
            gcms_ratios_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [gcms_ratios_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_ratios_mock_objects.TEST_DATA)],
            gcms_ratios_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GAS_CHROMATOGRAPHY}/{gas_chromatography_mock_objects.TEST_DATASET_RECORD_ID}",
            gas_chromatography_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [gas_chromatography_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gas_chromatography_mock_objects.TEST_DATA)],
            gas_chromatography_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GAS_COMPOSITION}/{gas_composition_mock_objects.TEST_DATASET_RECORD_ID}",
            gas_composition_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [gas_composition_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gas_composition_mock_objects.TEST_DATA)],
            gas_composition_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotope_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            isotope_analysis_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [isotope_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", isotope_analysis_mock_objects.TEST_DATA)],
            isotope_analysis_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.BULK_PYROLYSIS}/{bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID}",
            bulk_pyrolysis_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [bulk_pyrolysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", bulk_pyrolysis_mock_objects.TEST_DATA)],
            bulk_pyrolysis_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CORE_GAMMA}/{core_gamma_mock_objects.TEST_DATASET_RECORD_ID}",
            core_gamma_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [core_gamma_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", core_gamma_mock_objects.TEST_DATA)],
            core_gamma_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MINING_GEOTECH_LOGGING}/{mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID}",
            mining_geotech_logging_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [mining_geotech_logging_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mining_geotech_logging_mock_objects.TEST_DATA)],
            mining_geotech_logging_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
            uniaxial_test_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [uniaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_test_mock_objects.TEST_DATA)],
            uniaxial_test_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMSMS_ANALYSIS}/{gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            gcmsms_analysis_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [gcmsms_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcmsms_analysis_mock_objects.TEST_DATA)],
            gcmsms_analysis_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ELECTRICAL_PROPERTIES}/{electricalproperties_mock_objects.TEST_DATASET_RECORD_ID}",
            electricalproperties_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [electricalproperties_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", electricalproperties_mock_objects.TEST_DATA)],
            electricalproperties_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CEC_CONTENT}/{cec_content_mock_objects.TEST_DATASET_RECORD_ID}",
            cec_content_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [cec_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cec_content_mock_objects.TEST_DATA)],
            cec_content_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
            triaxial_test_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [triaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_test_mock_objects.TEST_DATA)],
            triaxial_test_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CAP_PRESSURE}/{cappressure_mock_objects.TEST_DATASET_RECORD_ID}",
            cappressure_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cappressure_mock_objects.TEST_DATA)],
            cappressure_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.WETTABILITY_INDEX}/{wettability_index_mock_objects.TEST_DATASET_RECORD_ID}",
            wettability_index_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [wettability_index_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", wettability_index_mock_objects.TEST_DATA)],
            wettability_index_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TEC}/{tec_data_mock_objects.TEST_DATASET_RECORD_ID}",
            tec_data_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [tec_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", tec_data_mock_objects.TEST_DATA)],
            tec_data_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.EDS_MAPPING}/{eds_mapping_mock_objects.TEST_DATASET_RECORD_ID}",
            eds_mapping_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [eds_mapping_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", eds_mapping_mock_objects.TEST_DATA)],
            eds_mapping_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.XRF}/{xrf_mock_objects.TEST_DATASET_RECORD_ID}",
            xrf_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", xrf_mock_objects.TEST_DATA)],
            xrf_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.RCA}/{rca_mock_objects.TEST_DATASET_RECORD_ID}",
            rca_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", rca_mock_objects.TEST_DATA)],
            rca_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CCE}/{cce_mock_objects.TEST_DATASET_RECORD_ID}",
            cce_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [cce_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cce_mock_objects.TEST_DATA)],
            cce_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.DIFF_LIB}/{diff_lib_mock_objects.TEST_DATASET_RECORD_ID}",
            diff_lib_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [diff_lib_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", diff_lib_mock_objects.TEST_DATA)],
            diff_lib_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TRANSPORT_TEST}/{transport_test_mock_objects.TEST_DATASET_RECORD_ID}",
            transport_test_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [transport_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", transport_test_mock_objects.TEST_DATA)],
            transport_test_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS}/{compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            compositional_analysis_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [compositional_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", compositional_analysis_mock_objects.TEST_DATA)],
            compositional_analysis_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MSS}/{mss_mock_objects.TEST_DATASET_RECORD_ID}",
            mss_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [mss_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mss_mock_objects.TEST_DATA)],
            mss_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SWELLING}/{swelling_mock_objects.TEST_DATASET_RECORD_ID}",
            swelling_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [swelling_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", swelling_mock_objects.TEST_DATA)],
            swelling_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CVD}/{cvd_mock_objects.TEST_DATASET_RECORD_ID}",
            cvd_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [cvd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cvd_mock_objects.TEST_DATA)],
            cvd_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.WATER_ANALYSIS}/{water_analysis_data_mock_objects.TEST_DATASET_RECORD_ID}",
            water_analysis_data_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [water_analysis_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", water_analysis_data_mock_objects.TEST_DATA)],
            water_analysis_data_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.INTERFACIAL_TENSION}/{interfacial_tension_mock_objects.TEST_DATASET_RECORD_ID}",
            interfacial_tension_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [interfacial_tension_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", interfacial_tension_mock_objects.TEST_DATA)],
            interfacial_tension_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.VLE}/{vle_mock_objects.TEST_DATASET_RECORD_ID}",
            vle_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", vle_mock_objects.TEST_DATA)],
            vle_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MCM}/{mcm_mock_objects.TEST_DATASET_RECORD_ID}",
            mcm_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [mcm_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mcm_mock_objects.TEST_DATA)],
            mcm_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SLIMTUBE}/{slimtube_mock_objects.TEST_DATASET_RECORD_ID}",
            slimtube_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", slimtube_mock_objects.TEST_DATA)],
            slimtube_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.EXTRACTION}/{extraction_mock_objects.TEST_DATASET_RECORD_ID}",
            extraction_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [extraction_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", extraction_mock_objects.TEST_DATA)],
            extraction_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.FRACTIONATION}/{fractionation_mock_objects.TEST_DATASET_RECORD_ID}",
            fractionation_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [fractionation_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", fractionation_mock_objects.TEST_DATA)],
            fractionation_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.RELATIVE_PERMEABILITY}/{relative_permeability_mock_objects.TEST_DATASET_RECORD_ID}",
            relative_permeability_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", relative_permeability_mock_objects.TEST_DATA)],
            relative_permeability_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ROCK_COMPRESSIBILITY}/{rock_compressibility_mock_objects.TEST_DATASET_RECORD_ID}",
            rock_compressibility_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [rock_compressibility_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", rock_compressibility_mock_objects.TEST_DATA)],
            rock_compressibility_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.NMR}/{nmr_mock_objects.TEST_DATASET_RECORD_ID}",
            nmr_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [nmr_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", nmr_mock_objects.TEST_DATA)],
            nmr_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MULTIPLE_SALINITY}/{multiple_salinity_mock_objects.TEST_DATASET_RECORD_ID}",
            multiple_salinity_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [multiple_salinity_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", multiple_salinity_mock_objects.TEST_DATA)],
            multiple_salinity_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_ALKANES}/{gcms_alkanes_mock_objects.TEST_DATASET_RECORD_ID}",
            gcms_alkanes_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [gcms_alkanes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_alkanes_mock_objects.TEST_DATA)],
            gcms_alkanes_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_AROMATICS}/{gcms_aromatics_mock_objects.TEST_DATASET_RECORD_ID}",
            gcms_aromatics_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [gcms_aromatics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_aromatics_mock_objects.TEST_DATA)],
            gcms_aromatics_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_RATIOS}/{gcms_ratios_mock_objects.TEST_DATASET_RECORD_ID}",
            gcms_ratios_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [gcms_ratios_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_ratios_mock_objects.TEST_DATA)],
            gcms_ratios_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GAS_CHROMATOGRAPHY}/{gas_chromatography_mock_objects.TEST_DATASET_RECORD_ID}",
            gas_chromatography_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [gas_chromatography_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gas_chromatography_mock_objects.TEST_DATA)],
            gas_chromatography_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GAS_COMPOSITION}/{gas_composition_mock_objects.TEST_DATASET_RECORD_ID}",
            gas_composition_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [gas_composition_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gas_composition_mock_objects.TEST_DATA)],
            gas_composition_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotope_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            isotope_analysis_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [isotope_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", isotope_analysis_mock_objects.TEST_DATA)],
            isotope_analysis_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.BULK_PYROLYSIS}/{bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID}",
            bulk_pyrolysis_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [bulk_pyrolysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", bulk_pyrolysis_mock_objects.TEST_DATA)],
            bulk_pyrolysis_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CORE_GAMMA}/{core_gamma_mock_objects.TEST_DATASET_RECORD_ID}",
            core_gamma_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [core_gamma_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", core_gamma_mock_objects.TEST_DATA)],
            core_gamma_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MINING_GEOTECH_LOGGING}/{mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID}",
            mining_geotech_logging_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [mining_geotech_logging_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mining_geotech_logging_mock_objects.TEST_DATA)],
            mining_geotech_logging_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
            uniaxial_test_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [uniaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_test_mock_objects.TEST_DATA)],
            uniaxial_test_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMSMS_ANALYSIS}/{gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            gcmsms_analysis_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [gcmsms_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcmsms_analysis_mock_objects.TEST_DATA)],
            gcmsms_analysis_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CEC_CONTENT}/{cec_content_mock_objects.TEST_DATASET_RECORD_ID}",
            cec_content_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [cec_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cec_content_mock_objects.TEST_DATA)],
            cec_content_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ELECTRICAL_PROPERTIES}/{electricalproperties_mock_objects.TEST_DATASET_RECORD_ID}",
            electricalproperties_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [electricalproperties_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", electricalproperties_mock_objects.TEST_DATA)],
            electricalproperties_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
            triaxial_test_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [triaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_test_mock_objects.TEST_DATA)],
            triaxial_test_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CAP_PRESSURE}/{cappressure_mock_objects.TEST_DATASET_RECORD_ID}",
            cappressure_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cappressure_mock_objects.TEST_DATA)],
            cappressure_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.WETTABILITY_INDEX}/{wettability_index_mock_objects.TEST_DATASET_RECORD_ID}",
            wettability_index_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [wettability_index_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", wettability_index_mock_objects.TEST_DATA)],
            wettability_index_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TEC}/{tec_data_mock_objects.TEST_DATASET_RECORD_ID}",
            tec_data_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [tec_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", tec_data_mock_objects.TEST_DATA)],
            tec_data_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.EDS_MAPPING}/{eds_mapping_mock_objects.TEST_DATASET_RECORD_ID}",
            eds_mapping_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [eds_mapping_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", eds_mapping_mock_objects.TEST_DATA)],
            eds_mapping_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.XRF}/{xrf_mock_objects.TEST_DATASET_RECORD_ID}",
            xrf_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", xrf_mock_objects.TEST_DATA)],
            xrf_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TENSILE_STRENGTH}/{tensile_strength_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [tensile_strength_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", tensile_strength_mock_objects.TEST_DATA)],
            tensile_strength_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TENSILE_STRENGTH}/{tensile_strength_mock_objects.TEST_DATASET_RECORD_ID}",
            tensile_strength_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [tensile_strength_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", tensile_strength_mock_objects.TEST_DATA)],
            tensile_strength_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TENSILE_STRENGTH}/{tensile_strength_mock_objects.TEST_DATASET_RECORD_ID}",
            tensile_strength_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [tensile_strength_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", tensile_strength_mock_objects.TEST_DATA)],
            tensile_strength_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.VITRINITE_REFLECTANCE}/{vitrinite_reflectance_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [vitrinite_reflectance_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", vitrinite_reflectance_mock_objects.TEST_DATA)],
            vitrinite_reflectance_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.VITRINITE_REFLECTANCE}/{vitrinite_reflectance_mock_objects.TEST_DATASET_RECORD_ID}",
            vitrinite_reflectance_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [vitrinite_reflectance_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", vitrinite_reflectance_mock_objects.TEST_DATA)],
            vitrinite_reflectance_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.VITRINITE_REFLECTANCE}/{vitrinite_reflectance_mock_objects.TEST_DATASET_RECORD_ID}",
            vitrinite_reflectance_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [vitrinite_reflectance_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", vitrinite_reflectance_mock_objects.TEST_DATA)],
            vitrinite_reflectance_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.XRD}/{xrd_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", xrd_mock_objects.TEST_DATA)],
            xrd_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.XRD}/{xrd_mock_objects.TEST_DATASET_RECORD_ID}",
            xrd_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", xrd_mock_objects.TEST_DATA)],
            xrd_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.XRD}/{xrd_mock_objects.TEST_DATASET_RECORD_ID}",
            xrd_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", xrd_mock_objects.TEST_DATA)],
            xrd_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.PDP}/{pdp_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [pdp_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", pdp_mock_objects.TEST_DATA)],
            pdp_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.PDP}/{pdp_mock_objects.TEST_DATASET_RECORD_ID}",
            pdp_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [pdp_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", pdp_mock_objects.TEST_DATA)],
            pdp_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.PDP}/{pdp_mock_objects.TEST_DATASET_RECORD_ID}",
            pdp_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [pdp_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", pdp_mock_objects.TEST_DATA)],
            pdp_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.STO}/{sto_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", sto_mock_objects.TEST_DATA)],
            sto_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.STO}/{sto_mock_objects.TEST_DATASET_RECORD_ID}",
            sto_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", sto_mock_objects.TEST_DATA)],
            sto_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.STO}/{sto_mock_objects.TEST_DATASET_RECORD_ID}",
            sto_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", sto_mock_objects.TEST_DATA)],
            sto_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS}/{crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", crushed_rock_analysis_mock_objects.TEST_DATA)],
            crushed_rock_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS}/{crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            crushed_rock_analysis_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", crushed_rock_analysis_mock_objects.TEST_DATA)],
            crushed_rock_analysis_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS}/{crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            crushed_rock_analysis_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", crushed_rock_analysis_mock_objects.TEST_DATA)],
            crushed_rock_analysis_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.MPFM_CALIBRATION}/{mpfm_calibration_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [mpfm_calibration_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mpfm_calibration_mock_objects.TEST_DATA)],
            mpfm_calibration_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.MPFM_CALIBRATION}/{mpfm_calibration_mock_objects.TEST_DATASET_RECORD_ID}",
            mpfm_calibration_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [mpfm_calibration_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mpfm_calibration_mock_objects.TEST_DATA)],
            mpfm_calibration_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.MPFM_CALIBRATION}/{mpfm_calibration_mock_objects.TEST_DATASET_RECORD_ID}",
            mpfm_calibration_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [mpfm_calibration_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mpfm_calibration_mock_objects.TEST_DATA)],
            mpfm_calibration_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.EOS}/{eos_content_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [eos_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", eos_content_mock_objects.TEST_DATA)],
            eos_content_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.EOS}/{eos_content_mock_objects.TEST_DATASET_RECORD_ID}",
            eos_content_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [eos_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", eos_content_mock_objects.TEST_DATA)],
            eos_content_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.EOS}/{eos_content_mock_objects.TEST_DATASET_RECORD_ID}",
            eos_content_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [eos_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", eos_content_mock_objects.TEST_DATA)],
            eos_content_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.COMPONENT_SCENARIO}/{component_scenario_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [component_scenario_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", component_scenario_mock_objects.TEST_DATA)],
            component_scenario_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.COMPONENT_SCENARIO}/{component_scenario_mock_objects.TEST_DATASET_RECORD_ID}",
            component_scenario_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [component_scenario_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", component_scenario_mock_objects.TEST_DATA)],
            component_scenario_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.COMPONENT_SCENARIO}/{component_scenario_mock_objects.TEST_DATASET_RECORD_ID}",
            component_scenario_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [component_scenario_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", component_scenario_mock_objects.TEST_DATA)],
            component_scenario_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.BLACK_OIL_TABLE}/{black_oil_table_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [black_oil_table_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_table_mock_objects.TEST_DATA)],
            black_oil_table_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.BLACK_OIL_TABLE}/{black_oil_table_mock_objects.TEST_DATASET_RECORD_ID}",
            black_oil_table_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [black_oil_table_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_table_mock_objects.TEST_DATA)],
            black_oil_table_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.BLACK_OIL_TABLE}/{black_oil_table_mock_objects.TEST_DATASET_RECORD_ID}",
            black_oil_table_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [black_oil_table_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_table_mock_objects.TEST_DATA)],
            black_oil_table_mock_objects.TEST_AGGREGATED_DATA,
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_data_json_data(
    data_endpoint_path,
    params,
    storage_method,
    osdu_records,
    dataset_method,
    blobs,
    returned_data,
    with_patched_services_success,
):
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                data_endpoint_path,
                headers=TEST_HEADERS_JSON,
                params=params,
            )
    from loguru import logger
    logger.warning(response.json())
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["index"] == returned_data["index"]
    assert set(response.json()["columns"]) == set(returned_data["columns"])
    assert all(i in response.json()["data"][0] for i in returned_data["data"][0])


@pytest.mark.parametrize(
    "data_endpoint_path,storage_method,osdu_records,dataset_method,blobs,returned_data", [
        (
            f"{TestContentPathsApiV2.RCA}/{rca_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", rca_mock_objects.TEST_DATA)],
            rca_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CCE}/{cce_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [cce_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cce_mock_objects.TEST_DATA)],
            cce_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.DIFF_LIB}/{diff_lib_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [diff_lib_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", diff_lib_mock_objects.TEST_DATA)],
            diff_lib_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TRANSPORT_TEST}/{transport_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [transport_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", transport_test_mock_objects.TEST_DATA)],
            transport_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS}/{compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [compositional_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", compositional_analysis_mock_objects.TEST_DATA)],
            compositional_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MSS}/{mss_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [mss_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mss_mock_objects.TEST_DATA)],
            mss_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SWELLING}/{swelling_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [swelling_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", swelling_mock_objects.TEST_DATA)],
            swelling_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CVD}/{cvd_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [cvd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cvd_mock_objects.TEST_DATA)],
            cvd_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.WATER_ANALYSIS}/{water_analysis_data_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [water_analysis_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", water_analysis_data_mock_objects.TEST_DATA)],
            water_analysis_data_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.INTERFACIAL_TENSION}/{interfacial_tension_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [interfacial_tension_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", interfacial_tension_mock_objects.TEST_DATA)],
            interfacial_tension_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.VLE}/{vle_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", vle_mock_objects.TEST_DATA)],
            vle_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MCM}/{mcm_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [mcm_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mcm_mock_objects.TEST_DATA)],
            mcm_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SLIMTUBE}/{slimtube_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", slimtube_mock_objects.TEST_DATA)],
            slimtube_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.EXTRACTION}/{extraction_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [extraction_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", extraction_mock_objects.TEST_DATA)],
            extraction_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.FRACTIONATION}/{fractionation_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [fractionation_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", fractionation_mock_objects.TEST_DATA)],
            fractionation_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.RELATIVE_PERMEABILITY}/{relative_permeability_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", relative_permeability_mock_objects.TEST_DATA)],
            relative_permeability_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ROCK_COMPRESSIBILITY}/{rock_compressibility_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [rock_compressibility_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", rock_compressibility_mock_objects.TEST_DATA)],
            rock_compressibility_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.NMR}/{nmr_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [nmr_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", nmr_mock_objects.TEST_DATA)],
            nmr_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MULTIPLE_SALINITY}/{multiple_salinity_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [multiple_salinity_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", multiple_salinity_mock_objects.TEST_DATA)],
            multiple_salinity_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_ALKANES}/{gcms_alkanes_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gcms_alkanes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_alkanes_mock_objects.TEST_DATA)],
            gcms_alkanes_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_AROMATICS}/{gcms_aromatics_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gcms_aromatics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_aromatics_mock_objects.TEST_DATA)],
            gcms_aromatics_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_RATIOS}/{gcms_ratios_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gcms_ratios_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_ratios_mock_objects.TEST_DATA)],
            gcms_ratios_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GAS_CHROMATOGRAPHY}/{gas_chromatography_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gas_chromatography_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gas_chromatography_mock_objects.TEST_DATA)],
            gas_chromatography_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GAS_COMPOSITION}/{gas_composition_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gas_composition_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gas_composition_mock_objects.TEST_DATA)],
            gas_composition_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotope_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [isotope_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", isotope_analysis_mock_objects.TEST_DATA)],
            isotope_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.BULK_PYROLYSIS}/{bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [bulk_pyrolysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", bulk_pyrolysis_mock_objects.TEST_DATA)],
            bulk_pyrolysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CORE_GAMMA}/{core_gamma_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [core_gamma_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", core_gamma_mock_objects.TEST_DATA)],
            core_gamma_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MINING_GEOTECH_LOGGING}/{mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [mining_geotech_logging_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mining_geotech_logging_mock_objects.TEST_DATA)],
            mining_geotech_logging_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [uniaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_test_mock_objects.TEST_DATA)],
            uniaxial_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMSMS_ANALYSIS}/{gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gcmsms_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcmsms_analysis_mock_objects.TEST_DATA)],
            gcmsms_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CEC_CONTENT}/{cec_content_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [cec_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cec_content_mock_objects.TEST_DATA)],
            cec_content_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ELECTRICAL_PROPERTIES}/{electricalproperties_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [electricalproperties_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", electricalproperties_mock_objects.TEST_DATA)],
            electricalproperties_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [triaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_test_mock_objects.TEST_DATA)],
            triaxial_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CAP_PRESSURE}/{cappressure_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cappressure_mock_objects.TEST_DATA)],
            cappressure_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.WETTABILITY_INDEX}/{wettability_index_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [wettability_index_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", wettability_index_mock_objects.TEST_DATA)],
            wettability_index_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TEC}/{tec_data_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [tec_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", tec_data_mock_objects.TEST_DATA)],
            tec_data_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.EDS_MAPPING}/{eds_mapping_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [eds_mapping_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", eds_mapping_mock_objects.TEST_DATA)],
            eds_mapping_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.XRF}/{xrf_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", xrf_mock_objects.TEST_DATA)],
            xrf_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TENSILE_STRENGTH}/{tensile_strength_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [tensile_strength_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", tensile_strength_mock_objects.TEST_DATA)],
            tensile_strength_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.VITRINITE_REFLECTANCE}/{vitrinite_reflectance_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [vitrinite_reflectance_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", vitrinite_reflectance_mock_objects.TEST_DATA)],
            vitrinite_reflectance_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.PDP}/{pdp_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [pdp_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", pdp_mock_objects.TEST_DATA)],
            pdp_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.STO}/{sto_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", sto_mock_objects.TEST_DATA)],
            sto_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS}/{crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", crushed_rock_analysis_mock_objects.TEST_DATA)],
            crushed_rock_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.MPFM_CALIBRATION}/{mpfm_calibration_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [mpfm_calibration_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mpfm_calibration_mock_objects.TEST_DATA)],
            mpfm_calibration_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.EOS}/{eos_content_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [eos_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", eos_content_mock_objects.TEST_DATA)],
            eos_content_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.COMPONENT_SCENARIO}/{component_scenario_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [component_scenario_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", component_scenario_mock_objects.TEST_DATA)],
            component_scenario_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.BLACK_OIL_TABLE}/{black_oil_table_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [black_oil_table_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_table_mock_objects.TEST_DATA)],
            black_oil_table_mock_objects.TEST_DATA,
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_data_json_data_no_content_schema_version(
    data_endpoint_path,
    storage_method,
    osdu_records,
    dataset_method,
    blobs,
    returned_data,
    with_patched_services_success,
):
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                data_endpoint_path,
                headers=TEST_HEADERS_WITHOUT_SCHEMA_VERSION,
            )
    expected_error = {
        "code": status.HTTP_400_BAD_REQUEST,
        "reason": "No schema version specified or invalid schema format. Check if the schema version is specified in the 'Accept' header. Example: --header 'Accept: */*;version=1.0.0'",
    }

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == expected_error


@pytest.mark.parametrize(
    "data_endpoint_path,storage_method,osdu_records,dataset_method,blobs,returned_data", [
        (
            f"{TestContentPathsApiV2.RCA}/{rca_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", rca_mock_objects.TEST_DATA)],
            rca_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CCE}/{cce_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [cce_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cce_mock_objects.TEST_DATA)],
            cce_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.DIFF_LIB}/{diff_lib_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [diff_lib_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", diff_lib_mock_objects.TEST_DATA)],
            diff_lib_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TRANSPORT_TEST}/{transport_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [transport_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", transport_test_mock_objects.TEST_DATA)],
            transport_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS}/{compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [compositional_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", compositional_analysis_mock_objects.TEST_DATA)],
            compositional_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MSS}/{mss_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [mss_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mss_mock_objects.TEST_DATA)],
            mss_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SWELLING}/{swelling_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [swelling_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", swelling_mock_objects.TEST_DATA)],
            swelling_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CVD}/{cvd_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [cvd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cvd_mock_objects.TEST_DATA)],
            cvd_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.WATER_ANALYSIS}/{water_analysis_data_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [water_analysis_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", water_analysis_data_mock_objects.TEST_DATA)],
            water_analysis_data_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.INTERFACIAL_TENSION}/{interfacial_tension_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [interfacial_tension_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", interfacial_tension_mock_objects.TEST_DATA)],
            interfacial_tension_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.VLE}/{vle_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", vle_mock_objects.TEST_DATA)],
            vle_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MCM}/{mcm_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [mcm_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mcm_mock_objects.TEST_DATA)],
            mcm_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SLIMTUBE}/{slimtube_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", slimtube_mock_objects.TEST_DATA)],
            slimtube_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.EXTRACTION}/{extraction_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [extraction_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", extraction_mock_objects.TEST_DATA)],
            extraction_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.FRACTIONATION}/{fractionation_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [fractionation_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", fractionation_mock_objects.TEST_DATA)],
            fractionation_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.RELATIVE_PERMEABILITY}/{relative_permeability_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", relative_permeability_mock_objects.TEST_DATA)],
            relative_permeability_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ROCK_COMPRESSIBILITY}/{rock_compressibility_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [rock_compressibility_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", rock_compressibility_mock_objects.TEST_DATA)],
            rock_compressibility_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.NMR}/{nmr_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [nmr_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", nmr_mock_objects.TEST_DATA)],
            nmr_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MULTIPLE_SALINITY}/{multiple_salinity_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [multiple_salinity_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", multiple_salinity_mock_objects.TEST_DATA)],
            multiple_salinity_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_ALKANES}/{gcms_alkanes_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gcms_alkanes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_alkanes_mock_objects.TEST_DATA)],
            gcms_alkanes_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_AROMATICS}/{gcms_aromatics_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gcms_aromatics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_aromatics_mock_objects.TEST_DATA)],
            gcms_aromatics_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_RATIOS}/{gcms_ratios_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gcms_ratios_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_ratios_mock_objects.TEST_DATA)],
            gcms_ratios_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GAS_CHROMATOGRAPHY}/{gas_chromatography_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gas_chromatography_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gas_chromatography_mock_objects.TEST_DATA)],
            gas_chromatography_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GAS_COMPOSITION}/{gas_composition_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gas_composition_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gas_composition_mock_objects.TEST_DATA)],
            gas_composition_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotope_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [isotope_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", isotope_analysis_mock_objects.TEST_DATA)],
            isotope_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.BULK_PYROLYSIS}/{bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [bulk_pyrolysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", bulk_pyrolysis_mock_objects.TEST_DATA)],
            bulk_pyrolysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CORE_GAMMA}/{core_gamma_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [core_gamma_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", core_gamma_mock_objects.TEST_DATA)],
            core_gamma_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MINING_GEOTECH_LOGGING}/{mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [mining_geotech_logging_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mining_geotech_logging_mock_objects.TEST_DATA)],
            mining_geotech_logging_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [uniaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_test_mock_objects.TEST_DATA)],
            uniaxial_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMSMS_ANALYSIS}/{gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gcmsms_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcmsms_analysis_mock_objects.TEST_DATA)],
            gcmsms_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CEC_CONTENT}/{cec_content_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [cec_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cec_content_mock_objects.TEST_DATA)],
            cec_content_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ELECTRICAL_PROPERTIES}/{electricalproperties_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [electricalproperties_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", electricalproperties_mock_objects.TEST_DATA)],
            electricalproperties_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [triaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_test_mock_objects.TEST_DATA)],
            triaxial_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CAP_PRESSURE}/{cappressure_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cappressure_mock_objects.TEST_DATA)],
            cappressure_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.WETTABILITY_INDEX}/{wettability_index_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [wettability_index_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", wettability_index_mock_objects.TEST_DATA)],
            wettability_index_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TEC}/{tec_data_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [tec_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", tec_data_mock_objects.TEST_DATA)],
            tec_data_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.EDS_MAPPING}/{eds_mapping_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [eds_mapping_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", eds_mapping_mock_objects.TEST_DATA)],
            eds_mapping_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.XRF}/{xrf_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", xrf_mock_objects.TEST_DATA)],
            xrf_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TENSILE_STRENGTH}/{tensile_strength_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [tensile_strength_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", tensile_strength_mock_objects.TEST_DATA)],
            tensile_strength_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.VITRINITE_REFLECTANCE}/{vitrinite_reflectance_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [vitrinite_reflectance_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", vitrinite_reflectance_mock_objects.TEST_DATA)],
            vitrinite_reflectance_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.XRD}/{xrd_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", xrd_mock_objects.TEST_DATA)],
            xrd_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.PDP}/{pdp_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [pdp_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", pdp_mock_objects.TEST_DATA)],
            pdp_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.STO}/{sto_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", sto_mock_objects.TEST_DATA)],
            sto_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS}/{crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", crushed_rock_analysis_mock_objects.TEST_DATA)],
            crushed_rock_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.MPFM_CALIBRATION}/{mpfm_calibration_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [mpfm_calibration_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mpfm_calibration_mock_objects.TEST_DATA)],
            mpfm_calibration_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.EOS}/{eos_content_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [eos_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", eos_content_mock_objects.TEST_DATA)],
            eos_content_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.COMPONENT_SCENARIO}/{component_scenario_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [component_scenario_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", component_scenario_mock_objects.TEST_DATA)],
            component_scenario_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.BLACK_OIL_TABLE}/{black_oil_table_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [black_oil_table_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_table_mock_objects.TEST_DATA)],
            black_oil_table_mock_objects.TEST_DATA,
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_data_json_data_improper_schema_version(
    data_endpoint_path,
    storage_method,
    osdu_records,
    dataset_method,
    blobs,
    returned_data,
    with_patched_services_success,
):
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                data_endpoint_path,
                headers=TEST_HEADERS_IMPROPER_SCHEMA_VERSION,
            )
    expected_error = {
        "code": status.HTTP_400_BAD_REQUEST,
        "reason": "No schema version specified or invalid schema format. Check if the schema version is specified in the 'Accept' header. Example: --header 'Accept: */*;version=1.0.0'",
    }

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == expected_error


@pytest.mark.parametrize(
    "data_endpoint_path,storage_method,osdu_records,dataset_method,blobs,returned_data", [
        (
            f"{TestContentPathsApiV2.RCA}/{rca_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [rca_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", rca_mock_objects.TEST_DATA)],
            rca_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CCE}/{cce_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [cce_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cce_mock_objects.TEST_DATA)],
            cce_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.DIFF_LIB}/{diff_lib_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [diff_lib_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", diff_lib_mock_objects.TEST_DATA)],
            diff_lib_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TRANSPORT_TEST}/{transport_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [transport_test_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", transport_test_mock_objects.TEST_DATA)],
            transport_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS}/{compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [compositional_analysis_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", compositional_analysis_mock_objects.TEST_DATA)],
            compositional_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MSS}/{mss_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [mss_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mss_mock_objects.TEST_DATA)],
            mss_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SWELLING}/{swelling_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [swelling_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", swelling_mock_objects.TEST_DATA)],
            swelling_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CVD}/{cvd_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [cvd_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cvd_mock_objects.TEST_DATA)],
            cvd_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.WATER_ANALYSIS}/{water_analysis_data_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [water_analysis_data_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", water_analysis_data_mock_objects.TEST_DATA)],
            water_analysis_data_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.INTERFACIAL_TENSION}/{interfacial_tension_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [interfacial_tension_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", interfacial_tension_mock_objects.TEST_DATA)],
            interfacial_tension_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.VLE}/{vle_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [vle_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", vle_mock_objects.TEST_DATA)],
            vle_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MCM}/{mcm_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [mcm_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mcm_mock_objects.TEST_DATA)],
            mcm_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SLIMTUBE}/{slimtube_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [slimtube_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", slimtube_mock_objects.TEST_DATA)],
            slimtube_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.EXTRACTION}/{extraction_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [extraction_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", extraction_mock_objects.TEST_DATA)],
            extraction_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.FRACTIONATION}/{fractionation_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [fractionation_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", fractionation_mock_objects.TEST_DATA)],
            fractionation_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.RELATIVE_PERMEABILITY}/{relative_permeability_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [relative_permeability_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", relative_permeability_mock_objects.TEST_DATA)],
            relative_permeability_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ROCK_COMPRESSIBILITY}/{rock_compressibility_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [rock_compressibility_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", rock_compressibility_mock_objects.TEST_DATA)],
            rock_compressibility_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.NMR}/{nmr_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [nmr_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", nmr_mock_objects.TEST_DATA)],
            nmr_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MULTIPLE_SALINITY}/{multiple_salinity_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [multiple_salinity_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", multiple_salinity_mock_objects.TEST_DATA)],
            multiple_salinity_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_ALKANES}/{gcms_alkanes_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gcms_alkanes_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_alkanes_mock_objects.TEST_DATA)],
            gcms_alkanes_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_AROMATICS}/{gcms_aromatics_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gcms_aromatics_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_aromatics_mock_objects.TEST_DATA)],
            gcms_aromatics_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMS_RATIOS}/{gcms_ratios_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gcms_ratios_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcms_ratios_mock_objects.TEST_DATA)],
            gcms_ratios_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GAS_CHROMATOGRAPHY}/{gas_chromatography_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gas_chromatography_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gas_chromatography_mock_objects.TEST_DATA)],
            gas_chromatography_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GAS_COMPOSITION}/{gas_composition_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gas_composition_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gas_composition_mock_objects.TEST_DATA)],
            gas_composition_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotope_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [isotope_analysis_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", isotope_analysis_mock_objects.TEST_DATA)],
            isotope_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.BULK_PYROLYSIS}/{bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [bulk_pyrolysis_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", bulk_pyrolysis_mock_objects.TEST_DATA)],
            bulk_pyrolysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CORE_GAMMA}/{core_gamma_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [core_gamma_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", core_gamma_mock_objects.TEST_DATA)],
            core_gamma_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.MINING_GEOTECH_LOGGING}/{mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [mining_geotech_logging_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mining_geotech_logging_mock_objects.TEST_DATA)],
            mining_geotech_logging_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [uniaxial_test_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_test_mock_objects.TEST_DATA)],
            uniaxial_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.GCMSMS_ANALYSIS}/{gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [gcmsms_analysis_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", gcmsms_analysis_mock_objects.TEST_DATA)],
            gcmsms_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CEC_CONTENT}/{cec_content_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [cec_content_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cec_content_mock_objects.TEST_DATA)],
            cec_content_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ELECTRICAL_PROPERTIES}/{electricalproperties_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [electricalproperties_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", electricalproperties_mock_objects.TEST_DATA)],
            electricalproperties_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [triaxial_test_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_test_mock_objects.TEST_DATA)],
            triaxial_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CAP_PRESSURE}/{cappressure_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [cappressure_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cappressure_mock_objects.TEST_DATA)],
            cappressure_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.WETTABILITY_INDEX}/{wettability_index_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [wettability_index_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", wettability_index_mock_objects.TEST_DATA)],
            wettability_index_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.TEC}/{tec_data_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [tec_data_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", tec_data_mock_objects.TEST_DATA)],
            tec_data_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.EDS_MAPPING}/{eds_mapping_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [eds_mapping_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", eds_mapping_mock_objects.TEST_DATA)],
            eds_mapping_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.XRF}/{xrf_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [xrf_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", xrf_mock_objects.TEST_DATA)],
            xrf_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.VITRINITE_REFLECTANCE}/{vitrinite_reflectance_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [vitrinite_reflectance_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", vitrinite_reflectance_mock_objects.TEST_DATA)],
            vitrinite_reflectance_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.XRD}/{xrd_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [xrd_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", xrd_mock_objects.TEST_DATA)],
            xrd_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.PDP}/{pdp_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [pdp_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", pdp_mock_objects.TEST_DATA)],
            pdp_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.STO}/{sto_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [sto_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", sto_mock_objects.TEST_DATA)],
            sto_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS}/{crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", crushed_rock_analysis_mock_objects.TEST_DATA)],
            crushed_rock_analysis_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.MPFM_CALIBRATION}/{mpfm_calibration_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [mpfm_calibration_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", mpfm_calibration_mock_objects.TEST_DATA)],
            mpfm_calibration_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.EOS}/{eos_content_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [eos_content_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", eos_content_mock_objects.TEST_DATA)],
            eos_content_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.COMPONENT_SCENARIO}/{component_scenario_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [component_scenario_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", component_scenario_mock_objects.TEST_DATA)],
            component_scenario_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsPVTModel.BLACK_OIL_TABLE}/{black_oil_table_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [black_oil_table_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_table_mock_objects.TEST_DATA)],
            black_oil_table_mock_objects.TEST_DATA,
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_data_json_data_no_schema_version_for_dataset(
    data_endpoint_path,
    storage_method,
    osdu_records,
    dataset_method,
    blobs,
    returned_data,
    with_patched_services_success,
):
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                data_endpoint_path,
                headers=TEST_HEADERS_JSON,
            )
    expected_error = {
        "code": status.HTTP_400_BAD_REQUEST,
        "reason": "Invalid schema version has been provided. Schema version 1.0.0 is not one of proper versions: {'2.0.0'}",
    }

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == expected_error


@pytest.mark.parametrize(
    "data_endpoint_path,record_data,test_data,test_dataset_record_id,test_ddms_urn",
    [
        (
            TestContentPathsApiV2.RCA,
            rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            rca_mock_objects.TEST_DATA,
            rca_mock_objects.TEST_DATASET_RECORD_ID,
            rca_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CCE,
            cce_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cce_mock_objects.TEST_DATA,
            cce_mock_objects.TEST_DATASET_RECORD_ID,
            cce_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.DIFF_LIB,
            diff_lib_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            diff_lib_mock_objects.TEST_DATA,
            diff_lib_mock_objects.TEST_DATASET_RECORD_ID,
            diff_lib_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TRANSPORT_TEST,
            transport_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            transport_test_mock_objects.TEST_DATA,
            transport_test_mock_objects.TEST_DATASET_RECORD_ID,
            transport_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS,
            compositional_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            compositional_analysis_mock_objects.TEST_DATA,
            compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            compositional_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MSS,
            mss_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mss_mock_objects.TEST_DATA,
            mss_mock_objects.TEST_DATASET_RECORD_ID,
            mss_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SWELLING,
            swelling_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            swelling_mock_objects.TEST_DATA,
            swelling_mock_objects.TEST_DATASET_RECORD_ID,
            swelling_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CVD,
            cvd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cvd_mock_objects.TEST_DATA,
            cvd_mock_objects.TEST_DATASET_RECORD_ID,
            cvd_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.WATER_ANALYSIS,
            water_analysis_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            water_analysis_data_mock_objects.TEST_DATA,
            water_analysis_data_mock_objects.TEST_DATASET_RECORD_ID,
            water_analysis_data_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.INTERFACIAL_TENSION,
            interfacial_tension_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            interfacial_tension_mock_objects.TEST_DATA,
            interfacial_tension_mock_objects.TEST_DATASET_RECORD_ID,
            interfacial_tension_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.VLE,
            vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            vle_mock_objects.TEST_DATA,
            vle_mock_objects.TEST_DATASET_RECORD_ID,
            vle_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MCM,
            mcm_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mcm_mock_objects.TEST_DATA,
            mcm_mock_objects.TEST_DATASET_RECORD_ID,
            mcm_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SLIMTUBE,
            slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            slimtube_mock_objects.TEST_DATA,
            slimtube_mock_objects.TEST_DATASET_RECORD_ID,
            slimtube_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.EXTRACTION,
            extraction_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            extraction_mock_objects.TEST_DATA,
            extraction_mock_objects.TEST_DATASET_RECORD_ID,
            extraction_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.FRACTIONATION,
            fractionation_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            fractionation_mock_objects.TEST_DATA,
            fractionation_mock_objects.TEST_DATASET_RECORD_ID,
            fractionation_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            relative_permeability_mock_objects.TEST_DATA,
            relative_permeability_mock_objects.TEST_DATASET_RECORD_ID,
            relative_permeability_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ROCK_COMPRESSIBILITY,
            rock_compressibility_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            rock_compressibility_mock_objects.TEST_DATA,
            rock_compressibility_mock_objects.TEST_DATASET_RECORD_ID,
            rock_compressibility_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.NMR,
            nmr_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            nmr_mock_objects.TEST_DATA,
            nmr_mock_objects.TEST_DATASET_RECORD_ID,
            nmr_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MULTIPLE_SALINITY,
            multiple_salinity_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            multiple_salinity_mock_objects.TEST_DATA,
            multiple_salinity_mock_objects.TEST_DATASET_RECORD_ID,
            multiple_salinity_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMS_ALKANES,
            gcms_alkanes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_alkanes_mock_objects.TEST_DATA,
            gcms_alkanes_mock_objects.TEST_DATASET_RECORD_ID,
            gcms_alkanes_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMS_AROMATICS,
            gcms_aromatics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_aromatics_mock_objects.TEST_DATA,
            gcms_aromatics_mock_objects.TEST_DATASET_RECORD_ID,
            gcms_aromatics_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMS_RATIOS,
            gcms_ratios_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_ratios_mock_objects.TEST_DATA,
            gcms_ratios_mock_objects.TEST_DATASET_RECORD_ID,
            gcms_ratios_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GAS_CHROMATOGRAPHY,
            gas_chromatography_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gas_chromatography_mock_objects.TEST_DATA,
            gas_chromatography_mock_objects.TEST_DATASET_RECORD_ID,
            gas_chromatography_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GAS_COMPOSITION,
            gas_composition_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gas_composition_mock_objects.TEST_DATA,
            gas_composition_mock_objects.TEST_DATASET_RECORD_ID,
            gas_composition_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ISOTOPE_ANALYSIS,
            isotope_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            isotope_analysis_mock_objects.TEST_DATA,
            isotope_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            isotope_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.BULK_PYROLYSIS,
            bulk_pyrolysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            bulk_pyrolysis_mock_objects.TEST_DATA,
            bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID,
            bulk_pyrolysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CORE_GAMMA,
            core_gamma_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            core_gamma_mock_objects.TEST_DATA,
            core_gamma_mock_objects.TEST_DATASET_RECORD_ID,
            core_gamma_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MINING_GEOTECH_LOGGING,
            mining_geotech_logging_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mining_geotech_logging_mock_objects.TEST_DATA,
            mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID,
            mining_geotech_logging_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.UNIAXIAL_TEST,
            uniaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            uniaxial_test_mock_objects.TEST_DATA,
            uniaxial_test_mock_objects.TEST_DATASET_RECORD_ID,
            uniaxial_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMSMS_ANALYSIS,
            gcmsms_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcmsms_analysis_mock_objects.TEST_DATA,
            gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            gcmsms_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CEC_CONTENT,
            cec_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cec_content_mock_objects.TEST_DATA,
            cec_content_mock_objects.TEST_DATASET_RECORD_ID,
            cec_content_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ELECTRICAL_PROPERTIES,
            electricalproperties_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            electricalproperties_mock_objects.TEST_DATA,
            electricalproperties_mock_objects.TEST_DATASET_RECORD_ID,
            electricalproperties_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TRIAXIAL_TEST,
            triaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            triaxial_test_mock_objects.TEST_DATA,
            triaxial_test_mock_objects.TEST_DATASET_RECORD_ID,
            triaxial_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cappressure_mock_objects.TEST_DATA,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            cappressure_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.WETTABILITY_INDEX,
            wettability_index_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            wettability_index_mock_objects.TEST_DATA,
            wettability_index_mock_objects.TEST_DATASET_RECORD_ID,
            wettability_index_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TEC,
            tec_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            tec_data_mock_objects.TEST_DATA,
            tec_data_mock_objects.TEST_DATASET_RECORD_ID,
            tec_data_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.EDS_MAPPING,
            eds_mapping_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            eds_mapping_mock_objects.TEST_DATA,
            eds_mapping_mock_objects.TEST_DATASET_RECORD_ID,
            eds_mapping_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.XRF,
            xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            xrf_mock_objects.TEST_DATA,
            xrf_mock_objects.TEST_DATASET_RECORD_ID,
            xrf_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TENSILE_STRENGTH,
            tensile_strength_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            tensile_strength_mock_objects.TEST_DATA,
            tensile_strength_mock_objects.TEST_DATASET_RECORD_ID,
            tensile_strength_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.VITRINITE_REFLECTANCE,
            vitrinite_reflectance_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            vitrinite_reflectance_mock_objects.TEST_DATA,
            vitrinite_reflectance_mock_objects.TEST_DATASET_RECORD_ID,
            vitrinite_reflectance_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.XRD,
            xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            xrd_mock_objects.TEST_DATA,
            xrd_mock_objects.TEST_DATASET_RECORD_ID,
            xrd_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.PDP,
            pdp_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            pdp_mock_objects.TEST_DATA,
            pdp_mock_objects.TEST_DATASET_RECORD_ID,
            pdp_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.STO,
            sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            sto_mock_objects.TEST_DATA,
            sto_mock_objects.TEST_DATASET_RECORD_ID,
            sto_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
            crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            crushed_rock_analysis_mock_objects.TEST_DATA,
            crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            crushed_rock_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.MPFM_CALIBRATION,
            mpfm_calibration_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mpfm_calibration_mock_objects.TEST_DATA,
            mpfm_calibration_mock_objects.TEST_DATASET_RECORD_ID,
            mpfm_calibration_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.EOS,
            eos_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            eos_content_mock_objects.TEST_DATA,
            eos_content_mock_objects.TEST_DATASET_RECORD_ID,
            eos_content_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.COMPONENT_SCENARIO,
            component_scenario_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            component_scenario_mock_objects.TEST_DATA,
            component_scenario_mock_objects.TEST_DATASET_RECORD_ID,
            component_scenario_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.BLACK_OIL_TABLE,
            black_oil_table_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            black_oil_table_mock_objects.TEST_DATA,
            black_oil_table_mock_objects.TEST_DATASET_RECORD_ID,
            black_oil_table_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_data_json(data_endpoint_path, record_data, test_data, test_dataset_record_id, test_ddms_urn):
    with post_overrides(record_data, test_dataset_record_id, test_data):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=TEST_HEADERS_JSON,
                content=json.dumps(test_data),
            )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["ddms_urn"] == test_ddms_urn
    assert test_ddms_urn in record_data["data"]["DDMSDatasets"]


@pytest.mark.parametrize(
    "data_endpoint_path,record_data,test_data,test_dataset_record_id,test_ddms_urn",
    [
        (
            TestContentPathsApiV2.RCA,
            rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            rca_mock_objects.TEST_DATA,
            rca_mock_objects.TEST_DATASET_RECORD_ID,
            rca_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CCE,
            cce_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cce_mock_objects.TEST_DATA,
            cce_mock_objects.TEST_DATASET_RECORD_ID,
            cce_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.DIFF_LIB,
            diff_lib_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            diff_lib_mock_objects.TEST_DATA,
            diff_lib_mock_objects.TEST_DATASET_RECORD_ID,
            diff_lib_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TRANSPORT_TEST,
            transport_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            transport_test_mock_objects.TEST_DATA,
            transport_test_mock_objects.TEST_DATASET_RECORD_ID,
            transport_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS,
            compositional_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            compositional_analysis_mock_objects.TEST_DATA,
            compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            compositional_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MSS,
            mss_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mss_mock_objects.TEST_DATA,
            mss_mock_objects.TEST_DATASET_RECORD_ID,
            mss_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SWELLING,
            swelling_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            swelling_mock_objects.TEST_DATA,
            swelling_mock_objects.TEST_DATASET_RECORD_ID,
            swelling_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CVD,
            cvd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cvd_mock_objects.TEST_DATA,
            cvd_mock_objects.TEST_DATASET_RECORD_ID,
            cvd_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.WATER_ANALYSIS,
            water_analysis_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            water_analysis_data_mock_objects.TEST_DATA,
            water_analysis_data_mock_objects.TEST_DATASET_RECORD_ID,
            water_analysis_data_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.INTERFACIAL_TENSION,
            interfacial_tension_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            interfacial_tension_mock_objects.TEST_DATA,
            interfacial_tension_mock_objects.TEST_DATASET_RECORD_ID,
            interfacial_tension_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.VLE,
            vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            vle_mock_objects.TEST_DATA,
            vle_mock_objects.TEST_DATASET_RECORD_ID,
            vle_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MCM,
            mcm_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mcm_mock_objects.TEST_DATA,
            mcm_mock_objects.TEST_DATASET_RECORD_ID,
            mcm_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SLIMTUBE,
            slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            slimtube_mock_objects.TEST_DATA,
            slimtube_mock_objects.TEST_DATASET_RECORD_ID,
            slimtube_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.EXTRACTION,
            extraction_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            extraction_mock_objects.TEST_DATA,
            extraction_mock_objects.TEST_DATASET_RECORD_ID,
            extraction_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.FRACTIONATION,
            fractionation_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            fractionation_mock_objects.TEST_DATA,
            fractionation_mock_objects.TEST_DATASET_RECORD_ID,
            fractionation_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            relative_permeability_mock_objects.TEST_DATA,
            relative_permeability_mock_objects.TEST_DATASET_RECORD_ID,
            relative_permeability_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ROCK_COMPRESSIBILITY,
            rock_compressibility_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            rock_compressibility_mock_objects.TEST_DATA,
            rock_compressibility_mock_objects.TEST_DATASET_RECORD_ID,
            rock_compressibility_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.NMR,
            nmr_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            nmr_mock_objects.TEST_DATA,
            nmr_mock_objects.TEST_DATASET_RECORD_ID,
            nmr_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MULTIPLE_SALINITY,
            multiple_salinity_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            multiple_salinity_mock_objects.TEST_DATA,
            multiple_salinity_mock_objects.TEST_DATASET_RECORD_ID,
            multiple_salinity_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMS_ALKANES,
            gcms_alkanes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_alkanes_mock_objects.TEST_DATA,
            gcms_alkanes_mock_objects.TEST_DATASET_RECORD_ID,
            gcms_alkanes_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMS_AROMATICS,
            gcms_aromatics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_aromatics_mock_objects.TEST_DATA,
            gcms_aromatics_mock_objects.TEST_DATASET_RECORD_ID,
            gcms_aromatics_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMS_RATIOS,
            gcms_ratios_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_ratios_mock_objects.TEST_DATA,
            gcms_ratios_mock_objects.TEST_DATASET_RECORD_ID,
            gcms_ratios_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GAS_CHROMATOGRAPHY,
            gas_chromatography_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gas_chromatography_mock_objects.TEST_DATA,
            gas_chromatography_mock_objects.TEST_DATASET_RECORD_ID,
            gas_chromatography_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GAS_COMPOSITION,
            gas_composition_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gas_composition_mock_objects.TEST_DATA,
            gas_composition_mock_objects.TEST_DATASET_RECORD_ID,
            gas_composition_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ISOTOPE_ANALYSIS,
            isotope_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            isotope_analysis_mock_objects.TEST_DATA,
            isotope_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            isotope_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.BULK_PYROLYSIS,
            bulk_pyrolysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            bulk_pyrolysis_mock_objects.TEST_DATA,
            bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID,
            bulk_pyrolysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CORE_GAMMA,
            core_gamma_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            core_gamma_mock_objects.TEST_DATA,
            core_gamma_mock_objects.TEST_DATASET_RECORD_ID,
            core_gamma_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MINING_GEOTECH_LOGGING,
            mining_geotech_logging_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mining_geotech_logging_mock_objects.TEST_DATA,
            mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID,
            mining_geotech_logging_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.UNIAXIAL_TEST,
            uniaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            uniaxial_test_mock_objects.TEST_DATA,
            uniaxial_test_mock_objects.TEST_DATASET_RECORD_ID,
            uniaxial_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMSMS_ANALYSIS,
            gcmsms_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcmsms_analysis_mock_objects.TEST_DATA,
            gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            gcmsms_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CEC_CONTENT,
            cec_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cec_content_mock_objects.TEST_DATA,
            cec_content_mock_objects.TEST_DATASET_RECORD_ID,
            cec_content_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ELECTRICAL_PROPERTIES,
            electricalproperties_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            electricalproperties_mock_objects.TEST_DATA,
            electricalproperties_mock_objects.TEST_DATASET_RECORD_ID,
            electricalproperties_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TRIAXIAL_TEST,
            triaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            triaxial_test_mock_objects.TEST_DATA,
            triaxial_test_mock_objects.TEST_DATASET_RECORD_ID,
            triaxial_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cappressure_mock_objects.TEST_DATA,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            cappressure_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.WETTABILITY_INDEX,
            wettability_index_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            wettability_index_mock_objects.TEST_DATA,
            wettability_index_mock_objects.TEST_DATASET_RECORD_ID,
            wettability_index_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TEC,
            tec_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            tec_data_mock_objects.TEST_DATA,
            tec_data_mock_objects.TEST_DATASET_RECORD_ID,
            tec_data_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.EDS_MAPPING,
            eds_mapping_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            eds_mapping_mock_objects.TEST_DATA,
            eds_mapping_mock_objects.TEST_DATASET_RECORD_ID,
            eds_mapping_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.XRF,
            xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            xrf_mock_objects.TEST_DATA,
            xrf_mock_objects.TEST_DATASET_RECORD_ID,
            xrf_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TENSILE_STRENGTH,
            tensile_strength_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            tensile_strength_mock_objects.TEST_DATA,
            tensile_strength_mock_objects.TEST_DATASET_RECORD_ID,
            tensile_strength_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.VITRINITE_REFLECTANCE,
            vitrinite_reflectance_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            vitrinite_reflectance_mock_objects.TEST_DATA,
            vitrinite_reflectance_mock_objects.TEST_DATASET_RECORD_ID,
            vitrinite_reflectance_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.XRD,
            xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            xrd_mock_objects.TEST_DATA,
            xrd_mock_objects.TEST_DATASET_RECORD_ID,
            xrd_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.PDP,
            pdp_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            pdp_mock_objects.TEST_DATA,
            pdp_mock_objects.TEST_DATASET_RECORD_ID,
            pdp_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.STO,
            sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            sto_mock_objects.TEST_DATA,
            sto_mock_objects.TEST_DATASET_RECORD_ID,
            sto_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
            crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            crushed_rock_analysis_mock_objects.TEST_DATA,
            crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            crushed_rock_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.MPFM_CALIBRATION,
            mpfm_calibration_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mpfm_calibration_mock_objects.TEST_DATA,
            mpfm_calibration_mock_objects.TEST_DATASET_RECORD_ID,
            mpfm_calibration_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.EOS,
            eos_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            eos_content_mock_objects.TEST_DATA,
            eos_content_mock_objects.TEST_DATASET_RECORD_ID,
            eos_content_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.COMPONENT_SCENARIO,
            component_scenario_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            component_scenario_mock_objects.TEST_DATA,
            component_scenario_mock_objects.TEST_DATASET_RECORD_ID,
            component_scenario_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.BLACK_OIL_TABLE,
            black_oil_table_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            black_oil_table_mock_objects.TEST_DATA,
            black_oil_table_mock_objects.TEST_DATASET_RECORD_ID,
            black_oil_table_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_data_json_no_ddmsdatasets_field(
        data_endpoint_path, record_data, test_data, test_dataset_record_id, test_ddms_urn,
):
    del record_data["data"]["DDMSDatasets"]
    with post_overrides(record_data, test_dataset_record_id, test_data):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=TEST_HEADERS_JSON,
                content=json.dumps(test_data),
            )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["ddms_urn"] == test_ddms_urn
    assert test_ddms_urn in record_data["data"]["DDMSDatasets"]


@pytest.mark.parametrize(
    "data_endpoint_path,record_data,test_dataset_record_id",
    [
        (
            TestContentPathsApiV2.RCA,
            rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            rca_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.CCE,
            cce_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cce_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.DIFF_LIB,
            diff_lib_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            diff_lib_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.TRANSPORT_TEST,
            transport_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            transport_test_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS,
            compositional_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.MSS,
            mss_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mss_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.SWELLING,
            swelling_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            swelling_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.CVD,
            cvd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cvd_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.WATER_ANALYSIS,
            water_analysis_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            water_analysis_data_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.INTERFACIAL_TENSION,
            interfacial_tension_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            interfacial_tension_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.VLE,
            vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            vle_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.MCM,
            mcm_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mcm_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.SLIMTUBE,
            slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            slimtube_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.EXTRACTION,
            extraction_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            extraction_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.FRACTIONATION,
            fractionation_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            fractionation_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            relative_permeability_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.ROCK_COMPRESSIBILITY,
            rock_compressibility_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            rock_compressibility_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.NMR,
            nmr_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            nmr_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.MULTIPLE_SALINITY,
            multiple_salinity_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            multiple_salinity_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.GCMS_ALKANES,
            gcms_alkanes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_alkanes_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.GCMS_AROMATICS,
            gcms_aromatics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_aromatics_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.GCMS_RATIOS,
            gcms_ratios_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_ratios_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.GAS_CHROMATOGRAPHY,
            gas_chromatography_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gas_chromatography_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.GAS_COMPOSITION,
            gas_composition_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gas_composition_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.ISOTOPE_ANALYSIS,
            isotope_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            isotope_analysis_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.BULK_PYROLYSIS,
            bulk_pyrolysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.CORE_GAMMA,
            core_gamma_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            core_gamma_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.MINING_GEOTECH_LOGGING,
            mining_geotech_logging_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.UNIAXIAL_TEST,
            uniaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            uniaxial_test_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.GCMSMS_ANALYSIS,
            gcmsms_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.CEC_CONTENT,
            cec_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cec_content_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.ELECTRICAL_PROPERTIES,
            electricalproperties_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            electricalproperties_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.TRIAXIAL_TEST,
            triaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            triaxial_test_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.WETTABILITY_INDEX,
            wettability_index_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            wettability_index_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.TEC,
            tec_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            tec_data_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.EDS_MAPPING,
            eds_mapping_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            eds_mapping_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.XRF,
            xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            xrf_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.TENSILE_STRENGTH,
            tensile_strength_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            tensile_strength_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.VITRINITE_REFLECTANCE,
            vitrinite_reflectance_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            vitrinite_reflectance_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.XRD,
            xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            xrd_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.PDP,
            pdp_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            pdp_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.STO,
            sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            sto_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
            crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsPVTModel.MPFM_CALIBRATION,
            mpfm_calibration_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mpfm_calibration_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsPVTModel.EOS,
            eos_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            eos_content_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsPVTModel.COMPONENT_SCENARIO,
            component_scenario_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            component_scenario_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsPVTModel.BLACK_OIL_TABLE,
            black_oil_table_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            black_oil_table_mock_objects.TEST_DATASET_RECORD_ID,
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_data_parquet_empty(data_endpoint_path, record_data, test_dataset_record_id):
    with post_overrides(record_data, test_dataset_record_id):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=TEST_HEADERS_PARQUET,
                content=b"",
            )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize(
    "data_endpoint_path,record_data,test_data,test_dataset_record_id,test_ddms_urn",
    [
        (
            TestContentPathsApiV2.RCA,
            rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            rca_mock_objects.TEST_DATA,
            rca_mock_objects.TEST_DATASET_RECORD_ID,
            rca_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CCE,
            cce_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cce_mock_objects.TEST_DATA,
            cce_mock_objects.TEST_DATASET_RECORD_ID,
            cce_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.DIFF_LIB,
            diff_lib_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            diff_lib_mock_objects.TEST_DATA,
            diff_lib_mock_objects.TEST_DATASET_RECORD_ID,
            diff_lib_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TRANSPORT_TEST,
            transport_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            transport_test_mock_objects.TEST_DATA,
            transport_test_mock_objects.TEST_DATASET_RECORD_ID,
            transport_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS,
            compositional_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            compositional_analysis_mock_objects.TEST_DATA,
            compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            compositional_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MSS,
            mss_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mss_mock_objects.TEST_DATA,
            mss_mock_objects.TEST_DATASET_RECORD_ID,
            mss_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SWELLING,
            swelling_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            swelling_mock_objects.TEST_DATA,
            swelling_mock_objects.TEST_DATASET_RECORD_ID,
            swelling_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CVD,
            cvd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cvd_mock_objects.TEST_DATA,
            cvd_mock_objects.TEST_DATASET_RECORD_ID,
            cvd_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.WATER_ANALYSIS,
            water_analysis_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            water_analysis_data_mock_objects.TEST_DATA,
            water_analysis_data_mock_objects.TEST_DATASET_RECORD_ID,
            water_analysis_data_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.INTERFACIAL_TENSION,
            interfacial_tension_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            interfacial_tension_mock_objects.TEST_DATA,
            interfacial_tension_mock_objects.TEST_DATASET_RECORD_ID,
            interfacial_tension_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.VLE,
            vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            vle_mock_objects.TEST_DATA,
            vle_mock_objects.TEST_DATASET_RECORD_ID,
            vle_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MCM,
            mcm_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mcm_mock_objects.TEST_DATA,
            mcm_mock_objects.TEST_DATASET_RECORD_ID,
            mcm_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SLIMTUBE,
            slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            slimtube_mock_objects.TEST_DATA,
            slimtube_mock_objects.TEST_DATASET_RECORD_ID,
            slimtube_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.EXTRACTION,
            extraction_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            extraction_mock_objects.TEST_DATA,
            extraction_mock_objects.TEST_DATASET_RECORD_ID,
            extraction_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.FRACTIONATION,
            fractionation_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            fractionation_mock_objects.TEST_DATA,
            fractionation_mock_objects.TEST_DATASET_RECORD_ID,
            fractionation_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            relative_permeability_mock_objects.TEST_DATA,
            relative_permeability_mock_objects.TEST_DATASET_RECORD_ID,
            relative_permeability_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ROCK_COMPRESSIBILITY,
            rock_compressibility_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            rock_compressibility_mock_objects.TEST_DATA,
            rock_compressibility_mock_objects.TEST_DATASET_RECORD_ID,
            rock_compressibility_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.NMR,
            nmr_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            nmr_mock_objects.TEST_DATA,
            nmr_mock_objects.TEST_DATASET_RECORD_ID,
            nmr_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MULTIPLE_SALINITY,
            multiple_salinity_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            multiple_salinity_mock_objects.TEST_DATA,
            multiple_salinity_mock_objects.TEST_DATASET_RECORD_ID,
            multiple_salinity_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMS_ALKANES,
            gcms_alkanes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_alkanes_mock_objects.TEST_DATA,
            gcms_alkanes_mock_objects.TEST_DATASET_RECORD_ID,
            gcms_alkanes_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMS_AROMATICS,
            gcms_aromatics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_aromatics_mock_objects.TEST_DATA,
            gcms_aromatics_mock_objects.TEST_DATASET_RECORD_ID,
            gcms_aromatics_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMS_RATIOS,
            gcms_ratios_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_ratios_mock_objects.TEST_DATA,
            gcms_ratios_mock_objects.TEST_DATASET_RECORD_ID,
            gcms_ratios_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GAS_CHROMATOGRAPHY,
            gas_chromatography_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gas_chromatography_mock_objects.TEST_DATA,
            gas_chromatography_mock_objects.TEST_DATASET_RECORD_ID,
            gas_chromatography_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GAS_COMPOSITION,
            gas_composition_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gas_composition_mock_objects.TEST_DATA,
            gas_composition_mock_objects.TEST_DATASET_RECORD_ID,
            gas_composition_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ISOTOPE_ANALYSIS,
            isotope_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            isotope_analysis_mock_objects.TEST_DATA,
            isotope_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            isotope_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.BULK_PYROLYSIS,
            bulk_pyrolysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            bulk_pyrolysis_mock_objects.TEST_DATA,
            bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID,
            bulk_pyrolysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CORE_GAMMA,
            core_gamma_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            core_gamma_mock_objects.TEST_DATA,
            core_gamma_mock_objects.TEST_DATASET_RECORD_ID,
            core_gamma_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MINING_GEOTECH_LOGGING,
            mining_geotech_logging_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mining_geotech_logging_mock_objects.TEST_DATA,
            mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID,
            mining_geotech_logging_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.UNIAXIAL_TEST,
            uniaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            uniaxial_test_mock_objects.TEST_DATA,
            uniaxial_test_mock_objects.TEST_DATASET_RECORD_ID,
            uniaxial_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMSMS_ANALYSIS,
            gcmsms_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcmsms_analysis_mock_objects.TEST_DATA,
            gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            gcmsms_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CEC_CONTENT,
            cec_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cec_content_mock_objects.TEST_DATA,
            cec_content_mock_objects.TEST_DATASET_RECORD_ID,
            cec_content_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ELECTRICAL_PROPERTIES,
            electricalproperties_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            electricalproperties_mock_objects.TEST_DATA,
            electricalproperties_mock_objects.TEST_DATASET_RECORD_ID,
            electricalproperties_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TRIAXIAL_TEST,
            triaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            triaxial_test_mock_objects.TEST_DATA,
            triaxial_test_mock_objects.TEST_DATASET_RECORD_ID,
            triaxial_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cappressure_mock_objects.TEST_DATA,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            cappressure_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.WETTABILITY_INDEX,
            wettability_index_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            wettability_index_mock_objects.TEST_DATA,
            wettability_index_mock_objects.TEST_DATASET_RECORD_ID,
            wettability_index_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TEC,
            tec_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            tec_data_mock_objects.TEST_DATA,
            tec_data_mock_objects.TEST_DATASET_RECORD_ID,
            tec_data_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.EDS_MAPPING,
            eds_mapping_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            eds_mapping_mock_objects.TEST_DATA,
            eds_mapping_mock_objects.TEST_DATASET_RECORD_ID,
            eds_mapping_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.XRF,
            xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            xrf_mock_objects.TEST_DATA,
            xrf_mock_objects.TEST_DATASET_RECORD_ID,
            xrf_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TENSILE_STRENGTH,
            tensile_strength_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            tensile_strength_mock_objects.TEST_DATA,
            tensile_strength_mock_objects.TEST_DATASET_RECORD_ID,
            tensile_strength_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.VITRINITE_REFLECTANCE,
            vitrinite_reflectance_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            vitrinite_reflectance_mock_objects.TEST_DATA,
            vitrinite_reflectance_mock_objects.TEST_DATASET_RECORD_ID,
            vitrinite_reflectance_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.XRD,
            xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            xrd_mock_objects.TEST_DATA,
            xrd_mock_objects.TEST_DATASET_RECORD_ID,
            xrd_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.PDP,
            pdp_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            pdp_mock_objects.TEST_DATA,
            pdp_mock_objects.TEST_DATASET_RECORD_ID,
            pdp_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.STO,
            sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            sto_mock_objects.TEST_DATA,
            sto_mock_objects.TEST_DATASET_RECORD_ID,
            sto_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
            crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            crushed_rock_analysis_mock_objects.TEST_DATA,
            crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            crushed_rock_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.MPFM_CALIBRATION,
            mpfm_calibration_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mpfm_calibration_mock_objects.TEST_DATA,
            mpfm_calibration_mock_objects.TEST_DATASET_RECORD_ID,
            mpfm_calibration_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.EOS,
            eos_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            eos_content_mock_objects.TEST_DATA,
            eos_content_mock_objects.TEST_DATASET_RECORD_ID,
            eos_content_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.COMPONENT_SCENARIO,
            component_scenario_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            component_scenario_mock_objects.TEST_DATA,
            component_scenario_mock_objects.TEST_DATASET_RECORD_ID,
            component_scenario_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.BLACK_OIL_TABLE,
            black_oil_table_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            black_oil_table_mock_objects.TEST_DATA,
            black_oil_table_mock_objects.TEST_DATASET_RECORD_ID,
            black_oil_table_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_data_parquet(data_endpoint_path, record_data, test_data, test_dataset_record_id, test_ddms_urn):
    dataframe = pd.DataFrame(test_data["data"], columns=test_data["columns"])

    with post_overrides(record_data, test_dataset_record_id, dataframe):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=TEST_HEADERS_PARQUET,
                content=dataframe.to_parquet(),
            )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["ddms_urn"] == test_ddms_urn
    assert test_ddms_urn in record_data["data"]["DDMSDatasets"]


@pytest.mark.parametrize(
    "data_endpoint_path,record_data,test_data,test_dataset_record_id,test_ddms_urn",
    [
        (
            TestContentPathsApiV2.RCA,
            rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            rca_mock_objects.TEST_DATA,
            rca_mock_objects.TEST_DATASET_RECORD_ID,
            rca_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CCE,
            cce_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cce_mock_objects.TEST_DATA,
            cce_mock_objects.TEST_DATASET_RECORD_ID,
            cce_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.DIFF_LIB,
            diff_lib_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            diff_lib_mock_objects.TEST_DATA,
            diff_lib_mock_objects.TEST_DATASET_RECORD_ID,
            diff_lib_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TRANSPORT_TEST,
            transport_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            transport_test_mock_objects.TEST_DATA,
            transport_test_mock_objects.TEST_DATASET_RECORD_ID,
            transport_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS,
            compositional_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            compositional_analysis_mock_objects.TEST_DATA,
            compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            compositional_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MSS,
            mss_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mss_mock_objects.TEST_DATA,
            mss_mock_objects.TEST_DATASET_RECORD_ID,
            mss_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SWELLING,
            swelling_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            swelling_mock_objects.TEST_DATA,
            swelling_mock_objects.TEST_DATASET_RECORD_ID,
            swelling_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CVD,
            cvd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cvd_mock_objects.TEST_DATA,
            cvd_mock_objects.TEST_DATASET_RECORD_ID,
            cvd_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.WATER_ANALYSIS,
            water_analysis_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            water_analysis_data_mock_objects.TEST_DATA,
            water_analysis_data_mock_objects.TEST_DATASET_RECORD_ID,
            water_analysis_data_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.INTERFACIAL_TENSION,
            interfacial_tension_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            interfacial_tension_mock_objects.TEST_DATA,
            interfacial_tension_mock_objects.TEST_DATASET_RECORD_ID,
            interfacial_tension_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.VLE,
            vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            vle_mock_objects.TEST_DATA,
            vle_mock_objects.TEST_DATASET_RECORD_ID,
            vle_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MCM,
            mcm_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mcm_mock_objects.TEST_DATA,
            mcm_mock_objects.TEST_DATASET_RECORD_ID,
            mcm_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SLIMTUBE,
            slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            slimtube_mock_objects.TEST_DATA,
            slimtube_mock_objects.TEST_DATASET_RECORD_ID,
            slimtube_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.EXTRACTION,
            extraction_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            extraction_mock_objects.TEST_DATA,
            extraction_mock_objects.TEST_DATASET_RECORD_ID,
            extraction_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.FRACTIONATION,
            fractionation_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            fractionation_mock_objects.TEST_DATA,
            fractionation_mock_objects.TEST_DATASET_RECORD_ID,
            fractionation_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            relative_permeability_mock_objects.TEST_DATA,
            relative_permeability_mock_objects.TEST_DATASET_RECORD_ID,
            relative_permeability_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ROCK_COMPRESSIBILITY,
            rock_compressibility_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            rock_compressibility_mock_objects.TEST_DATA,
            rock_compressibility_mock_objects.TEST_DATASET_RECORD_ID,
            rock_compressibility_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.NMR,
            nmr_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            nmr_mock_objects.TEST_DATA,
            nmr_mock_objects.TEST_DATASET_RECORD_ID,
            nmr_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MULTIPLE_SALINITY,
            multiple_salinity_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            multiple_salinity_mock_objects.TEST_DATA,
            multiple_salinity_mock_objects.TEST_DATASET_RECORD_ID,
            multiple_salinity_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMS_ALKANES,
            gcms_alkanes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_alkanes_mock_objects.TEST_DATA,
            gcms_alkanes_mock_objects.TEST_DATASET_RECORD_ID,
            gcms_alkanes_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMS_AROMATICS,
            gcms_aromatics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_aromatics_mock_objects.TEST_DATA,
            gcms_aromatics_mock_objects.TEST_DATASET_RECORD_ID,
            gcms_aromatics_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMS_RATIOS,
            gcms_ratios_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcms_ratios_mock_objects.TEST_DATA,
            gcms_ratios_mock_objects.TEST_DATASET_RECORD_ID,
            gcms_ratios_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GAS_CHROMATOGRAPHY,
            gas_chromatography_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gas_chromatography_mock_objects.TEST_DATA,
            gas_chromatography_mock_objects.TEST_DATASET_RECORD_ID,
            gas_chromatography_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GAS_COMPOSITION,
            gas_composition_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gas_composition_mock_objects.TEST_DATA,
            gas_composition_mock_objects.TEST_DATASET_RECORD_ID,
            gas_composition_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ISOTOPE_ANALYSIS,
            isotope_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            isotope_analysis_mock_objects.TEST_DATA,
            isotope_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            isotope_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.BULK_PYROLYSIS,
            bulk_pyrolysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            bulk_pyrolysis_mock_objects.TEST_DATA,
            bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID,
            bulk_pyrolysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CORE_GAMMA,
            core_gamma_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            core_gamma_mock_objects.TEST_DATA,
            core_gamma_mock_objects.TEST_DATASET_RECORD_ID,
            core_gamma_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.MINING_GEOTECH_LOGGING,
            mining_geotech_logging_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mining_geotech_logging_mock_objects.TEST_DATA,
            mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID,
            mining_geotech_logging_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.UNIAXIAL_TEST,
            uniaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            uniaxial_test_mock_objects.TEST_DATA,
            uniaxial_test_mock_objects.TEST_DATASET_RECORD_ID,
            uniaxial_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.GCMSMS_ANALYSIS,
            gcmsms_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            gcmsms_analysis_mock_objects.TEST_DATA,
            gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            gcmsms_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CEC_CONTENT,
            cec_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cec_content_mock_objects.TEST_DATA,
            cec_content_mock_objects.TEST_DATASET_RECORD_ID,
            cec_content_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ELECTRICAL_PROPERTIES,
            electricalproperties_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            electricalproperties_mock_objects.TEST_DATA,
            electricalproperties_mock_objects.TEST_DATASET_RECORD_ID,
            electricalproperties_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TRIAXIAL_TEST,
            triaxial_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            triaxial_test_mock_objects.TEST_DATA,
            triaxial_test_mock_objects.TEST_DATASET_RECORD_ID,
            triaxial_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cappressure_mock_objects.TEST_DATA,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            cappressure_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.WETTABILITY_INDEX,
            wettability_index_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            wettability_index_mock_objects.TEST_DATA,
            wettability_index_mock_objects.TEST_DATASET_RECORD_ID,
            wettability_index_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TEC,
            tec_data_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            tec_data_mock_objects.TEST_DATA,
            tec_data_mock_objects.TEST_DATASET_RECORD_ID,
            tec_data_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.EDS_MAPPING,
            eds_mapping_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            eds_mapping_mock_objects.TEST_DATA,
            eds_mapping_mock_objects.TEST_DATASET_RECORD_ID,
            eds_mapping_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.XRF,
            xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            xrf_mock_objects.TEST_DATA,
            xrf_mock_objects.TEST_DATASET_RECORD_ID,
            xrf_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.TENSILE_STRENGTH,
            tensile_strength_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            tensile_strength_mock_objects.TEST_DATA,
            tensile_strength_mock_objects.TEST_DATASET_RECORD_ID,
            tensile_strength_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.VITRINITE_REFLECTANCE,
            vitrinite_reflectance_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            vitrinite_reflectance_mock_objects.TEST_DATA,
            vitrinite_reflectance_mock_objects.TEST_DATASET_RECORD_ID,
            vitrinite_reflectance_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.XRD,
            xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            xrd_mock_objects.TEST_DATA,
            xrd_mock_objects.TEST_DATASET_RECORD_ID,
            xrd_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.PDP,
            pdp_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            pdp_mock_objects.TEST_DATA,
            pdp_mock_objects.TEST_DATASET_RECORD_ID,
            pdp_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.STO,
            sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            sto_mock_objects.TEST_DATA,
            sto_mock_objects.TEST_DATASET_RECORD_ID,
            sto_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
            crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            crushed_rock_analysis_mock_objects.TEST_DATA,
            crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            crushed_rock_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.MPFM_CALIBRATION,
            mpfm_calibration_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            mpfm_calibration_mock_objects.TEST_DATA,
            mpfm_calibration_mock_objects.TEST_DATASET_RECORD_ID,
            mpfm_calibration_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.EOS,
            eos_content_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            eos_content_mock_objects.TEST_DATA,
            eos_content_mock_objects.TEST_DATASET_RECORD_ID,
            eos_content_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.COMPONENT_SCENARIO,
            component_scenario_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            component_scenario_mock_objects.TEST_DATA,
            component_scenario_mock_objects.TEST_DATASET_RECORD_ID,
            component_scenario_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsPVTModel.BLACK_OIL_TABLE,
            black_oil_table_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            black_oil_table_mock_objects.TEST_DATA,
            black_oil_table_mock_objects.TEST_DATASET_RECORD_ID,
            black_oil_table_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_data_new_dataset(data_endpoint_path, record_data, test_data, test_dataset_record_id, test_ddms_urn):
    with post_overrides(record_data, test_dataset_record_id, test_data):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=TEST_HEADERS_JSON,
                content=json.dumps(test_data),
            )
            body = response.json()

    assert body["ddms_urn"] == test_ddms_urn


@pytest.mark.parametrize(
    "data_endpoint_path, incorrect_schema_test_data", [
        (TestContentPathsApiV2.RCA, rca_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.CCE, cce_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.DIFF_LIB, diff_lib_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.TRANSPORT_TEST, transport_test_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS, compositional_analysis_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.MSS, mss_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.SWELLING, swelling_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.CVD, cvd_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.WATER_ANALYSIS, water_analysis_data_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.INTERFACIAL_TENSION, interfacial_tension_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.VLE, vle_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.MCM, mcm_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.SLIMTUBE, slimtube_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.EXTRACTION, extraction_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.FRACTIONATION, fractionation_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.RELATIVE_PERMEABILITY, relative_permeability_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.ROCK_COMPRESSIBILITY, rock_compressibility_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.NMR, nmr_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.MULTIPLE_SALINITY, multiple_salinity_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.GCMS_ALKANES, gcms_alkanes_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.GCMS_AROMATICS, gcms_aromatics_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.GCMS_RATIOS, gcms_ratios_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.GAS_CHROMATOGRAPHY, gas_chromatography_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.GAS_COMPOSITION, gas_composition_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.ISOTOPE_ANALYSIS, isotope_analysis_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.BULK_PYROLYSIS, bulk_pyrolysis_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.CORE_GAMMA, core_gamma_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.MINING_GEOTECH_LOGGING, mining_geotech_logging_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.UNIAXIAL_TEST, uniaxial_test_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.GCMSMS_ANALYSIS, gcmsms_analysis_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.CEC_CONTENT, cec_content_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.ELECTRICAL_PROPERTIES, electricalproperties_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.TRIAXIAL_TEST, triaxial_test_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.CAP_PRESSURE, cappressure_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.WETTABILITY_INDEX, wettability_index_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.TEC, tec_data_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.EDS_MAPPING, eds_mapping_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.XRF, xrf_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.TENSILE_STRENGTH, tensile_strength_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.VITRINITE_REFLECTANCE, vitrinite_reflectance_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.XRD, xrd_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.PDP, pdp_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.STO, sto_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS, crushed_rock_analysis_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
    ],
)
@pytest.mark.asyncio
async def test_post_data_validation_error(data_endpoint_path, incorrect_schema_test_data):
    with post_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=TEST_HEADERS_JSON,
                content=json.dumps(incorrect_schema_test_data),
            )

    body = response.json()
    assert ["code", "reason", "errors"] == list(body.keys())
    assert body["reason"] == "Data validation failed."
    reason = body["errors"]
    assert isinstance(reason, dict)
    assert len(reason) == 1
    assert set(reason.keys()) == {"Invalid type"}


@pytest.mark.parametrize(
    "data_endpoint_path,incorrect_dataframe_data,error_reason", [
        (
            TestContentPathsApiV2.RCA,
            rca_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            rca_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.CCE,
            cce_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            cce_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.DIFF_LIB,
            diff_lib_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            diff_lib_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.TRANSPORT_TEST,
            transport_test_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            transport_test_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS,
            compositional_analysis_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            compositional_analysis_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.MSS,
            mss_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            mss_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.SWELLING,
            swelling_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            swelling_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.CVD,
            cvd_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            cvd_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.WATER_ANALYSIS,
            water_analysis_data_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            water_analysis_data_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.INTERFACIAL_TENSION,
            interfacial_tension_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            interfacial_tension_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.VLE,
            vle_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            vle_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.MCM,
            mcm_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            mcm_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.SLIMTUBE,
            slimtube_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            slimtube_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.EXTRACTION,
            extraction_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            extraction_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.FRACTIONATION,
            fractionation_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            fractionation_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            relative_permeability_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.ROCK_COMPRESSIBILITY,
            rock_compressibility_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            rock_compressibility_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.NMR,
            nmr_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            nmr_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.MULTIPLE_SALINITY,
            multiple_salinity_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            multiple_salinity_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.GCMS_ALKANES,
            gcms_alkanes_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            gcms_alkanes_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.GCMS_AROMATICS,
            gcms_aromatics_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            gcms_aromatics_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.GCMS_RATIOS,
            gcms_ratios_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            gcms_ratios_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.GAS_CHROMATOGRAPHY,
            gas_chromatography_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            gas_chromatography_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.GAS_COMPOSITION,
            gas_composition_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            gas_composition_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.ISOTOPE_ANALYSIS,
            isotope_analysis_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            isotope_analysis_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.BULK_PYROLYSIS,
            bulk_pyrolysis_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            bulk_pyrolysis_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.CORE_GAMMA,
            core_gamma_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            core_gamma_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.MINING_GEOTECH_LOGGING,
            mining_geotech_logging_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            mining_geotech_logging_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.UNIAXIAL_TEST,
            uniaxial_test_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            uniaxial_test_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.GCMSMS_ANALYSIS,
            gcmsms_analysis_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            gcmsms_analysis_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.CEC_CONTENT,
            cec_content_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            cec_content_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.ELECTRICAL_PROPERTIES,
            electricalproperties_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            electricalproperties_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.TRIAXIAL_TEST,
            triaxial_test_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            triaxial_test_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            cappressure_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.WETTABILITY_INDEX,
            wettability_index_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            wettability_index_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.TEC,
            tec_data_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            tec_data_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.EDS_MAPPING,
            eds_mapping_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            eds_mapping_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.XRF,
            xrf_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            xrf_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.TENSILE_STRENGTH,
            tensile_strength_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            tensile_strength_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.VITRINITE_REFLECTANCE,
            vitrinite_reflectance_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            vitrinite_reflectance_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.XRD,
            xrd_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            xrd_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.PDP,
            pdp_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            pdp_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.STO,
            sto_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            sto_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
            crushed_rock_analysis_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            crushed_rock_analysis_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsPVTModel.MPFM_CALIBRATION,
            mpfm_calibration_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            mpfm_calibration_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsPVTModel.EOS,
            eos_content_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            eos_content_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsPVTModel.COMPONENT_SCENARIO,
            component_scenario_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            component_scenario_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsPVTModel.BLACK_OIL_TABLE,
            black_oil_table_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            black_oil_table_mock_objects.EXPECTED_ERROR_REASON,
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_invalid_df_error(data_endpoint_path, incorrect_dataframe_data, error_reason):
    with post_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=TEST_HEADERS_JSON,
                content=json.dumps(incorrect_dataframe_data),
            )

    body = response.json()
    assert ["code", "reason"] == list(body.keys())
    assert body["reason"] == error_reason


@pytest.mark.parametrize(
    "data_endpoint_path", [
        f"{TestContentPathsApiV2.RCA}/{rca_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.CCE}/{cce_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.DIFF_LIB}/{diff_lib_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.TRANSPORT_TEST}/{transport_test_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS}/{compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.MSS}/{mss_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.SWELLING}/{swelling_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.CVD}/{cvd_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.WATER_ANALYSIS}/{water_analysis_data_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.INTERFACIAL_TENSION}/{interfacial_tension_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.VLE}/{vle_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.MCM}/{mcm_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.SLIMTUBE}/{slimtube_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.EXTRACTION}/{extraction_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.FRACTIONATION}/{fractionation_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.RELATIVE_PERMEABILITY}/{relative_permeability_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.ROCK_COMPRESSIBILITY}/{rock_compressibility_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.NMR}/{nmr_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.MULTIPLE_SALINITY}/{multiple_salinity_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.GCMS_ALKANES}/{gcms_alkanes_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.GCMS_AROMATICS}/{gcms_aromatics_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.GCMS_RATIOS}/{gcms_ratios_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.GAS_CHROMATOGRAPHY}/{gas_chromatography_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.GAS_COMPOSITION}/{gas_composition_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotope_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.BULK_PYROLYSIS}/{bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.CORE_GAMMA}/{core_gamma_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.MINING_GEOTECH_LOGGING}/{mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.GCMSMS_ANALYSIS}/{gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.CEC_CONTENT}/{cec_content_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.ELECTRICAL_PROPERTIES}/{electricalproperties_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_test_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.CAP_PRESSURE}/{cappressure_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.WETTABILITY_INDEX}/{wettability_index_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.TEC}/{tec_data_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.EDS_MAPPING}/{eds_mapping_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.XRF}/{xrf_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.TENSILE_STRENGTH}/{tensile_strength_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.VITRINITE_REFLECTANCE}/{vitrinite_reflectance_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.XRD}/{xrd_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.PDP}/{pdp_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.STO}/{sto_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS}/{crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsPVTModel.MPFM_CALIBRATION}/{mpfm_calibration_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsPVTModel.EOS}/{eos_content_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsPVTModel.COMPONENT_SCENARIO}/{component_scenario_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsPVTModel.BLACK_OIL_TABLE}/{black_oil_table_mock_objects.TEST_DATASET_RECORD_ID}",
    ],
)
@pytest.mark.asyncio
async def test_get_403(data_endpoint_path):
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.get(
            data_endpoint_path,
            headers=TEST_HEADERS_NO_AUTH,
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    "data_endpoint_path", [
        TestContentPathsApiV2.RCA,
        TestContentPathsApiV2.CCE,
        TestContentPathsApiV2.DIFF_LIB,
        TestContentPathsApiV2.TRANSPORT_TEST,
        TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS,
        TestContentPathsApiV2.MSS,
        TestContentPathsApiV2.SWELLING,
        TestContentPathsApiV2.CVD,
        TestContentPathsApiV2.WATER_ANALYSIS,
        TestContentPathsApiV2.INTERFACIAL_TENSION,
        TestContentPathsApiV2.VLE,
        TestContentPathsApiV2.MCM,
        TestContentPathsApiV2.SLIMTUBE,
        TestContentPathsApiV2.EXTRACTION,
        TestContentPathsApiV2.FRACTIONATION,
        TestContentPathsApiV2.RELATIVE_PERMEABILITY,
        TestContentPathsApiV2.ROCK_COMPRESSIBILITY,
        TestContentPathsApiV2.NMR,
        TestContentPathsApiV2.MULTIPLE_SALINITY,
        TestContentPathsApiV2.GCMS_ALKANES,
        TestContentPathsApiV2.GCMS_AROMATICS,
        TestContentPathsApiV2.GCMS_RATIOS,
        TestContentPathsApiV2.GAS_CHROMATOGRAPHY,
        TestContentPathsApiV2.GAS_COMPOSITION,
        TestContentPathsApiV2.ISOTOPE_ANALYSIS,
        TestContentPathsApiV2.BULK_PYROLYSIS,
        TestContentPathsApiV2.CORE_GAMMA,
        TestContentPathsApiV2.MINING_GEOTECH_LOGGING,
        TestContentPathsApiV2.UNIAXIAL_TEST,
        TestContentPathsApiV2.GCMSMS_ANALYSIS,
        TestContentPathsApiV2.CEC_CONTENT,
        TestContentPathsApiV2.ELECTRICAL_PROPERTIES,
        TestContentPathsApiV2.TRIAXIAL_TEST,
        TestContentPathsApiV2.CAP_PRESSURE,
        TestContentPathsApiV2.WETTABILITY_INDEX,
        TestContentPathsApiV2.TEC,
        TestContentPathsApiV2.EDS_MAPPING,
        TestContentPathsApiV2.XRF,
        TestContentPathsApiV2.TENSILE_STRENGTH,
        TestContentPathsApiV2.VITRINITE_REFLECTANCE,
        TestContentPathsApiV2.XRD,
        TestContentPathsApiV2.PDP,
        TestContentPathsApiV2.STO,
        TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
        TestContentPathsPVTModel.MPFM_CALIBRATION,
        TestContentPathsPVTModel.EOS,
        TestContentPathsPVTModel.COMPONENT_SCENARIO,
        TestContentPathsPVTModel.BLACK_OIL_TABLE,
    ],
)
@pytest.mark.asyncio
async def test_post_403(data_endpoint_path):
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.post(
            data_endpoint_path,
            headers=TEST_HEADERS_NO_AUTH,
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    "data_endpoint_path,integrity_error_dataframe_data,missed_records", [
        (
            TestContentPathsApiV2.RCA, rca_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(rca_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.CCE, cce_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(cce_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.DIFF_LIB, diff_lib_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(diff_lib_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.TRANSPORT_TEST, transport_test_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(transport_test_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS, compositional_analysis_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(compositional_analysis_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.MSS, mss_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(mss_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.SWELLING, swelling_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(swelling_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.CVD, cvd_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(cvd_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.WATER_ANALYSIS, water_analysis_data_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(water_analysis_data_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.INTERFACIAL_TENSION, interfacial_tension_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(interfacial_tension_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.VLE, vle_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(vle_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.MCM, mcm_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(mcm_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.SLIMTUBE, slimtube_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(slimtube_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.EXTRACTION, extraction_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(extraction_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.FRACTIONATION, fractionation_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(fractionation_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.RELATIVE_PERMEABILITY, relative_permeability_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(relative_permeability_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.ROCK_COMPRESSIBILITY, rock_compressibility_mock_objects.TEST_DATA, list(
                find_osdu_ids_from_string(json.dumps(rock_compressibility_mock_objects.TEST_DATA)),
            ),
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_integrity_error(data_endpoint_path, integrity_error_dataframe_data, missed_records, with_patched_storage_failed_integrity_validation):
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=TEST_HEADERS_JSON,
                content=json.dumps(integrity_error_dataframe_data),
            )

    body = response.json()
    assert ["code", "reason", "errors"] == list(body.keys())
    assert body["reason"] == "Data validation failed."
    errors = body["errors"]
    assert errors.get("Missing records in storage", []).sort() == missed_records.sort()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        TestContentPathsApiV2.RCA,
        TestContentPathsApiV2.CCE,
        TestContentPathsApiV2.DIFF_LIB,
        TestContentPathsApiV2.TRANSPORT_TEST,
        TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS,
        TestContentPathsApiV2.MSS,
        TestContentPathsApiV2.SWELLING,
        TestContentPathsApiV2.CVD,
        TestContentPathsApiV2.WATER_ANALYSIS,
        TestContentPathsApiV2.INTERFACIAL_TENSION,
        TestContentPathsApiV2.VLE,
        TestContentPathsApiV2.MCM,
        TestContentPathsApiV2.SLIMTUBE,
        TestContentPathsApiV2.EXTRACTION,
        TestContentPathsApiV2.FRACTIONATION,
        TestContentPathsApiV2.RELATIVE_PERMEABILITY,
        TestContentPathsApiV2.ROCK_COMPRESSIBILITY,
        TestContentPathsApiV2.NMR,
        TestContentPathsApiV2.MULTIPLE_SALINITY,
        TestContentPathsApiV2.GCMS_ALKANES,
        TestContentPathsApiV2.GCMS_AROMATICS,
        TestContentPathsApiV2.GCMS_RATIOS,
        TestContentPathsApiV2.GAS_CHROMATOGRAPHY,
        TestContentPathsApiV2.GAS_COMPOSITION,
        TestContentPathsApiV2.ISOTOPE_ANALYSIS,
        TestContentPathsApiV2.BULK_PYROLYSIS,
        TestContentPathsApiV2.CORE_GAMMA,
        TestContentPathsApiV2.MINING_GEOTECH_LOGGING,
        TestContentPathsApiV2.UNIAXIAL_TEST,
        TestContentPathsApiV2.GCMSMS_ANALYSIS,
        TestContentPathsApiV2.CEC_CONTENT,
        TestContentPathsApiV2.ELECTRICAL_PROPERTIES,
        TestContentPathsApiV2.TRIAXIAL_TEST,
        TestContentPathsApiV2.CAP_PRESSURE,
        TestContentPathsApiV2.WETTABILITY_INDEX,
        TestContentPathsApiV2.TEC,
        TestContentPathsApiV2.EDS_MAPPING,
        TestContentPathsApiV2.XRF,
        TestContentPathsApiV2.TENSILE_STRENGTH,
        TestContentPathsApiV2.VITRINITE_REFLECTANCE,
        TestContentPathsApiV2.XRD,
        TestContentPathsApiV2.PDP,
        TestContentPathsApiV2.STO,
        TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
        TestContentPathsPVTModel.MPFM_CALIBRATION,
        TestContentPathsPVTModel.EOS,
        TestContentPathsPVTModel.COMPONENT_SCENARIO,
        TestContentPathsPVTModel.BLACK_OIL_TABLE,
    ],
)
async def test_invalid_data_with_nan(path):
    with post_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                path,
                headers=TEST_HEADERS_JSON,
                content=json.dumps(INVALID_DATA_WITH_NAN),
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    body = response.json()
    assert ["code", "reason", "errors"] == list(body.keys())
    assert body["reason"] == "Data validation failed."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,payloads",
    [
        (TestContentPathsApiV2.RCA, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.CCE, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.DIFF_LIB, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.TRANSPORT_TEST, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.MSS, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.SWELLING, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.CVD, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.WATER_ANALYSIS, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.INTERFACIAL_TENSION, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.VLE, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.MCM, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.SLIMTUBE, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.EXTRACTION, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.FRACTIONATION, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.RELATIVE_PERMEABILITY, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.ROCK_COMPRESSIBILITY, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.NMR, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.MULTIPLE_SALINITY, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.GCMS_ALKANES, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.GCMS_AROMATICS, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.GCMS_RATIOS, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.GAS_CHROMATOGRAPHY, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.GAS_COMPOSITION, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.ISOTOPE_ANALYSIS, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.BULK_PYROLYSIS, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.CORE_GAMMA, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.MINING_GEOTECH_LOGGING, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.UNIAXIAL_TEST, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.GCMSMS_ANALYSIS, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.CEC_CONTENT, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.ELECTRICAL_PROPERTIES, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.TRIAXIAL_TEST, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.CAP_PRESSURE, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.WETTABILITY_INDEX, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.TEC, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.EDS_MAPPING, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.XRF, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.TENSILE_STRENGTH, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.VITRINITE_REFLECTANCE, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.XRD, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.PDP, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.STO, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsPVTModel.MPFM_CALIBRATION, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsPVTModel.EOS, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsPVTModel.COMPONENT_SCENARIO, ORIENT_SPLIT_400_PAYLOADS),
        (TestContentPathsPVTModel.BLACK_OIL_TABLE, ORIENT_SPLIT_400_PAYLOADS),
    ],
)
async def test_invalid_data_json_payload(path, payloads):
    for payload in payloads:
        with post_overrides():
            async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                response = await client.post(
                    path,
                    headers=TEST_HEADERS_JSON,
                    content=json.dumps(payload),
                )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        body = response.json()

        assert ["code", "reason"] == list(body.keys())
        assert body["reason"].startswith("Data error:")
