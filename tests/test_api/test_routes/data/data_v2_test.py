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

import copy as _copy
import io
import json
from contextlib import contextmanager
from datetime import date
from unittest.mock import AsyncMock, create_autospec, patch

import pandas as pd
import pyarrow as pa
import pytest
from httpx import AsyncClient
from pyarrow import parquet as pq
from starlette import status

from app.api.dependencies.services import (
    get_async_dataset_service,
    get_async_entitlements_service,
    get_async_storage_service,
)
from app.api.routes.utils.query import find_osdu_ids_from_string
from app.api.routes.utils.records import get_id, get_id_version
from app.main import app
from app.services import dataset, entitlements, storage
from tests.test_api.test_routes import dependencies
from tests.test_api.test_routes.api_v2.atm_flash_compositional_analysis import (
    atmospheric_flash_mock_objects,
    compositional_analysis_mock_objects,
)
from tests.test_api.test_routes.api_v2.bulk_pyrolysis import (
    bulk_pyrolysis_mock_objects,
)
from tests.test_api.test_routes.api_v2.capillary_suction_time import (
    capillary_suction_time_mock_objects,
)
from tests.test_api.test_routes.api_v2.cappressure import (
    cappressure_mock_objects,
)
from tests.test_api.test_routes.api_v2.cce import cce_mock_objects
from tests.test_api.test_routes.api_v2.cec_content import (
    cec_content_mock_objects,
)
from tests.test_api.test_routes.api_v2.constantvolumedepletion import (
    cvd_mock_objects,
)
from tests.test_api.test_routes.api_v2.core_gamma import (
    core_gamma_mock_objects,
)
from tests.test_api.test_routes.api_v2.coretologdepthshift import (
    coretologdepthshift_mock_objects,
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
from tests.test_api.test_routes.api_v2.gas_chromatography import (
    gas_chromatography_mock_objects,
)
from tests.test_api.test_routes.api_v2.gas_composition import (
    gas_composition_mock_objects,
)
from tests.test_api.test_routes.api_v2.gcms_alkanes import (
    gcms_alkanes_mock_objects,
)
from tests.test_api.test_routes.api_v2.gcms_aromatics import (
    gcms_aromatics_mock_objects,
)
from tests.test_api.test_routes.api_v2.gcms_ratios import (
    gcms_ratios_mock_objects,
)
from tests.test_api.test_routes.api_v2.gcmsms_analysis import (
    gcmsms_analysis_mock_objects,
)
from tests.test_api.test_routes.api_v2.interfacialtension import (
    interfacial_tension_mock_objects,
)
from tests.test_api.test_routes.api_v2.isotopes import isotopes_mock_objects
from tests.test_api.test_routes.api_v2.mininggeotechlogging import (
    mining_geotech_logging_mock_objects,
)
from tests.test_api.test_routes.api_v2.multiple_salinity import (
    multiple_salinity_mock_objects,
)
from tests.test_api.test_routes.api_v2.multiplecontactmiscibility import (
    mcm_mock_objects,
)
from tests.test_api.test_routes.api_v2.multistageseparator import (
    mss_mock_objects,
)
from tests.test_api.test_routes.api_v2.nmr import nmr_mock_objects
from tests.test_api.test_routes.api_v2.pdp import pdp_mock_objects
from tests.test_api.test_routes.api_v2.proppant_embedment import (
    proppant_embedment_mock_objects,
)
from tests.test_api.test_routes.api_v2.relative_permeability import (
    relative_permeability_mock_objects,
)
from tests.test_api.test_routes.api_v2.rock_compressibility import (
    rock_compressibility_mock_objects,
)
from tests.test_api.test_routes.api_v2.roller_oven_test import roller_oven_test_mock_objects
from tests.test_api.test_routes.api_v2.routinecoreanalysis import (
    rca_mock_objects,
)
from tests.test_api.test_routes.api_v2.saturation_test import saturation_test_mock_objects
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
from tests.test_api.test_routes.api_v2.triaxial import triaxial_mock_objects
from tests.test_api.test_routes.api_v2.uniaxial import uniaxial_mock_objects
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
from tests.test_api.test_routes.api_v2.black_oil_fluid_model import (
    black_oil_fluid_model_mock_objects,
)
from tests.test_api.test_routes.api_v2.compositional_fluid_model import (
    compositional_fluid_model_mock_objects,
)
from tests.test_api.test_routes.api_v2.thermal_compositional_fluid_model import (
    thermal_compositional_fluid_model_mock_objects,
)
from tests.test_api.test_routes.api_v2.xrd import xrd_mock_objects
from tests.test_api.test_routes.api_v2.xrf import xrf_mock_objects
from tests.test_api.test_routes.data import data_mock_objects
from tests.test_api.test_routes.data.data_mock_objects import (
    INVALID_DATA_WITH_NAN,
    ORIENT_SPLIT_422_PAYLOADS,
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
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    PARTITION,
    TEST_DEPTH_SHIFT_ID,
    TEST_DEPTH_SHIFT_KIND,
    BulkDatasetIdV2,
    TestContentPathsApiV2,
)
from tests.test_api.test_routes.reservoir_simulation_rock_physics_model import (
    res_sim_rock_physics_mock_objects,
)
from tests.test_api.test_routes.saturation_function_set import (
    saturation_function_set_mock_objects,
)

async_storage_record_service_mock = create_autospec(storage.StorageService, spec_set=True, instance=True)
async_dataset_service_mock = create_autospec(dataset.DatasetService, spec_set=True, instance=True)
async_entitlements_service_mock = create_autospec(entitlements.EntitlementsService, spec_set=True, instance=True)

async_entitlements_service_mock.get_groups.return_value = {
    "groups": [{"name": "test-group", "email": "test@example.com"}],
    "desId": "test-user",
}


async def mock_get_async_dataset_service():
    yield async_dataset_service_mock


async def mock_get_storage_service():
    yield async_storage_record_service_mock


async def mock_get_async_storage_service():
    yield async_storage_record_service_mock


async def mock_get_async_entitlements_service():
    yield async_entitlements_service_mock


@contextmanager
def services_overrides():
    overrides = {
        get_async_storage_service: mock_get_async_storage_service,
        get_async_dataset_service: mock_get_async_dataset_service,
        get_async_entitlements_service: mock_get_async_entitlements_service,
    }
    with dependencies.DependencyOverrider(app, overrides) as mock_dependencies:
        yield mock_dependencies


@pytest.fixture
def with_patched_storage_failed_integrity_validation(missed_records):
    """Patch storage query_records failure."""
    query_response = {
        "invalidRecords": missed_records,
    }
    with patch.object(
        async_storage_record_service_mock,
        "query_records",
        new_callable=AsyncMock,
        return_value=query_response,
    ):
        yield


@pytest.fixture
def with_patched_services_success(storage_method, osdu_records, dataset_method, blobs):
    """Patch storage and datasets to 200 success."""
    with patch.object(async_storage_record_service_mock, storage_method, side_effect=osdu_records):
        with patch.object(async_dataset_service_mock, dataset_method, side_effect=blobs):
            yield


@contextmanager
def post_overrides(
    record_data=None, test_dataset_record_id=data_mock_objects.TEST_DATASET_RECORD_ID, data_payload=None
):
    mock_get_storage_service = build_mock_get_storage_service(record_data, data_payload)
    mock_get_dataset_service = build_mock_get_dataset_service(test_dataset_record_id=test_dataset_record_id)
    overrides = {
        get_async_storage_service: mock_get_storage_service,
        get_async_dataset_service: mock_get_dataset_service,
    }
    with dependencies.DependencyOverrider(app, overrides) as mock_dependencies:
        yield mock_dependencies


def _version_from_urn(urn):
    """Extract schema version from DDMSDatasets URN (last segment if semver-like)."""
    last = urn.rsplit("/", 1)[-1]
    if len(last.split(".")) == 3 and all(p.isdigit() for p in last.split(".")):
        return last
    return "1.0.0"


def _headers_json(version="1.0.0"):
    return {**TEST_HEADERS_JSON, "Accept": f"*/*;version={version}"}


def _headers_parquet(version="1.0.0"):
    return {**TEST_HEADERS_PARQUET, "Accept": f"application/x-parquet;version={version}"}


def _headers_parquet_accept_only(version="1.0.0"):
    return {
        "data-partition-id": "opendes",
        "Authorization": "Bearer token",
        "Accept": f"application/x-parquet;version={version}",
    }


@pytest.mark.parametrize(
    "data_endpoint_path,dataset_id",
    [
        (TestContentPathsApiV2.RCA, BulkDatasetIdV2.RCA),
        (TestContentPathsApiV2.CCE, BulkDatasetIdV2.CCE),
        (TestContentPathsApiV2.DIFF_LIB, BulkDatasetIdV2.DIFF_LIB),
        (TestContentPathsApiV2.TRANSPORT_TEST, BulkDatasetIdV2.TRANSPORT_TEST),
        (TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS, BulkDatasetIdV2.COMPOSITIONAL_ANALYSIS),
        (TestContentPathsApiV2.ATMOSPHERIC_FLASH, BulkDatasetIdV2.ATMOSPHERIC_FLASH),
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
        (TestContentPathsApiV2.PROPPANT_EMBEDMENT, BulkDatasetIdV2.PROPPANT_EMBEDMENT),
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
        (TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL, BulkDatasetIdV2.RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL),
        (TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL, BulkDatasetIdV2.SATURATION_FUNCTION_SET_MODEL),
        (TestContentPathsApiV2.DEPTH_SHIFT_MODEL, BulkDatasetIdV2.DEPTH_SHIFT_MODEL),
        (TestContentPathsApiV2.ROLLER_OVEN_TEST, BulkDatasetIdV2.ROLLER_OVEN_TEST),
        (TestContentPathsApiV2.SATURATION_TEST, BulkDatasetIdV2.SATURATION_TEST),
        (TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL, BulkDatasetIdV2.BLACK_OIL_FLUID_MODEL),
        (TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL, BulkDatasetIdV2.COMPOSITIONAL_FLUID_MODEL),
        (TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL, BulkDatasetIdV2.THERMAL_COMPOSITIONAL_FLUID_MODEL),
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
    "data_endpoint_path",
    [
        TestContentPathsApiV2.RCA,
        TestContentPathsApiV2.CCE,
        TestContentPathsApiV2.DIFF_LIB,
        TestContentPathsApiV2.TRANSPORT_TEST,
        TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS,
        TestContentPathsApiV2.ATMOSPHERIC_FLASH,
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
        TestContentPathsApiV2.PROPPANT_EMBEDMENT,
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
        TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL,
        TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
        TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
        TestContentPathsApiV2.ROLLER_OVEN_TEST,
        TestContentPathsApiV2.SATURATION_TEST,
        TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
        TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL,
        TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
    ],
)
@pytest.mark.asyncio
async def test_post_data_no_content_header(data_endpoint_path):
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers={"data-partition-id": "opendes"},
                content=b"{}",
            )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    expected = {"code": status.HTTP_400_BAD_REQUEST, "reason": "Content-Type header is required, but was not provided"}
    assert response.json() == expected


@pytest.mark.parametrize(
    "data_endpoint_path",
    [
        TestContentPathsApiV2.RCA,
        TestContentPathsApiV2.CCE,
        TestContentPathsApiV2.DIFF_LIB,
        TestContentPathsApiV2.TRANSPORT_TEST,
        TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS,
        TestContentPathsApiV2.ATMOSPHERIC_FLASH,
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
        TestContentPathsApiV2.PROPPANT_EMBEDMENT,
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
        TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL,
        TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
        TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
        TestContentPathsApiV2.ROLLER_OVEN_TEST,
        TestContentPathsApiV2.SATURATION_TEST,
        TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
        TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL,
        TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL
    ],
)
@pytest.mark.asyncio
async def test_post_data_wrong_content_header(data_endpoint_path):
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers={"Content-Type": "wrong-type", "data-partition-id": "opendes"},
                content=b"{}",
            )

    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    expected = {
        "code": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        "reason": "The provided content-type is not supported. Please provide one of the next supported content types: ['application/json', 'application/x-parquet']",
    }
    assert response.json() == expected


@pytest.mark.parametrize(
    "data_endpoint_path,dataset_id",
    [
        (TestContentPathsApiV2.RCA, rca_mock_objects.TEST_DATASET_RECORD_ID),
        (TestContentPathsApiV2.VLE, vle_mock_objects.TEST_DATASET_RECORD_ID),
        (TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL, res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID),
        (
            TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
            saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
            coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL, 
            black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL, 
            compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID
        ),
        (
            TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
            thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_data_no_content_type_does_not_return_400(data_endpoint_path, dataset_id):
    """GET data without Content-Type must NOT return 400 Content-Type validation error.

    Content-Type is irrelevant for GET requests; response format is
    negotiated via the Accept header instead.  This test proves that the
    Content-Type validation dependency is no longer attached to GET routes.
    The 404 response (dataset not found in mock) is expected and acceptable –
    it confirms the request passed header validation and reached business logic.
    """
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{data_endpoint_path}/{dataset_id}",
                headers={
                    "data-partition-id": "opendes",
                    "Authorization": "Bearer token",
                    "Accept": "*/*;version=1.0.0",
                    # No Content-Type header on purpose
                },
            )

    assert response.status_code != status.HTTP_400_BAD_REQUEST, "GET must not fail with 400 due to missing Content-Type"
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        assert "Content-Type" not in response.json().get("reason", "")


@pytest.mark.parametrize(
    "data_endpoint_path,dataset_id",
    [
        (TestContentPathsApiV2.RCA, rca_mock_objects.TEST_DATASET_RECORD_ID),
        (TestContentPathsApiV2.VLE, vle_mock_objects.TEST_DATASET_RECORD_ID),
        (
            TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL, 
            black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL, 
            compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID
        ),
        (
            TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
            thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_data_accept_parquet_does_not_return_content_type_error(data_endpoint_path, dataset_id):
    """GET data with Accept: application/x-parquet must NOT return a Content-Type 400 error.

    This proves the Accept header MIME type is accepted for content negotiation.
    A 404 response (dataset not found in mock) is acceptable – it means the
    request reached business logic and was not blocked by header validation.
    """
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{data_endpoint_path}/{dataset_id}",
                headers={
                    "data-partition-id": "opendes",
                    "Authorization": "Bearer token",
                    "Accept": "application/x-parquet;version=1.0.0",
                    # No Content-Type header on purpose
                },
            )

    assert (
        response.status_code != status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    ), "GET must not fail with 415 Unsupported Media Type"
    assert response.status_code != status.HTTP_400_BAD_REQUEST, "GET must not fail with 400 due to missing Content-Type"


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
            TestContentPathsApiV2.ATMOSPHERIC_FLASH,
            atmospheric_flash_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                atmospheric_flash_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", atmospheric_flash_mock_objects.TEST_DATA)],
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
            TestContentPathsApiV2.VLE,
            vle_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            ],
            "download_file",
            [build_get_test_data("x-parquet", vle_mock_objects.TEST_DATA_V2)],
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
            TestContentPathsApiV2.SLIMTUBE,
            slimtube_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            ],
            "download_file",
            [build_get_test_data("x-parquet", slimtube_mock_objects.TEST_DATA_V2)],
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
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            ],
            "download_file",
            [build_get_test_data("x-parquet", relative_permeability_mock_objects.TEST_DATA_V2)],
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
            isotopes_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                isotopes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", isotopes_mock_objects.TEST_DATA)],
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
            uniaxial_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                uniaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_mock_objects.TEST_DATA)],
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
            triaxial_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                triaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.PROPPANT_EMBEDMENT,
            proppant_embedment_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                proppant_embedment_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", proppant_embedment_mock_objects.TEST_DATA)],
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
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            ],
            "download_file",
            [build_get_test_data("x-parquet", cappressure_mock_objects.TEST_DATA_V2)],
        ),
        (
            TestContentPathsApiV2.CAP_SUCTION_TIME,
            capillary_suction_time_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                capillary_suction_time_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", capillary_suction_time_mock_objects.TEST_DATA)],
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
            TestContentPathsApiV2.XRF,
            xrf_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            ],
            "download_file",
            [build_get_test_data("x-parquet", xrf_mock_objects.TEST_DATA_V2)],
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
            TestContentPathsApiV2.XRD,
            xrd_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            ],
            "download_file",
            [build_get_test_data("x-parquet", xrd_mock_objects.TEST_DATA_V2)],
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
            TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL,
            res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                res_sim_rock_physics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", res_sim_rock_physics_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
            saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                saturation_function_set_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", saturation_function_set_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
            coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", coretologdepthshift_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.ROLLER_OVEN_TEST,
            roller_oven_test_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                roller_oven_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", roller_oven_test_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.SATURATION_TEST,
            saturation_test_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                saturation_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", saturation_test_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
            black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_fluid_model_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL,
            compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", compositional_fluid_model_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
            thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [
                thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            ],
            "download_file",
            [build_get_test_data("x-parquet", thermal_compositional_fluid_model_mock_objects.TEST_DATA)],
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
    version = _version_from_urn(osdu_records[0]["data"]["DDMSDatasets"][0])
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{data_endpoint_path}/{dataset_id}",
                headers=_headers_parquet(version),
            )
    assert response.status_code == status.HTTP_200_OK
    expected_df = pq.read_table(pa.BufferReader(blobs[0])).to_pandas()
    actual_df = pq.read_table(pa.BufferReader(response.content)).to_pandas()
    pd.testing.assert_frame_equal(expected_df, actual_df, check_like=True)


@pytest.mark.parametrize(
    "data_endpoint_path,dataset_id,storage_method,osdu_records,dataset_method,blobs",
    [
        (
            TestContentPathsApiV2.RCA,
            rca_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", rca_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.CCE,
            cce_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [cce_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", cce_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
            black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_fluid_model_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL,
            compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", compositional_fluid_model_mock_objects.TEST_DATA)],
        ),
        (
            TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
            thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            "get_record",
            [thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", thermal_compositional_fluid_model_mock_objects.TEST_DATA)],
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_data_accept_negotiation_returns_parquet(
    data_endpoint_path,
    dataset_id,
    storage_method,
    osdu_records,
    dataset_method,
    blobs,
    with_patched_services_success,
):
    """Accept: application/x-parquet without Content-Type header must return parquet response.

    Verifies that response format is negotiated via the Accept header, not
    Content-Type.  Content-Type is absent on purpose — GET requests carry no
    body, so the server must not rely on it for output selection.
    """
    version = _version_from_urn(osdu_records[0]["data"]["DDMSDatasets"][0])
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{data_endpoint_path}/{dataset_id}",
                headers=_headers_parquet_accept_only(version),
            )
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("application/x-parquet")
    expected_df = pq.read_table(pa.BufferReader(blobs[0])).to_pandas()
    actual_df = pq.read_table(pa.BufferReader(response.content)).to_pandas()
    pd.testing.assert_frame_equal(expected_df, actual_df, check_like=True)


@pytest.mark.parametrize(
    "data_endpoint_path,dataset_id",
    [
        (TestContentPathsApiV2.RCA, rca_mock_objects.TEST_DATASET_RECORD_ID),
        (TestContentPathsApiV2.VLE, vle_mock_objects.TEST_DATASET_RECORD_ID),
        (   
            TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL, 
            black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID
        ),
        (   
            TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL, 
            compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID
        ),
        (
            TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
            thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID
        )
    ],
)
@pytest.mark.asyncio
async def test_get_data_unsupported_accept_returns_406(data_endpoint_path, dataset_id):
    """Accept header with unsupported MIME type must return 406 Not Acceptable."""
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{data_endpoint_path}/{dataset_id}",
                headers={
                    "data-partition-id": "opendes",
                    "Authorization": "Bearer token",
                    "Accept": "application/xml;version=1.0.0",
                },
            )
    assert response.status_code == status.HTTP_406_NOT_ACCEPTABLE


@pytest.mark.parametrize(
    "data_endpoint_path,params,storage_method,osdu_records,dataset_method,blobs,returned_data",
    [
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
            f"{TestContentPathsApiV2.ATMOSPHERIC_FLASH}/{atmospheric_flash_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [atmospheric_flash_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", atmospheric_flash_mock_objects.TEST_DATA)],
            atmospheric_flash_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.VLE}/{vle_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", vle_mock_objects.TEST_DATA_V2)],
            vle_mock_objects.TEST_DATA_V2,
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
            f"{TestContentPathsApiV2.SLIMTUBE}/{slimtube_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", slimtube_mock_objects.TEST_DATA_V2)],
            slimtube_mock_objects.TEST_DATA_V2,
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
            f"{TestContentPathsApiV2.RELATIVE_PERMEABILITY}/{relative_permeability_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", relative_permeability_mock_objects.TEST_DATA_V2)],
            relative_permeability_mock_objects.TEST_DATA_V2,
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
            f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotopes_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [isotopes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", isotopes_mock_objects.TEST_DATA)],
            isotopes_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [uniaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_mock_objects.TEST_DATA)],
            uniaxial_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [triaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_mock_objects.TEST_DATA)],
            triaxial_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.PROPPANT_EMBEDMENT}/{proppant_embedment_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [proppant_embedment_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", proppant_embedment_mock_objects.TEST_DATA)],
            proppant_embedment_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.CAP_PRESSURE}/{cappressure_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", cappressure_mock_objects.TEST_DATA_V2)],
            cappressure_mock_objects.TEST_DATA_V2,
        ),
        (
            f"{TestContentPathsApiV2.CAP_SUCTION_TIME}/{capillary_suction_time_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [capillary_suction_time_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", capillary_suction_time_mock_objects.TEST_DATA)],
            capillary_suction_time_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.XRF}/{xrf_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", xrf_mock_objects.TEST_DATA_V2)],
            xrf_mock_objects.TEST_DATA_V2,
        ),
        (
            f"{TestContentPathsApiV2.ROLLER_OVEN_TEST}/{roller_oven_test_mock_objects.TEST_DATASET_RECORD_ID}",
            roller_oven_test_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [roller_oven_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", roller_oven_test_mock_objects.TEST_DATA)],
            roller_oven_test_mock_objects.TEST_AGGREGATED_DATA,
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
            f"{TestContentPathsApiV2.ATMOSPHERIC_FLASH}/{atmospheric_flash_mock_objects.TEST_DATASET_RECORD_ID}",
            atmospheric_flash_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [atmospheric_flash_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", atmospheric_flash_mock_objects.TEST_DATA)],
            atmospheric_flash_mock_objects.TEST_AGGREGATED_DATA,
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
            f"{TestContentPathsApiV2.VLE}/{vle_mock_objects.TEST_DATASET_RECORD_ID}",
            vle_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", vle_mock_objects.TEST_DATA_V2)],
            vle_mock_objects.TEST_AGGREGATED_DATA_V2,
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
            f"{TestContentPathsApiV2.SLIMTUBE}/{slimtube_mock_objects.TEST_DATASET_RECORD_ID}",
            slimtube_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", slimtube_mock_objects.TEST_DATA_V2)],
            slimtube_mock_objects.TEST_AGGREGATED_DATA_V2,
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
            f"{TestContentPathsApiV2.RELATIVE_PERMEABILITY}/{relative_permeability_mock_objects.TEST_DATASET_RECORD_ID}",
            relative_permeability_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", relative_permeability_mock_objects.TEST_DATA_V2)],
            relative_permeability_mock_objects.TEST_AGGREGATED_DATA_V2,
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
            f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotopes_mock_objects.TEST_DATASET_RECORD_ID}",
            isotopes_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [isotopes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", isotopes_mock_objects.TEST_DATA)],
            isotopes_mock_objects.TEST_AGGREGATED_DATA,
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
            f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_mock_objects.TEST_DATASET_RECORD_ID}",
            uniaxial_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [uniaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_mock_objects.TEST_DATA)],
            uniaxial_mock_objects.TEST_AGGREGATED_DATA,
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
            f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_mock_objects.TEST_DATASET_RECORD_ID}",
            triaxial_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [triaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_mock_objects.TEST_DATA)],
            triaxial_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.PROPPANT_EMBEDMENT}/{proppant_embedment_mock_objects.TEST_DATASET_RECORD_ID}",
            proppant_embedment_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [proppant_embedment_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", proppant_embedment_mock_objects.TEST_DATA)],
            proppant_embedment_mock_objects.TEST_AGGREGATED_DATA,
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
            f"{TestContentPathsApiV2.CAP_PRESSURE}/{cappressure_mock_objects.TEST_DATASET_RECORD_ID}",
            cappressure_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", cappressure_mock_objects.TEST_DATA_V2)],
            cappressure_mock_objects.TEST_AGGREGATED_DATA_V2,
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
            f"{TestContentPathsApiV2.XRF}/{xrf_mock_objects.TEST_DATASET_RECORD_ID}",
            xrf_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", xrf_mock_objects.TEST_DATA_V2)],
            xrf_mock_objects.TEST_AGGREGATED_DATA_V2,
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
            f"{TestContentPathsApiV2.ATMOSPHERIC_FLASH}/{atmospheric_flash_mock_objects.TEST_DATASET_RECORD_ID}",
            atmospheric_flash_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [atmospheric_flash_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", atmospheric_flash_mock_objects.TEST_DATA)],
            atmospheric_flash_mock_objects.TEST_FILTERED_DATA,
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
            f"{TestContentPathsApiV2.VLE}/{vle_mock_objects.TEST_DATASET_RECORD_ID}",
            vle_mock_objects.TEST_PARAMS_FILTERS_V2,
            "get_record",
            [vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", vle_mock_objects.TEST_DATA_V2)],
            vle_mock_objects.TEST_FILTERED_DATA_V2,
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
            f"{TestContentPathsApiV2.SLIMTUBE}/{slimtube_mock_objects.TEST_DATASET_RECORD_ID}",
            slimtube_mock_objects.TEST_PARAMS_FILTERS_V2,
            "get_record",
            [slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", slimtube_mock_objects.TEST_DATA_V2)],
            slimtube_mock_objects.TEST_FILTERED_DATA_V2,
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
            f"{TestContentPathsApiV2.RELATIVE_PERMEABILITY}/{relative_permeability_mock_objects.TEST_DATASET_RECORD_ID}",
            relative_permeability_mock_objects.TEST_PARAMS_FILTERS_V2,
            "get_record",
            [relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", relative_permeability_mock_objects.TEST_DATA_V2)],
            relative_permeability_mock_objects.TEST_FILTERED_DATA_V2,
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
            f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotopes_mock_objects.TEST_DATASET_RECORD_ID}",
            isotopes_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [isotopes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", isotopes_mock_objects.TEST_DATA)],
            isotopes_mock_objects.TEST_FILTERED_DATA,
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
            f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_mock_objects.TEST_DATASET_RECORD_ID}",
            uniaxial_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [uniaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_mock_objects.TEST_DATA)],
            uniaxial_mock_objects.TEST_FILTERED_DATA,
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
            f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_mock_objects.TEST_DATASET_RECORD_ID}",
            triaxial_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [triaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_mock_objects.TEST_DATA)],
            triaxial_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.PROPPANT_EMBEDMENT}/{proppant_embedment_mock_objects.TEST_DATASET_RECORD_ID}",
            proppant_embedment_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [proppant_embedment_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", proppant_embedment_mock_objects.TEST_DATA)],
            proppant_embedment_mock_objects.TEST_FILTERED_DATA,
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
            f"{TestContentPathsApiV2.CAP_PRESSURE}/{cappressure_mock_objects.TEST_DATASET_RECORD_ID}",
            cappressure_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", cappressure_mock_objects.TEST_DATA_V2)],
            cappressure_mock_objects.TEST_FILTERED_DATA_V2,
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
            f"{TestContentPathsApiV2.XRF}/{xrf_mock_objects.TEST_DATASET_RECORD_ID}",
            xrf_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", xrf_mock_objects.TEST_DATA_V2)],
            xrf_mock_objects.TEST_FILTERED_DATA_V2,
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
            None,
            "get_record",
            [xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", xrd_mock_objects.TEST_DATA_V2)],
            xrd_mock_objects.TEST_DATA_V2,
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
            xrd_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", xrd_mock_objects.TEST_DATA_V2)],
            xrd_mock_objects.TEST_FILTERED_DATA_V2,
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
            f"{TestContentPathsApiV2.XRD}/{xrd_mock_objects.TEST_DATASET_RECORD_ID}",
            xrd_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", xrd_mock_objects.TEST_DATA_V2)],
            xrd_mock_objects.TEST_AGGREGATED_DATA_V2,
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
            None,
            "get_record",
            [sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", sto_mock_objects.TEST_DATA_V2)],
            sto_mock_objects.TEST_DATA_V2,
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
            sto_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", sto_mock_objects.TEST_DATA_V2)],
            sto_mock_objects.TEST_FILTERED_DATA_V2,
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
            f"{TestContentPathsApiV2.STO}/{sto_mock_objects.TEST_DATASET_RECORD_ID}",
            sto_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2],
            "download_file",
            [build_get_test_data("x-parquet", sto_mock_objects.TEST_DATA_V2)],
            sto_mock_objects.TEST_AGGREGATED_DATA_V2,
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
            f"{TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL}/{res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [res_sim_rock_physics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", res_sim_rock_physics_mock_objects.TRIMMED_TEST_DATA)],
            res_sim_rock_physics_mock_objects.TRIMMED_TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL}/{res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID}",
            res_sim_rock_physics_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [res_sim_rock_physics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", res_sim_rock_physics_mock_objects.TEST_DATA)],
            res_sim_rock_physics_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL}/{res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID}",
            res_sim_rock_physics_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [res_sim_rock_physics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", res_sim_rock_physics_mock_objects.TEST_DATA)],
            res_sim_rock_physics_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL}/{saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [saturation_function_set_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", saturation_function_set_mock_objects.TRIMMED_TEST_DATA)],
            saturation_function_set_mock_objects.TRIMMED_TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL}/{saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID}",
            saturation_function_set_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [saturation_function_set_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", saturation_function_set_mock_objects.TEST_DATA)],
            saturation_function_set_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL}/{saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID}",
            saturation_function_set_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [saturation_function_set_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", saturation_function_set_mock_objects.TEST_DATA)],
            saturation_function_set_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.DEPTH_SHIFT_MODEL}/{coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", coretologdepthshift_mock_objects.TRIMMED_TEST_DATA)],
            coretologdepthshift_mock_objects.TRIMMED_TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.DEPTH_SHIFT_MODEL}/{coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID}",
            coretologdepthshift_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", coretologdepthshift_mock_objects.TEST_DATA)],
            coretologdepthshift_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.DEPTH_SHIFT_MODEL}/{coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID}",
            coretologdepthshift_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", coretologdepthshift_mock_objects.TEST_DATA)],
            coretologdepthshift_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ROLLER_OVEN_TEST}/{roller_oven_test_mock_objects.TEST_DATASET_RECORD_ID}",
            roller_oven_test_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [roller_oven_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", roller_oven_test_mock_objects.TEST_DATA)],
            roller_oven_test_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SATURATION_TEST}/{saturation_test_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [saturation_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", saturation_test_mock_objects.TEST_DATA)],
            saturation_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SATURATION_TEST}/{saturation_test_mock_objects.TEST_DATASET_RECORD_ID}",
            saturation_test_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [saturation_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", saturation_test_mock_objects.TEST_DATA)],
            saturation_test_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SATURATION_TEST}/{saturation_test_mock_objects.TEST_DATASET_RECORD_ID}",
            saturation_test_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [saturation_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", saturation_test_mock_objects.TEST_DATA)],
            saturation_test_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL}/{black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_fluid_model_mock_objects.TRIMMED_TEST_DATA)],
            black_oil_fluid_model_mock_objects.TRIMMED_TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL}/{compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", compositional_fluid_model_mock_objects.TRIMMED_TEST_DATA)],
            compositional_fluid_model_mock_objects.TRIMMED_TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL}/{thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            None,
            "get_record",
            [thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", thermal_compositional_fluid_model_mock_objects.TRIMMED_TEST_DATA)],
            thermal_compositional_fluid_model_mock_objects.TRIMMED_TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL}/{black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            black_oil_fluid_model_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_fluid_model_mock_objects.TEST_DATA)],
            black_oil_fluid_model_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL}/{compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            compositional_fluid_model_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", compositional_fluid_model_mock_objects.TEST_DATA)],
            compositional_fluid_model_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL}/{thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            thermal_compositional_fluid_model_mock_objects.TEST_PARAMS_FILTERS,
            "get_record",
            [thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", thermal_compositional_fluid_model_mock_objects.TEST_DATA)],
            thermal_compositional_fluid_model_mock_objects.TEST_FILTERED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL}/{black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            black_oil_fluid_model_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_fluid_model_mock_objects.TEST_DATA)],
            black_oil_fluid_model_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL}/{compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            compositional_fluid_model_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", compositional_fluid_model_mock_objects.TEST_DATA)],
            compositional_fluid_model_mock_objects.TEST_AGGREGATED_DATA,
        ),
        (
            f"{TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL}/{thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            thermal_compositional_fluid_model_mock_objects.TEST_PARAMS_AGGREGATION,
            "get_record",
            [thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", thermal_compositional_fluid_model_mock_objects.TEST_DATA)],
            thermal_compositional_fluid_model_mock_objects.TEST_AGGREGATED_DATA,
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
    version = _version_from_urn(osdu_records[0]["data"]["DDMSDatasets"][0])
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                data_endpoint_path,
                headers=_headers_json(version),
                params=params,
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["index"] == returned_data["index"]
    assert set(response.json()["columns"]) == set(returned_data["columns"])
    assert all(i in response.json()["data"][0] for i in returned_data["data"][0])


@pytest.mark.parametrize(
    "data_endpoint_path,storage_method,osdu_records,dataset_method,blobs,returned_data",
    [
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
            f"{TestContentPathsApiV2.ATMOSPHERIC_FLASH}/{atmospheric_flash_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [atmospheric_flash_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", atmospheric_flash_mock_objects.TEST_DATA)],
            atmospheric_flash_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotopes_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [isotopes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", isotopes_mock_objects.TEST_DATA)],
            isotopes_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [uniaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_mock_objects.TEST_DATA)],
            uniaxial_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [triaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_mock_objects.TEST_DATA)],
            triaxial_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.PROPPANT_EMBEDMENT}/{proppant_embedment_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [proppant_embedment_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", proppant_embedment_mock_objects.TEST_DATA)],
            proppant_embedment_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL}/{res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [res_sim_rock_physics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", res_sim_rock_physics_mock_objects.TEST_DATA)],
            res_sim_rock_physics_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL}/{saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [saturation_function_set_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", saturation_function_set_mock_objects.TEST_DATA)],
            saturation_function_set_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.DEPTH_SHIFT_MODEL}/{coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", coretologdepthshift_mock_objects.TEST_DATA)],
            coretologdepthshift_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ROLLER_OVEN_TEST}/{roller_oven_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [roller_oven_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", roller_oven_test_mock_objects.TEST_DATA)],
            roller_oven_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SATURATION_TEST}/{saturation_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [saturation_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", saturation_test_mock_objects.TEST_DATA)],
            saturation_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL}/{black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_fluid_model_mock_objects.TEST_DATA)],
            black_oil_fluid_model_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL}/{compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", compositional_fluid_model_mock_objects.TEST_DATA)],
            compositional_fluid_model_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL}/{thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", thermal_compositional_fluid_model_mock_objects.TEST_DATA)],
            thermal_compositional_fluid_model_mock_objects.TEST_DATA,
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
        "code": status.HTTP_406_NOT_ACCEPTABLE,
        "reason": (
            "No schema version specified or invalid schema format."
            " Use the content_schema_version query parameter (e.g. ?content_schema_version=1.0.0)."
            " The deprecated Accept header versioning is also still accepted"
            " (e.g. Accept: */*;version=1.0.0)."
        ),
    }

    assert response.status_code == status.HTTP_406_NOT_ACCEPTABLE
    assert response.json() == expected_error


@pytest.mark.parametrize(
    "data_endpoint_path,storage_method,osdu_records,dataset_method,blobs,returned_data",
    [
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
            f"{TestContentPathsApiV2.ATMOSPHERIC_FLASH}/{atmospheric_flash_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [atmospheric_flash_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", atmospheric_flash_mock_objects.TEST_DATA)],
            atmospheric_flash_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotopes_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [isotopes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", isotopes_mock_objects.TEST_DATA)],
            isotopes_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [uniaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_mock_objects.TEST_DATA)],
            uniaxial_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [triaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_mock_objects.TEST_DATA)],
            triaxial_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.PROPPANT_EMBEDMENT}/{proppant_embedment_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [proppant_embedment_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", proppant_embedment_mock_objects.TEST_DATA)],
            proppant_embedment_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL}/{res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [res_sim_rock_physics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", res_sim_rock_physics_mock_objects.TEST_DATA)],
            res_sim_rock_physics_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL}/{saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [saturation_function_set_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", saturation_function_set_mock_objects.TEST_DATA)],
            saturation_function_set_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.DEPTH_SHIFT_MODEL}/{coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", coretologdepthshift_mock_objects.TEST_DATA)],
            coretologdepthshift_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ROLLER_OVEN_TEST}/{roller_oven_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [roller_oven_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", roller_oven_test_mock_objects.TEST_DATA)],
            roller_oven_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL}/{black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_fluid_model_mock_objects.TEST_DATA)],
            black_oil_fluid_model_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL}/{compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", compositional_fluid_model_mock_objects.TEST_DATA)],
            compositional_fluid_model_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL}/{thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", thermal_compositional_fluid_model_mock_objects.TEST_DATA)],
            thermal_compositional_fluid_model_mock_objects.TEST_DATA,
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
        "code": status.HTTP_406_NOT_ACCEPTABLE,
        "reason": (
            "No schema version specified or invalid schema format."
            " Use the content_schema_version query parameter (e.g. ?content_schema_version=1.0.0)."
            " The deprecated Accept header versioning is also still accepted"
            " (e.g. Accept: */*;version=1.0.0)."
        ),
    }

    assert response.status_code == status.HTTP_406_NOT_ACCEPTABLE
    assert response.json() == expected_error


@pytest.mark.parametrize(
    "data_endpoint_path,storage_method,osdu_records,dataset_method,blobs,returned_data",
    [
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
            f"{TestContentPathsApiV2.ATMOSPHERIC_FLASH}/{atmospheric_flash_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [atmospheric_flash_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", atmospheric_flash_mock_objects.TEST_DATA)],
            atmospheric_flash_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotopes_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [isotopes_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", isotopes_mock_objects.TEST_DATA)],
            isotopes_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [uniaxial_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", uniaxial_mock_objects.TEST_DATA)],
            uniaxial_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [triaxial_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", triaxial_mock_objects.TEST_DATA)],
            triaxial_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.PROPPANT_EMBEDMENT}/{proppant_embedment_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [proppant_embedment_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", proppant_embedment_mock_objects.TEST_DATA)],
            proppant_embedment_mock_objects.TEST_DATA,
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
            f"{TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL}/{res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [res_sim_rock_physics_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", res_sim_rock_physics_mock_objects.TEST_DATA)],
            res_sim_rock_physics_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL}/{saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [saturation_function_set_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", saturation_function_set_mock_objects.TEST_DATA)],
            saturation_function_set_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.DEPTH_SHIFT_MODEL}/{coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [coretologdepthshift_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", coretologdepthshift_mock_objects.TEST_DATA)],
            coretologdepthshift_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.ROLLER_OVEN_TEST}/{roller_oven_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [roller_oven_test_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", roller_oven_test_mock_objects.TEST_DATA)],
            roller_oven_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.SATURATION_TEST}/{saturation_test_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [saturation_test_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", saturation_test_mock_objects.TEST_DATA)],
            saturation_test_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL}/{black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", black_oil_fluid_model_mock_objects.TEST_DATA)],
            black_oil_fluid_model_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL}/{compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [compositional_fluid_model_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", compositional_fluid_model_mock_objects.TEST_DATA)],
            compositional_fluid_model_mock_objects.TEST_DATA,
        ),
        (
            f"{TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL}/{thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
            "get_record",
            [thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION],
            "download_file",
            [build_get_test_data("x-parquet", thermal_compositional_fluid_model_mock_objects.TEST_DATA)],
            thermal_compositional_fluid_model_mock_objects.TEST_DATA,
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
    dataset_id, _ = get_id_version(data_endpoint_path.split("/")[-1])
    error_title = f"Schema version mismatch for dataset {dataset_id}:"
    error_details = f"requested 1.0.0, stored ['2.0.0']"
    expected_error = {
        "code": status.HTTP_400_BAD_REQUEST,
        "reason": f"{error_title} {error_details}",
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
            TestContentPathsApiV2.ATMOSPHERIC_FLASH,
            atmospheric_flash_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            atmospheric_flash_mock_objects.TEST_DATA,
            atmospheric_flash_mock_objects.TEST_DATASET_RECORD_ID,
            atmospheric_flash_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            TestContentPathsApiV2.VLE,
            vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            vle_mock_objects.TEST_DATA_V2,
            vle_mock_objects.TEST_DATASET_RECORD_ID,
            vle_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.SLIMTUBE,
            slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            slimtube_mock_objects.TEST_DATA_V2,
            slimtube_mock_objects.TEST_DATASET_RECORD_ID,
            slimtube_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            relative_permeability_mock_objects.TEST_DATA_V2,
            relative_permeability_mock_objects.TEST_DATASET_RECORD_ID,
            relative_permeability_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            isotopes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            isotopes_mock_objects.TEST_DATA,
            isotopes_mock_objects.TEST_DATASET_RECORD_ID,
            isotopes_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            uniaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            uniaxial_mock_objects.TEST_DATA,
            uniaxial_mock_objects.TEST_DATASET_RECORD_ID,
            uniaxial_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            triaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            triaxial_mock_objects.TEST_DATA,
            triaxial_mock_objects.TEST_DATASET_RECORD_ID,
            triaxial_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.PROPPANT_EMBEDMENT,
            proppant_embedment_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            proppant_embedment_mock_objects.TEST_DATA,
            proppant_embedment_mock_objects.TEST_DATASET_RECORD_ID,
            proppant_embedment_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cappressure_mock_objects.TEST_DATA,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            cappressure_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            cappressure_mock_objects.TEST_DATA_V2,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            cappressure_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
        ),
        (
            TestContentPathsApiV2.CAP_SUCTION_TIME,
            capillary_suction_time_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            capillary_suction_time_mock_objects.TEST_DATA,
            capillary_suction_time_mock_objects.TEST_DATASET_RECORD_ID,
            capillary_suction_time_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            TestContentPathsApiV2.XRF,
            xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            xrf_mock_objects.TEST_DATA_V2,
            xrf_mock_objects.TEST_DATASET_RECORD_ID,
            xrf_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.XRD,
            xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            xrd_mock_objects.TEST_DATA_V2,
            xrd_mock_objects.TEST_DATASET_RECORD_ID,
            xrd_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.STO,
            sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            sto_mock_objects.TEST_DATA_V2,
            sto_mock_objects.TEST_DATASET_RECORD_ID,
            sto_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
        ),
        (
            TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
            crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            crushed_rock_analysis_mock_objects.TEST_DATA,
            crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            crushed_rock_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL,
            res_sim_rock_physics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            res_sim_rock_physics_mock_objects.TEST_DATA,
            res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID,
            res_sim_rock_physics_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
            saturation_function_set_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            saturation_function_set_mock_objects.TEST_DATA,
            saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID,
            saturation_function_set_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
            coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            coretologdepthshift_mock_objects.TEST_DATA,
            coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID,
            coretologdepthshift_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ROLLER_OVEN_TEST,
            roller_oven_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            roller_oven_test_mock_objects.TEST_DATA,
            roller_oven_test_mock_objects.TEST_DATASET_RECORD_ID,
            roller_oven_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SATURATION_TEST,
            saturation_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            saturation_test_mock_objects.TEST_DATA,
            saturation_test_mock_objects.TEST_DATASET_RECORD_ID,
            saturation_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
            black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            black_oil_fluid_model_mock_objects.TEST_DATA,
            black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            black_oil_fluid_model_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL,
            compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            compositional_fluid_model_mock_objects.TEST_DATA,
            compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            compositional_fluid_model_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
            thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            thermal_compositional_fluid_model_mock_objects.TEST_DATA,
            thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            thermal_compositional_fluid_model_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_data_json(data_endpoint_path, record_data, test_data, test_dataset_record_id, test_ddms_urn):
    version = _version_from_urn(record_data["data"]["DDMSDatasets"][0])
    with post_overrides(record_data, test_dataset_record_id, test_data):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=_headers_json(version),
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
            TestContentPathsApiV2.ATMOSPHERIC_FLASH,
            atmospheric_flash_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            atmospheric_flash_mock_objects.TEST_DATA,
            atmospheric_flash_mock_objects.TEST_DATASET_RECORD_ID,
            atmospheric_flash_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            TestContentPathsApiV2.VLE,
            vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            vle_mock_objects.TEST_DATA_V2,
            vle_mock_objects.TEST_DATASET_RECORD_ID,
            vle_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.SLIMTUBE,
            slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            slimtube_mock_objects.TEST_DATA_V2,
            slimtube_mock_objects.TEST_DATASET_RECORD_ID,
            slimtube_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            relative_permeability_mock_objects.TEST_DATA_V2,
            relative_permeability_mock_objects.TEST_DATASET_RECORD_ID,
            relative_permeability_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            isotopes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            isotopes_mock_objects.TEST_DATA,
            isotopes_mock_objects.TEST_DATASET_RECORD_ID,
            isotopes_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            uniaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            uniaxial_mock_objects.TEST_DATA,
            uniaxial_mock_objects.TEST_DATASET_RECORD_ID,
            uniaxial_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            triaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            triaxial_mock_objects.TEST_DATA,
            triaxial_mock_objects.TEST_DATASET_RECORD_ID,
            triaxial_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.PROPPANT_EMBEDMENT,
            proppant_embedment_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            proppant_embedment_mock_objects.TEST_DATA,
            proppant_embedment_mock_objects.TEST_DATASET_RECORD_ID,
            proppant_embedment_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cappressure_mock_objects.TEST_DATA,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            cappressure_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            cappressure_mock_objects.TEST_DATA_V2,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            cappressure_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
        ),
        (
            TestContentPathsApiV2.CAP_SUCTION_TIME,
            capillary_suction_time_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            capillary_suction_time_mock_objects.TEST_DATA,
            capillary_suction_time_mock_objects.TEST_DATASET_RECORD_ID,
            capillary_suction_time_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            TestContentPathsApiV2.XRF,
            xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            xrf_mock_objects.TEST_DATA_V2,
            xrf_mock_objects.TEST_DATASET_RECORD_ID,
            xrf_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.XRD,
            xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            xrd_mock_objects.TEST_DATA_V2,
            xrd_mock_objects.TEST_DATASET_RECORD_ID,
            xrd_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.STO,
            sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            sto_mock_objects.TEST_DATA_V2,
            sto_mock_objects.TEST_DATASET_RECORD_ID,
            sto_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
        ),
        (
            TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
            crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            crushed_rock_analysis_mock_objects.TEST_DATA,
            crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            crushed_rock_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL,
            res_sim_rock_physics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            res_sim_rock_physics_mock_objects.TEST_DATA,
            res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID,
            res_sim_rock_physics_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
            saturation_function_set_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            saturation_function_set_mock_objects.TEST_DATA,
            saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID,
            saturation_function_set_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
            coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            coretologdepthshift_mock_objects.TEST_DATA,
            coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID,
            coretologdepthshift_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ROLLER_OVEN_TEST,
            roller_oven_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            roller_oven_test_mock_objects.TEST_DATA,
            roller_oven_test_mock_objects.TEST_DATASET_RECORD_ID,
            roller_oven_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SATURATION_TEST,
            saturation_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            saturation_test_mock_objects.TEST_DATA,
            saturation_test_mock_objects.TEST_DATASET_RECORD_ID,
            saturation_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
            black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            black_oil_fluid_model_mock_objects.TEST_DATA,
            black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            black_oil_fluid_model_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL,
            compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            compositional_fluid_model_mock_objects.TEST_DATA,
            compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            compositional_fluid_model_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
            thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            thermal_compositional_fluid_model_mock_objects.TEST_DATA,
            thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            thermal_compositional_fluid_model_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_data_json_no_ddmsdatasets_field(
    data_endpoint_path,
    record_data,
    test_data,
    test_dataset_record_id,
    test_ddms_urn,
):
    version = _version_from_urn(test_ddms_urn)
    del record_data["data"]["DDMSDatasets"]
    with post_overrides(record_data, test_dataset_record_id, test_data):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=_headers_json(version),
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
            TestContentPathsApiV2.ATMOSPHERIC_FLASH,
            atmospheric_flash_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            atmospheric_flash_mock_objects.TEST_DATASET_RECORD_ID,
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
            TestContentPathsApiV2.VLE,
            vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
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
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
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
            isotopes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            isotopes_mock_objects.TEST_DATASET_RECORD_ID,
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
            uniaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            uniaxial_mock_objects.TEST_DATASET_RECORD_ID,
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
            triaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            triaxial_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.PROPPANT_EMBEDMENT,
            proppant_embedment_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            proppant_embedment_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
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
            TestContentPathsApiV2.XRF,
            xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
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
            TestContentPathsApiV2.XRD,
            xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
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
            TestContentPathsApiV2.STO,
            sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            sto_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
            crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL,
            res_sim_rock_physics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
            saturation_function_set_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
            coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.ROLLER_OVEN_TEST,
            roller_oven_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            roller_oven_test_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.SATURATION_TEST,
            saturation_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            saturation_test_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
            black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL,
            compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
        ),
        (
            TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
            thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_data_parquet_empty(data_endpoint_path, record_data, test_dataset_record_id):
    version = _version_from_urn(record_data["data"]["DDMSDatasets"][0])
    with post_overrides(record_data, test_dataset_record_id):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=_headers_parquet(version),
                content=b"",
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


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
            TestContentPathsApiV2.ATMOSPHERIC_FLASH,
            atmospheric_flash_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            atmospheric_flash_mock_objects.TEST_DATA,
            atmospheric_flash_mock_objects.TEST_DATASET_RECORD_ID,
            atmospheric_flash_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            TestContentPathsApiV2.VLE,
            vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            vle_mock_objects.TEST_DATA_V2,
            vle_mock_objects.TEST_DATASET_RECORD_ID,
            vle_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.SLIMTUBE,
            slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            slimtube_mock_objects.TEST_DATA_V2,
            slimtube_mock_objects.TEST_DATASET_RECORD_ID,
            slimtube_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            relative_permeability_mock_objects.TEST_DATA_V2,
            relative_permeability_mock_objects.TEST_DATASET_RECORD_ID,
            relative_permeability_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            isotopes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            isotopes_mock_objects.TEST_DATA,
            isotopes_mock_objects.TEST_DATASET_RECORD_ID,
            isotopes_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            uniaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            uniaxial_mock_objects.TEST_DATA,
            uniaxial_mock_objects.TEST_DATASET_RECORD_ID,
            uniaxial_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            triaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            triaxial_mock_objects.TEST_DATA,
            triaxial_mock_objects.TEST_DATASET_RECORD_ID,
            triaxial_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.PROPPANT_EMBEDMENT,
            proppant_embedment_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            proppant_embedment_mock_objects.TEST_DATA,
            proppant_embedment_mock_objects.TEST_DATASET_RECORD_ID,
            proppant_embedment_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cappressure_mock_objects.TEST_DATA,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            cappressure_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            cappressure_mock_objects.TEST_DATA_V2,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            cappressure_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
        ),
        (
            TestContentPathsApiV2.CAP_SUCTION_TIME,
            capillary_suction_time_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            capillary_suction_time_mock_objects.TEST_DATA,
            capillary_suction_time_mock_objects.TEST_DATASET_RECORD_ID,
            capillary_suction_time_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            TestContentPathsApiV2.XRF,
            xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            xrf_mock_objects.TEST_DATA_V2,
            xrf_mock_objects.TEST_DATASET_RECORD_ID,
            xrf_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.XRD,
            xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            xrd_mock_objects.TEST_DATA_V2,
            xrd_mock_objects.TEST_DATASET_RECORD_ID,
            xrd_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.STO,
            sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            sto_mock_objects.TEST_DATA_V2,
            sto_mock_objects.TEST_DATASET_RECORD_ID,
            sto_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
        ),
        (
            TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
            crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            crushed_rock_analysis_mock_objects.TEST_DATA,
            crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            crushed_rock_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL,
            res_sim_rock_physics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            res_sim_rock_physics_mock_objects.TRIMMED_TEST_DATA,
            res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID,
            res_sim_rock_physics_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
            saturation_function_set_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            saturation_function_set_mock_objects.TRIMMED_TEST_DATA,
            saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID,
            saturation_function_set_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
            coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            coretologdepthshift_mock_objects.TRIMMED_TEST_DATA,
            coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID,
            coretologdepthshift_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ROLLER_OVEN_TEST,
            roller_oven_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            roller_oven_test_mock_objects.TRIMMED_TEST_DATA,
            roller_oven_test_mock_objects.TEST_DATASET_RECORD_ID,
            roller_oven_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SATURATION_TEST,
            saturation_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            saturation_test_mock_objects.TEST_DATA,
            saturation_test_mock_objects.TEST_DATASET_RECORD_ID,
            saturation_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
            black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            black_oil_fluid_model_mock_objects.TRIMMED_TEST_DATA,
            black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            black_oil_fluid_model_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL,
            compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            compositional_fluid_model_mock_objects.TRIMMED_TEST_DATA,
            compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            compositional_fluid_model_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
            thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            thermal_compositional_fluid_model_mock_objects.TRIMMED_TEST_DATA,
            thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            thermal_compositional_fluid_model_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_data_parquet(data_endpoint_path, record_data, test_data, test_dataset_record_id, test_ddms_urn):
    version = _version_from_urn(record_data["data"]["DDMSDatasets"][0])
    dataframe = pd.DataFrame(test_data["data"], columns=test_data["columns"])

    with post_overrides(record_data, test_dataset_record_id, dataframe):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=_headers_parquet(version),
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
            TestContentPathsApiV2.ATMOSPHERIC_FLASH,
            atmospheric_flash_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            atmospheric_flash_mock_objects.TEST_DATA,
            atmospheric_flash_mock_objects.TEST_DATASET_RECORD_ID,
            atmospheric_flash_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            TestContentPathsApiV2.VLE,
            vle_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            vle_mock_objects.TEST_DATA_V2,
            vle_mock_objects.TEST_DATASET_RECORD_ID,
            vle_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.SLIMTUBE,
            slimtube_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            slimtube_mock_objects.TEST_DATA_V2,
            slimtube_mock_objects.TEST_DATASET_RECORD_ID,
            slimtube_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            relative_permeability_mock_objects.TEST_DATA_V2,
            relative_permeability_mock_objects.TEST_DATASET_RECORD_ID,
            relative_permeability_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            isotopes_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            isotopes_mock_objects.TEST_DATA,
            isotopes_mock_objects.TEST_DATASET_RECORD_ID,
            isotopes_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            uniaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            uniaxial_mock_objects.TEST_DATA,
            uniaxial_mock_objects.TEST_DATASET_RECORD_ID,
            uniaxial_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            triaxial_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            triaxial_mock_objects.TEST_DATA,
            triaxial_mock_objects.TEST_DATASET_RECORD_ID,
            triaxial_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.PROPPANT_EMBEDMENT,
            proppant_embedment_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            proppant_embedment_mock_objects.TEST_DATA,
            proppant_embedment_mock_objects.TEST_DATASET_RECORD_ID,
            proppant_embedment_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            cappressure_mock_objects.TEST_DATA,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            cappressure_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            cappressure_mock_objects.TEST_DATA_V2,
            cappressure_mock_objects.TEST_DATASET_RECORD_ID,
            cappressure_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
        ),
        (
            TestContentPathsApiV2.CAP_SUCTION_TIME,
            capillary_suction_time_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            capillary_suction_time_mock_objects.TEST_DATA,
            capillary_suction_time_mock_objects.TEST_DATASET_RECORD_ID,
            capillary_suction_time_mock_objects.TEST_DDMS_URN_WITH_VERSION,
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
            TestContentPathsApiV2.XRF,
            xrf_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            xrf_mock_objects.TEST_DATA_V2,
            xrf_mock_objects.TEST_DATASET_RECORD_ID,
            xrf_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.XRD,
            xrd_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            xrd_mock_objects.TEST_DATA_V2,
            xrd_mock_objects.TEST_DATASET_RECORD_ID,
            xrd_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
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
            TestContentPathsApiV2.STO,
            sto_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION_V2,
            sto_mock_objects.TEST_DATA_V2,
            sto_mock_objects.TEST_DATASET_RECORD_ID,
            sto_mock_objects.TEST_DDMS_URN_WITH_VERSION_V2,
        ),
        (
            TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS,
            crushed_rock_analysis_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            crushed_rock_analysis_mock_objects.TEST_DATA,
            crushed_rock_analysis_mock_objects.TEST_DATASET_RECORD_ID,
            crushed_rock_analysis_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL,
            res_sim_rock_physics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            res_sim_rock_physics_mock_objects.TEST_DATA,
            res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID,
            res_sim_rock_physics_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
            saturation_function_set_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            saturation_function_set_mock_objects.TEST_DATA,
            saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID,
            saturation_function_set_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
            coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            coretologdepthshift_mock_objects.TEST_DATA,
            coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID,
            coretologdepthshift_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.ROLLER_OVEN_TEST,
            roller_oven_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            roller_oven_test_mock_objects.TEST_DATA,
            roller_oven_test_mock_objects.TEST_DATASET_RECORD_ID,
            roller_oven_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.SATURATION_TEST,
            saturation_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            saturation_test_mock_objects.TEST_DATA,
            saturation_test_mock_objects.TEST_DATASET_RECORD_ID,
            saturation_test_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
            black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            black_oil_fluid_model_mock_objects.TEST_DATA,
            black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            black_oil_fluid_model_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL,
            compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            compositional_fluid_model_mock_objects.TEST_DATA,
            compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            compositional_fluid_model_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
        (
            TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
            thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
            thermal_compositional_fluid_model_mock_objects.TEST_DATA,
            thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
            thermal_compositional_fluid_model_mock_objects.TEST_DDMS_URN_WITH_VERSION,
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_data_new_dataset(data_endpoint_path, record_data, test_data, test_dataset_record_id, test_ddms_urn):
    version = _version_from_urn(record_data["data"]["DDMSDatasets"][0])
    with post_overrides(record_data, test_dataset_record_id, test_data):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=_headers_json(version),
                content=json.dumps(test_data),
            )
            body = response.json()
    assert body["ddms_urn"] == test_ddms_urn


@pytest.mark.parametrize(
    "data_endpoint_path, incorrect_schema_test_data",
    [
        (TestContentPathsApiV2.RCA, rca_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.CCE, cce_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.DIFF_LIB, diff_lib_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.TRANSPORT_TEST, transport_test_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS, compositional_analysis_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.ATMOSPHERIC_FLASH, atmospheric_flash_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
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
        (TestContentPathsApiV2.ISOTOPE_ANALYSIS, isotopes_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.BULK_PYROLYSIS, bulk_pyrolysis_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.CORE_GAMMA, core_gamma_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.MINING_GEOTECH_LOGGING, mining_geotech_logging_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.UNIAXIAL_TEST, uniaxial_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.GCMSMS_ANALYSIS, gcmsms_analysis_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.CEC_CONTENT, cec_content_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.ELECTRICAL_PROPERTIES, electricalproperties_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.TRIAXIAL_TEST, triaxial_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.PROPPANT_EMBEDMENT, proppant_embedment_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.CAP_PRESSURE, cappressure_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.CAP_SUCTION_TIME, capillary_suction_time_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
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
        (
            TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL,
            res_sim_rock_physics_mock_objects.INCORRECT_SCHEMA_TEST_DATA,
        ),
        (
            TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
            saturation_function_set_mock_objects.INCORRECT_SCHEMA_TEST_DATA,
        ),
        (
            TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
            coretologdepthshift_mock_objects.INCORRECT_SCHEMA_TEST_DATA,
        ),
        (TestContentPathsApiV2.ROLLER_OVEN_TEST, roller_oven_test_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (TestContentPathsApiV2.SATURATION_TEST, saturation_test_mock_objects.INCORRECT_SCHEMA_TEST_DATA),
        (
            TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
            black_oil_fluid_model_mock_objects.INCORRECT_SCHEMA_TEST_DATA,
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL,
            compositional_fluid_model_mock_objects.INCORRECT_SCHEMA_TEST_DATA,
        ),
        (
            TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
            thermal_compositional_fluid_model_mock_objects.INCORRECT_SCHEMA_TEST_DATA,
        ),
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
    "data_endpoint_path,incorrect_dataframe_data,error_reason",
    [
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
            TestContentPathsApiV2.ATMOSPHERIC_FLASH,
            atmospheric_flash_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            atmospheric_flash_mock_objects.EXPECTED_ERROR_REASON,
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
            isotopes_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            isotopes_mock_objects.EXPECTED_ERROR_REASON,
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
            uniaxial_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            uniaxial_mock_objects.EXPECTED_ERROR_REASON,
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
            triaxial_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            triaxial_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.PROPPANT_EMBEDMENT,
            proppant_embedment_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            proppant_embedment_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.CAP_PRESSURE,
            cappressure_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            cappressure_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.CAP_SUCTION_TIME,
            capillary_suction_time_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            capillary_suction_time_mock_objects.EXPECTED_ERROR_REASON,
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
            TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL,
            res_sim_rock_physics_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            res_sim_rock_physics_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
            saturation_function_set_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            saturation_function_set_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
            coretologdepthshift_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            coretologdepthshift_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.ROLLER_OVEN_TEST,
            roller_oven_test_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            roller_oven_test_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.SATURATION_TEST,
            saturation_test_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            saturation_test_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
            black_oil_fluid_model_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            black_oil_fluid_model_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL,
            compositional_fluid_model_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            compositional_fluid_model_mock_objects.EXPECTED_ERROR_REASON,
        ),
        (
            TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
            thermal_compositional_fluid_model_mock_objects.INCORRECT_DATAFRAME_TEST_DATA,
            thermal_compositional_fluid_model_mock_objects.EXPECTED_ERROR_REASON,
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
    "data_endpoint_path",
    [
        f"{TestContentPathsApiV2.RCA}/{rca_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.CCE}/{cce_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.DIFF_LIB}/{diff_lib_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.TRANSPORT_TEST}/{transport_test_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS}/{compositional_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.ATMOSPHERIC_FLASH}/{atmospheric_flash_mock_objects.TEST_DATASET_RECORD_ID}",
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
        f"{TestContentPathsApiV2.ISOTOPE_ANALYSIS}/{isotopes_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.BULK_PYROLYSIS}/{bulk_pyrolysis_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.CORE_GAMMA}/{core_gamma_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.MINING_GEOTECH_LOGGING}/{mining_geotech_logging_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.UNIAXIAL_TEST}/{uniaxial_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.GCMSMS_ANALYSIS}/{gcmsms_analysis_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.CEC_CONTENT}/{cec_content_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.ELECTRICAL_PROPERTIES}/{electricalproperties_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.TRIAXIAL_TEST}/{triaxial_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.PROPPANT_EMBEDMENT}/{proppant_embedment_mock_objects.TEST_DATASET_RECORD_ID}",
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
        f"{TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL}/{res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL}/{saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.DEPTH_SHIFT_MODEL}/{coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.ROLLER_OVEN_TEST}/{roller_oven_test_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.SATURATION_TEST}/{saturation_test_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL}/{black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL}/{compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
        f"{TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL}/{thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}",
    ],
)
@pytest.mark.asyncio
async def test_get_403(data_endpoint_path):
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.get(
            data_endpoint_path,
            headers=TEST_HEADERS_NO_AUTH,
        )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "data_endpoint_path",
    [
        TestContentPathsApiV2.RCA,
        TestContentPathsApiV2.CCE,
        TestContentPathsApiV2.DIFF_LIB,
        TestContentPathsApiV2.TRANSPORT_TEST,
        TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS,
        TestContentPathsApiV2.ATMOSPHERIC_FLASH,
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
        TestContentPathsApiV2.PROPPANT_EMBEDMENT,
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
        TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL,
        TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
        TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
        TestContentPathsApiV2.ROLLER_OVEN_TEST,
        TestContentPathsApiV2.SATURATION_TEST,
        TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
        TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL,
        TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
    ],
)
@pytest.mark.asyncio
async def test_post_403(data_endpoint_path):
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.post(
            data_endpoint_path,
            headers=TEST_HEADERS_NO_AUTH,
        )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "data_endpoint_path,integrity_error_dataframe_data,missed_records",
    [
        (
            TestContentPathsApiV2.RCA,
            rca_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(rca_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.CCE,
            cce_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(cce_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.DIFF_LIB,
            diff_lib_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(diff_lib_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.TRANSPORT_TEST,
            transport_test_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(transport_test_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS,
            compositional_analysis_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(compositional_analysis_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.ATMOSPHERIC_FLASH,
            atmospheric_flash_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(atmospheric_flash_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.MSS,
            mss_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(mss_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.SWELLING,
            swelling_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(swelling_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.CVD,
            cvd_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(cvd_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.WATER_ANALYSIS,
            water_analysis_data_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(water_analysis_data_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.INTERFACIAL_TENSION,
            interfacial_tension_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(interfacial_tension_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.VLE,
            vle_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(vle_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.MCM,
            mcm_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(mcm_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.SLIMTUBE,
            slimtube_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(slimtube_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.EXTRACTION,
            extraction_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(extraction_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.FRACTIONATION,
            fractionation_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(fractionation_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.RELATIVE_PERMEABILITY,
            relative_permeability_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(relative_permeability_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.ROCK_COMPRESSIBILITY,
            rock_compressibility_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(rock_compressibility_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.ROLLER_OVEN_TEST,
            roller_oven_test_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(roller_oven_test_mock_objects.TEST_DATA)),
            ),
        ),
        (
            TestContentPathsApiV2.SATURATION_TEST,
            saturation_test_mock_objects.TEST_DATA,
            list(
                find_osdu_ids_from_string(json.dumps(saturation_test_mock_objects.TEST_DATA)),
            ),
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_integrity_error(
    data_endpoint_path, integrity_error_dataframe_data, missed_records, with_patched_storage_failed_integrity_validation
):
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
        TestContentPathsApiV2.ATMOSPHERIC_FLASH,
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
        TestContentPathsApiV2.PROPPANT_EMBEDMENT,
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
        TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL,
        TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
        TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
        TestContentPathsApiV2.ROLLER_OVEN_TEST,
        TestContentPathsApiV2.SATURATION_TEST,
        TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
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

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    assert ["code", "reason", "errors"] == list(body.keys())
    assert body["reason"] == "Data validation failed."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,payloads",
    [
        (TestContentPathsApiV2.RCA, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.CCE, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.DIFF_LIB, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.TRANSPORT_TEST, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.COMPOSITIONAL_ANALYSIS, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.ATMOSPHERIC_FLASH, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.MSS, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.SWELLING, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.CVD, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.WATER_ANALYSIS, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.INTERFACIAL_TENSION, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.VLE, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.MCM, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.SLIMTUBE, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.EXTRACTION, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.FRACTIONATION, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.RELATIVE_PERMEABILITY, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.ROCK_COMPRESSIBILITY, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.NMR, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.MULTIPLE_SALINITY, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.GCMS_ALKANES, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.GCMS_AROMATICS, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.GCMS_RATIOS, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.GAS_CHROMATOGRAPHY, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.GAS_COMPOSITION, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.ISOTOPE_ANALYSIS, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.BULK_PYROLYSIS, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.CORE_GAMMA, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.MINING_GEOTECH_LOGGING, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.UNIAXIAL_TEST, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.GCMSMS_ANALYSIS, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.CEC_CONTENT, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.ELECTRICAL_PROPERTIES, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.TRIAXIAL_TEST, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.PROPPANT_EMBEDMENT, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.CAP_PRESSURE, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.WETTABILITY_INDEX, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.TEC, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.EDS_MAPPING, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.XRF, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.TENSILE_STRENGTH, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.VITRINITE_REFLECTANCE, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.XRD, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.PDP, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.STO, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.CRUSHED_ROCK_ANALYSIS, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.ROLLER_OVEN_TEST, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.SATURATION_TEST, ORIENT_SPLIT_422_PAYLOADS),
        (TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL, ORIENT_SPLIT_422_PAYLOADS),
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

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        body = response.json()
        print(body)
        assert ["code", "reason"] == list(body.keys())
        assert body["reason"].startswith("Data error:")


# Issue #678 — SamplesAnalysisID mismatch validation

_MISMATCHED_SAMPLESANALYSIS_ID = "opendes:work-product-component--SamplesAnalysis:wrong-record:"


def _rca_data_with_samples_analysis_id(samples_analysis_id):
    """Return a copy of RCA test data with the given SamplesAnalysisID."""
    data = _copy.deepcopy(rca_mock_objects.TEST_DATA)
    col_idx = data["columns"].index("SamplesAnalysisID")
    for row in data["data"]:
        row[col_idx] = samples_analysis_id
    return data


@pytest.mark.asyncio
async def test_post_data_rejects_mismatched_samplesanalysis_id():
    """Issue #678: SamplesAnalysisID in payload must match record_id in URL."""
    payload = _rca_data_with_samples_analysis_id(_MISMATCHED_SAMPLESANALYSIS_ID)
    with post_overrides(
        rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION, rca_mock_objects.TEST_DATASET_RECORD_ID, payload
    ):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                TestContentPathsApiV2.RCA,
                headers=_headers_json("1.0.0"),
                content=json.dumps(payload),
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    assert body["reason"] == "Data validation failed."
    assert "Invalid value" in body["errors"]
    assert any("SamplesAnalysisID" in entry for entry in body["errors"]["Invalid value"])


@pytest.mark.asyncio
async def test_post_data_null_samplesanalysis_id_not_mismatch_error():
    """Issue #678: null SamplesAnalysisID triggers schema error (required field),
    NOT an ID mismatch error — null values are excluded from mismatch validation."""
    payload = _rca_data_with_samples_analysis_id(None)
    with post_overrides(
        rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION, rca_mock_objects.TEST_DATASET_RECORD_ID, payload
    ):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                TestContentPathsApiV2.RCA,
                headers=_headers_json("1.0.0"),
                content=json.dumps(payload),
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    assert body["reason"] == "Data validation failed."
    # Must be a schema error — not an ID mismatch
    assert "Invalid value" not in body.get("errors", {}) or not any(
        "SamplesAnalysisID" in entry for entry in body["errors"].get("Invalid value", [])
    )


# Issue #678 — SaturationFunctionSetID and ReservoirSimulationRockPhysicsID mismatch validation

_MISMATCHED_SFS_ID = "opendes:work-product-component--SaturationFunctionSet:wrong-record:"
_MISMATCHED_RSRPM_ID = "opendes:work-product-component--ReservoirSimulationRockPhysicsModel:wrong-record:"


def _sfs_data_with_id(value):
    data = _copy.deepcopy(saturation_function_set_mock_objects.TEST_DATA)
    col_idx = data["columns"].index("SaturationFunctionSetID")
    for row in data["data"]:
        row[col_idx] = value
    return data


def _rsrpm_data_with_id(value):
    data = _copy.deepcopy(res_sim_rock_physics_mock_objects.TEST_DATA)
    col_idx = data["columns"].index("ReservoirSimulationRockPhysicsID")
    for row in data["data"]:
        row[col_idx] = value
    return data


@pytest.mark.asyncio
async def test_post_sfs_data_rejects_mismatched_id():
    """Issue #678: SaturationFunctionSetID in payload must match record_id in URL."""
    payload = _sfs_data_with_id(_MISMATCHED_SFS_ID)
    with post_overrides(
        saturation_function_set_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
        saturation_function_set_mock_objects.TEST_DATASET_RECORD_ID,
        payload,
    ):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                TestContentPathsApiV2.SATURATION_FUNCTION_SET_MODEL,
                headers=_headers_json("1.0.0"),
                content=json.dumps(payload),
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    assert body["reason"] == "Data validation failed."
    assert "Invalid value" in body["errors"]
    assert any("SaturationFunctionSetID" in entry for entry in body["errors"]["Invalid value"])


@pytest.mark.asyncio
async def test_post_rsrpm_data_rejects_mismatched_id():
    """Issue #678: ReservoirSimulationRockPhysicsID in payload must match record_id in URL."""
    payload = _rsrpm_data_with_id(_MISMATCHED_RSRPM_ID)
    with post_overrides(
        res_sim_rock_physics_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
        res_sim_rock_physics_mock_objects.TEST_DATASET_RECORD_ID,
        payload,
    ):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                TestContentPathsApiV2.RES_SIM_ROCK_PHYSICS_MODEL,
                headers=_headers_json("1.0.0"),
                content=json.dumps(payload),
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    assert body["reason"] == "Data validation failed."
    assert "Invalid value" in body["errors"]
    assert any("ReservoirSimulationRockPhysicsID" in entry for entry in body["errors"]["Invalid value"])


# Issue #678 — DepthShiftWPCID mismatch validation

_MISMATCHED_DS_WPC_ID = "opendes:work-product-component--DepthShift:wrong-record:"


def _ds_data_with_id(value):
    data = _copy.deepcopy(coretologdepthshift_mock_objects.TEST_DATA)
    col_idx = data["columns"].index("DepthShiftWPCID")
    for row in data["data"]:
        row[col_idx] = value
    return data


@pytest.mark.asyncio
async def test_post_ds_data_rejects_mismatched_id():
    """Issue #678: DepthShiftWPCID in payload must match record_id in URL."""
    payload = _ds_data_with_id(_MISMATCHED_DS_WPC_ID)
    with post_overrides(
        coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
        coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID,
        payload,
    ):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
                headers=_headers_json("1.0.0"),
                content=json.dumps(payload),
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    assert body["reason"] == "Data validation failed."
    assert "Invalid value" in body["errors"]
    assert any("DepthShiftWPCID" in entry for entry in body["errors"]["Invalid value"])


@pytest.mark.asyncio
async def test_post_ds_data_rejects_multi_row_payload():
    """POST CoreToLog with more than one row must be rejected at write time with 422."""
    single_row = coretologdepthshift_mock_objects.TEST_DATA
    multi_row = {
        "columns": single_row["columns"],
        "index": [0, 1],
        "data": [single_row["data"][0], single_row["data"][0]],
    }
    with post_overrides(
        coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
        coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID,
        multi_row,
    ):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
                headers=_headers_json("1.0.0"),
                content=json.dumps(multi_row),
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "exactly 1 row" in response.json()["reason"]


@pytest.mark.asyncio
async def test_post_ds_data_rejects_null_depth_shift_values():
    """POST CoreToLog with a null depth boundary in DepthShiftSet must be rejected with 422.

    For JSON payloads, schema validation catches null values before the parquet
    validator runs, returning an "Invalid type" error for DepthShiftSet.
    The parquet-path validator (validate_shift_values) provides the same guard
    for x-parquet ingestion that bypasses schema validation.
    """
    null_payload = {
        "columns": coretologdepthshift_mock_objects.TEST_DATA["columns"],
        "index": [0],
        "data": [
            [
                "partition:work-product-component--DepthShift:depth_shift_test_id:",
                [],
                [
                    {
                        "OriginalTopDepth": None,
                        "OriginalBaseDepth": 1010.0,
                        "ShiftedTopDepth": 1001.5,
                        "ShiftedBaseDepth": 1011.5,
                    }
                ],
            ]
        ],
    }
    with post_overrides(
        coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
        coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID,
        null_payload,
    ):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                TestContentPathsApiV2.DEPTH_SHIFT_MODEL,
                headers=_headers_json("1.0.0"),
                content=json.dumps(null_payload),
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    # Schema validation catches null before the parquet validator; either path produces 422.
    assert "DepthShiftSet" in str(body)


@pytest.mark.asyncio
async def test_get_data_with_null_depth_shift_values_returns_422():
    """GET with depth_shift_id returns 422 when the CoreToLog parquet has null depth boundaries."""
    from tests.test_api.test_routes.api_v2.routinecoreanalysis import rca_mock_objects

    null_shift_set = [
        {
            "OriginalTopDepth": 1000.0,
            "OriginalBaseDepth": None,
            "ShiftedTopDepth": 1001.5,
            "ShiftedBaseDepth": 1011.5,
        }
    ]
    null_coretolog_df = pd.DataFrame(
        [
            [
                "partition:work-product-component--DepthShift:depth_shift_test_id:",
                [],
                null_shift_set,
            ]
        ],
        columns=["DepthShiftWPCID", "Meta", "DepthShiftSet"],
    )
    null_coretolog_parquet = null_coretolog_df.to_parquet()

    storage_side_effects = [
        rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
        _DEPTH_SHIFT_WPC_WITH_DATASETS,
    ]
    dataset_side_effects = [
        _build_rca_parquet(),
        null_coretolog_parquet,
    ]
    query_records_response = {
        "records": [_DEPTH_SHIFT_SAMPLE_RECORD],
    }
    with patch.object(async_storage_record_service_mock, "get_record", side_effect=storage_side_effects):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=dataset_side_effects):
            with patch.object(
                async_storage_record_service_mock,
                "query_records",
                new_callable=AsyncMock,
                return_value=query_records_response,
            ):
                with services_overrides():
                    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                        response = await client.get(
                            f"{TestContentPathsApiV2.RCA}/{rca_mock_objects.TEST_DATASET_RECORD_ID}",
                            headers=_headers_json("1.0.0"),
                            params={
                                "depth_shift_id": TEST_DEPTH_SHIFT_ID,
                                "depth_shift_policy": "id_provided",
                            },
                        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "null" in response.json()["reason"].lower()
    assert "OriginalBaseDepth" in response.json()["reason"]


# ---------------------------------------------------------------------------
# Issue #751 — Depth-shift augmentation on SA GET data
# ---------------------------------------------------------------------------

_RCA_SAMPLE_ID = "opendes:master-data--Sample:Example_Sample:"

_DEPTH_SHIFT_SAMPLE_RECORD = {
    "id": _RCA_SAMPLE_ID,
    "kind": "osdu:wks:master-data--Sample:2.0.0",
    "data": {
        "WellboreID": "namespace:master-data--Wellbore:wellbore-001:",
        "DepthMeasurements": [
            {
                "VerticalMeasurementTypeID": "osdu:reference-data--VerticalMeasurementType:SampleTop:",
                "VerticalMeasurement": 1005.0,
                "VerticalMeasurementSourceID": "osdu:reference-data--VerticalMeasurementSource:DRL:",
            },
            {
                "VerticalMeasurementTypeID": "osdu:reference-data--VerticalMeasurementType:SampleBase:",
                "VerticalMeasurement": 1008.0,
                "VerticalMeasurementSourceID": "osdu:reference-data--VerticalMeasurementSource:DRL:",
            },
        ],
    },
}

_DEPTH_SHIFT_SAMPLE_RECORD_OTHER_WELLBORE = {
    **_DEPTH_SHIFT_SAMPLE_RECORD,
    "id": "opendes:master-data--Sample:Example_Sample_2:",
    "data": {
        **_DEPTH_SHIFT_SAMPLE_RECORD["data"],
        "SampleAcquisition": {
            "SampleAcquisitionDetail": {
                "WellboreID": "namespace:master-data--Wellbore:wellbore-002:",
            },
        },
    },
}

_DEPTH_SHIFT_WPC_WITH_DATASETS = {
    **coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
    "kind": TEST_DEPTH_SHIFT_KIND,
    "data": {
        **coretologdepthshift_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION.get("data", {}),
        "WellboreID": "namespace:master-data--Wellbore:wellbore-001:",
    },
}


def _build_coretolog_parquet():
    """Build CoreToLog parquet bytes from the existing mock fixture."""
    coretolog_df = pd.DataFrame(
        coretologdepthshift_mock_objects.TEST_DATA["data"],
        columns=coretologdepthshift_mock_objects.TEST_DATA["columns"],
    )
    return coretolog_df.to_parquet()


def _build_rca_parquet():
    """Build RCA parquet bytes from the existing mock fixture."""
    from tests.test_api.test_routes.api_v2.routinecoreanalysis import rca_mock_objects

    rca_df = pd.DataFrame(
        rca_mock_objects.TEST_DATA["data"],
        columns=rca_mock_objects.TEST_DATA["columns"],
    )
    return rca_df.to_parquet()


@pytest.mark.asyncio
async def test_get_data_with_depth_shift_id_returns_augmented_columns():
    """Issue #751: GET data with ?depth_shift_id returns augmented columns."""
    from tests.test_api.test_routes.api_v2.routinecoreanalysis import rca_mock_objects

    depth_shift_wpc_id = TEST_DEPTH_SHIFT_ID
    coretolog_dataset_id = coretologdepthshift_mock_objects.TEST_DATASET_RECORD_ID
    rca_content_id = rca_mock_objects.TEST_DATASET_RECORD_ID
    rca_record_data = rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION

    # Base data is loaded first, then depth-shift WPC/parquet is fetched.
    storage_side_effects = [
        rca_record_data,
        _DEPTH_SHIFT_WPC_WITH_DATASETS,
    ]
    dataset_side_effects = [
        _build_rca_parquet(),
        _build_coretolog_parquet(),
    ]
    query_records_response = {
        "records": [_DEPTH_SHIFT_SAMPLE_RECORD],
    }

    with patch.object(async_storage_record_service_mock, "get_record", side_effect=storage_side_effects):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=dataset_side_effects):
            with patch.object(
                async_storage_record_service_mock,
                "query_records",
                new_callable=AsyncMock,
                return_value=query_records_response,
            ):
                with services_overrides():
                    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                        response = await client.get(
                            f"{TestContentPathsApiV2.RCA}/{rca_content_id}",
                            headers=_headers_json("1.0.0"),
                            params={
                                "depth_shift_id": depth_shift_wpc_id,
                                "depth_shift_policy": "id_provided",
                            },
                        )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()

    # Depth-shift columns must NOT pollute the original schema columns.
    columns = body["columns"]
    for ds_col in ("SampleTop", "SampleBase", "ShiftedSampleTop", "ShiftedSampleBase", "DepthShiftWarnings"):
        assert ds_col not in columns, f"{ds_col} must not appear in main columns"

    # DepthShiftData must be a parallel list with per-row shift values.
    assert "DepthShiftData" in body
    depth_shift_data = body["DepthShiftData"]
    assert isinstance(depth_shift_data, list)
    assert len(depth_shift_data) == len(body["data"])
    first_ds_row = depth_shift_data[0]
    assert abs(first_ds_row["SampleTop"] - 1005.0) < 1e-6
    assert abs(first_ds_row["ShiftedSampleTop"] - 1006.5) < 1e-6
    assert isinstance(first_ds_row["DepthShiftWarnings"], list)
    assert "DepthShiftMetadata" in body
    metadata = body["DepthShiftMetadata"]
    assert isinstance(metadata["warnings"], list)


@pytest.mark.asyncio
async def test_get_data_with_depth_shift_id_rejects_multiple_wellbores():
    """Issue #751: mixed wellbore sample records must fail fast with 422."""
    from tests.test_api.test_routes.api_v2.routinecoreanalysis import rca_mock_objects

    depth_shift_wpc_id = TEST_DEPTH_SHIFT_ID
    rca_content_id = rca_mock_objects.TEST_DATASET_RECORD_ID
    rca_record_data = rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION

    storage_side_effects = [
        rca_record_data,
        _DEPTH_SHIFT_WPC_WITH_DATASETS,
    ]
    dataset_side_effects = [
        _build_rca_parquet(),
        _build_coretolog_parquet(),
    ]
    mixed_sample_records = {
        _DEPTH_SHIFT_SAMPLE_RECORD["id"]: _DEPTH_SHIFT_SAMPLE_RECORD,
        _DEPTH_SHIFT_SAMPLE_RECORD_OTHER_WELLBORE["id"]: _DEPTH_SHIFT_SAMPLE_RECORD_OTHER_WELLBORE,
    }

    with patch.object(async_storage_record_service_mock, "get_record", side_effect=storage_side_effects):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=dataset_side_effects):
            with patch(
                "app.api.routes.samplesanalysis.endpoints.DepthShiftResolver.fetch_sample_records",
                return_value=mixed_sample_records,
            ):
                with services_overrides():
                    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                        response = await client.get(
                            f"{TestContentPathsApiV2.RCA}/{rca_content_id}",
                            headers=_headers_json("1.0.0"),
                            params={
                                "depth_shift_id": depth_shift_wpc_id,
                                "depth_shift_policy": "id_provided",
                            },
                        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    assert "wellbore-scoped" in body["reason"].lower()


@pytest.mark.asyncio
async def test_get_data_with_depth_shift_id_without_policy_returns_400():
    """Issue #751: depth_shift_id without depth_shift_policy returns 400."""
    from tests.test_api.test_routes.api_v2.routinecoreanalysis import rca_mock_objects

    rca_content_id = rca_mock_objects.TEST_DATASET_RECORD_ID

    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{TestContentPathsApiV2.RCA}/{rca_content_id}",
                headers=_headers_json("1.0.0"),
                params={
                    "depth_shift_id": "ds-001",
                },
            )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_get_data_without_depth_shift_params_unchanged():
    """Issue #751: regression guard — no depth shift params → original response."""
    from tests.test_api.test_routes.api_v2.routinecoreanalysis import rca_mock_objects

    rca_content_id = rca_mock_objects.TEST_DATASET_RECORD_ID
    rca_record_data = rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION

    with patch.object(async_storage_record_service_mock, "get_record", side_effect=[rca_record_data]):
        with patch.object(
            async_dataset_service_mock,
            "download_file",
            side_effect=[build_get_test_data("x-parquet", rca_mock_objects.TEST_DATA)],
        ):
            with services_overrides():
                async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                    response = await client.get(
                        f"{TestContentPathsApiV2.RCA}/{rca_content_id}",
                        headers=_headers_json("1.0.0"),
                    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "ShiftedSampleTop" not in body["columns"]
    assert "DepthShiftWarnings" not in body["columns"]
    assert set(body["columns"]) == set(rca_mock_objects.TEST_DATA["columns"])


@pytest.mark.asyncio
async def test_get_data_definitive_policy_no_definitive_id_returns_422():
    """definitive policy with no sample DefinitiveDepthShiftID must fail with 422."""
    from tests.test_api.test_routes.api_v2.routinecoreanalysis import rca_mock_objects

    rca_content_id = rca_mock_objects.TEST_DATASET_RECORD_ID
    rca_record_data = rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION
    sample_record_no_definitive = {
        **_DEPTH_SHIFT_SAMPLE_RECORD,
        "data": {
            **_DEPTH_SHIFT_SAMPLE_RECORD["data"],
            "DefinitiveDepthShift": {},
        },
    }
    query_records_response = {"records": [sample_record_no_definitive]}

    with patch.object(async_storage_record_service_mock, "get_record", side_effect=[rca_record_data]):
        with patch.object(
            async_dataset_service_mock,
            "download_file",
            side_effect=[_build_rca_parquet()],
        ):
            with patch.object(
                async_storage_record_service_mock,
                "query_records",
                new_callable=AsyncMock,
                return_value=query_records_response,
            ):
                with services_overrides():
                    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                        response = await client.get(
                            f"{TestContentPathsApiV2.RCA}/{rca_content_id}",
                            headers=_headers_json("1.0.0"),
                            params={"depth_shift_policy": "definitive"},
                        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_get_data_id_provided_with_different_definitive_id_emits_warning():
    """Issue #751: id_provided + different definitive ID in sample → warning in DepthShiftWarnings."""
    from tests.test_api.test_routes.api_v2.routinecoreanalysis import rca_mock_objects

    provided_wpc_id = TEST_DEPTH_SHIFT_ID
    definitive_wpc_id = "opendes:work-product-component--DepthShift:definitive-001:"
    rca_content_id = rca_mock_objects.TEST_DATASET_RECORD_ID
    rca_record_data = rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION

    # Sample record that carries a DefinitiveDepthShiftID different from the provided one.
    sample_with_definitive = {
        **_DEPTH_SHIFT_SAMPLE_RECORD,
        "data": {
            **_DEPTH_SHIFT_SAMPLE_RECORD["data"],
            "DefinitiveDepthShift": {
                "DefinitiveDepthShiftID": definitive_wpc_id,
            },
        },
    }

    storage_side_effects = [
        rca_record_data,
        _DEPTH_SHIFT_WPC_WITH_DATASETS,
    ]
    dataset_side_effects = [
        _build_rca_parquet(),
        _build_coretolog_parquet(),
    ]
    query_records_response = {"records": [sample_with_definitive]}

    with patch.object(async_storage_record_service_mock, "get_record", side_effect=storage_side_effects):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=dataset_side_effects):
            with patch.object(
                async_storage_record_service_mock,
                "query_records",
                new_callable=AsyncMock,
                return_value=query_records_response,
            ):
                with services_overrides():
                    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                        response = await client.get(
                            f"{TestContentPathsApiV2.RCA}/{rca_content_id}",
                            headers=_headers_json("1.0.0"),
                            params={
                                "depth_shift_id": provided_wpc_id,
                                "depth_shift_policy": "id_provided",
                            },
                        )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()

    # Top-level DepthShiftMetadata must reflect id_provided with definitive available.
    assert "DepthShiftMetadata" in body
    metadata = body["DepthShiftMetadata"]
    assert metadata["appliedDepthShiftId"] == provided_wpc_id
    assert metadata["source"] == "user-provided"
    assert metadata["usedDefinitive"] is False
    assert metadata["definitiveDepthShiftAvailable"] is True

    # Conflict warning must appear in metadata.warnings (not as a top-level key).
    assert "DepthShiftWarnings" not in body
    metadata_warnings = metadata["warnings"]
    assert isinstance(metadata_warnings, list)
    normalized_definitive_id = get_id(definitive_wpc_id)
    conflict_warning = next(
        (w for w in metadata_warnings if normalized_definitive_id in w and provided_wpc_id in w),
        None,
    )
    assert conflict_warning is not None, (
        f"Expected a warning mentioning both definitive ID ({normalized_definitive_id}) "
        f"and provided ID ({provided_wpc_id}), got: {metadata_warnings}"
    )


@pytest.mark.asyncio
async def test_get_data_with_depth_shift_orient_records_returns_200():
    """orient=records + depth-shift must return 200 with a 'data' key (not crash with 500)."""
    from tests.test_api.test_routes.api_v2.routinecoreanalysis import rca_mock_objects

    rca_content_id = rca_mock_objects.TEST_DATASET_RECORD_ID
    rca_record_data = rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION

    storage_side_effects = [rca_record_data, _DEPTH_SHIFT_WPC_WITH_DATASETS]
    dataset_side_effects = [_build_rca_parquet(), _build_coretolog_parquet()]
    query_records_response = {"records": [_DEPTH_SHIFT_SAMPLE_RECORD]}

    with patch.object(async_storage_record_service_mock, "get_record", side_effect=storage_side_effects):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=dataset_side_effects):
            with patch.object(
                async_storage_record_service_mock,
                "query_records",
                new_callable=AsyncMock,
                return_value=query_records_response,
            ):
                with services_overrides():
                    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                        response = await client.get(
                            f"{TestContentPathsApiV2.RCA}/{rca_content_id}",
                            headers=_headers_json("1.0.0"),
                            params={
                                "depth_shift_id": TEST_DEPTH_SHIFT_ID,
                                "depth_shift_policy": "id_provided",
                                "orient": "records",
                            },
                        )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "data" in body, "orient=records response must have a 'data' key"
    assert isinstance(body["data"], list)
    assert "DepthShiftData" in body
    assert "DepthShiftMetadata" in body
    assert "DepthShiftWarnings" not in body


@pytest.mark.asyncio
async def test_search_data_with_depth_shift_params_returns_200_for_empty_results():
    """Valid depth-shift requests should pass through empty search results."""

    from tests.test_api.test_routes.osdu.storage_mock_objects import (
        SAMPLESANALYSIS_ENDPOINT_PATH,
    )

    with patch(
        "app.services.search.SearchService.find_records",
        new_callable=AsyncMock,
        return_value={"results": [], "cursor": None},
    ):
        with services_overrides():
            async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                response = await client.get(
                    f"{SAMPLESANALYSIS_ENDPOINT_PATH}/routinecoreanalysis/search/data",
                    headers=_headers_json("1.0.0"),
                    params={
                        "wellbore_id": "pastition:master-data--Wellbore:wellbore-001:",
                        "depth_shift_id": TEST_DEPTH_SHIFT_ID,
                        "depth_shift_policy": "id_provided",
                    },
                )

    assert response.status_code == status.HTTP_200_OK

    body = response.json()
    assert body["result"] == {
        "index": [],
        "columns": [],
        "data": [],
    }
    assert body["total_size"] == 0


@pytest.mark.asyncio
async def test_search_data_with_empty_results_and_depth_shift_without_wellbore_id_returns_422():
    """Empty search results must not bypass depth-shift scope validation."""

    from tests.test_api.test_routes.osdu.storage_mock_objects import (
        SAMPLESANALYSIS_ENDPOINT_PATH,
    )

    with patch(
        "app.services.search.SearchService.find_records",
        new_callable=AsyncMock,
        return_value={"results": [], "cursor": None},
    ):
        with services_overrides():
            async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                response = await client.get(
                    f"{SAMPLESANALYSIS_ENDPOINT_PATH}/routinecoreanalysis/search/data",
                    headers=_headers_json("1.0.0"),
                    params={
                        "depth_shift_id": TEST_DEPTH_SHIFT_ID,
                        "depth_shift_policy": "id_provided",
                    },
                )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    body = response.json()
    assert body["reason"] == ("Depth shift requires a wellbore-scoped search. " "Please provide wellbore_id parameter.")


@pytest.mark.asyncio
async def test_get_data_definitive_flat_path_recognized():
    """DefinitiveDepthShiftID stored flat at data.DefinitiveDepthShiftID (not nested) must be found."""
    from tests.test_api.test_routes.api_v2.routinecoreanalysis import rca_mock_objects

    rca_content_id = rca_mock_objects.TEST_DATASET_RECORD_ID
    rca_record_data = rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION

    # Sample with flat path — no nested DefinitiveDepthShift object.
    sample_flat_path = {
        **_DEPTH_SHIFT_SAMPLE_RECORD,
        "data": {
            **_DEPTH_SHIFT_SAMPLE_RECORD["data"],
            "DefinitiveDepthShiftID": TEST_DEPTH_SHIFT_ID,
        },
    }

    storage_side_effects = [rca_record_data, _DEPTH_SHIFT_WPC_WITH_DATASETS]
    dataset_side_effects = [_build_rca_parquet(), _build_coretolog_parquet()]
    query_records_response = {"records": [sample_flat_path]}

    with patch.object(async_storage_record_service_mock, "get_record", side_effect=storage_side_effects):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=dataset_side_effects):
            with patch.object(
                async_storage_record_service_mock,
                "query_records",
                new_callable=AsyncMock,
                return_value=query_records_response,
            ):
                with services_overrides():
                    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                        response = await client.get(
                            f"{TestContentPathsApiV2.RCA}/{rca_content_id}",
                            headers=_headers_json("1.0.0"),
                            params={"depth_shift_policy": "definitive"},
                        )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["DepthShiftMetadata"]["usedDefinitive"] is True
    assert body["DepthShiftMetadata"]["definitiveDepthShiftAvailable"] is True


# Issue #678 FluidModelID mismatch validation
_MISMATCHED_FM_ID = "partition:work-product-component--FluidModel:wrong-record:"

def _blfm_data_with_id(value):
    data = _copy.deepcopy(black_oil_fluid_model_mock_objects.TEST_DATA)
    col_idx = data["columns"].index("FluidModelID")
    for row in data["data"]:
        row[col_idx] = value
    return data


def _cfm_data_with_id(value):
    data = _copy.deepcopy(compositional_fluid_model_mock_objects.TEST_DATA)
    col_idx = data["columns"].index("FluidModelID")
    for row in data["data"]:
        row[col_idx] = value
    return data


def _tcfm_data_with_id(value):
    data = _copy.deepcopy(thermal_compositional_fluid_model_mock_objects.TEST_DATA)
    col_idx = data["columns"].index("FluidModelID")
    for row in data["data"]:
        row[col_idx] = value
    return data



@pytest.mark.asyncio
async def test_post_blfm_data_rejects_mismatched_id():
    """Issue #678: FluidModelID in payload must match record_id in URL."""
    payload = _blfm_data_with_id(_MISMATCHED_FM_ID)
    with post_overrides(
        black_oil_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
        black_oil_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
        payload,
    ):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL,
                headers=_headers_json("1.0.0"),
                content=json.dumps(payload),
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    assert body["reason"] == "Data validation failed."
    assert "Invalid value" in body["errors"]
    assert any("FluidModelID" in entry for entry in body["errors"]["Invalid value"])


@pytest.mark.asyncio
async def test_post_cfm_data_rejects_mismatched_id():
    """Issue #678: FluidModelID in payload must match record_id in URL."""
    payload = _cfm_data_with_id(_MISMATCHED_FM_ID)
    with post_overrides(
        compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
        compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
        payload,
    ):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                TestContentPathsApiV2.COMPOSITIONAL_FLUID_MODEL,
                headers=_headers_json("1.0.0"),
                content=json.dumps(payload),
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    assert body["reason"] == "Data validation failed."
    assert "Invalid value" in body["errors"]
    assert any("FluidModelID" in entry for entry in body["errors"]["Invalid value"])


@pytest.mark.asyncio
async def test_post_tcfm_data_rejects_mismatched_id():
    """Issue #678: FluidModelID in payload must match record_id in URL."""
    payload = _tcfm_data_with_id(_MISMATCHED_FM_ID)
    with post_overrides(
        thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
        thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID,
        payload,
    ):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL,
                headers=_headers_json("1.0.0"),
                content=json.dumps(payload),
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    assert body["reason"] == "Data validation failed."
    assert "Invalid value" in body["errors"]
    assert any("FluidModelID" in entry for entry in body["errors"]["Invalid value"])


@pytest.mark.parametrize(
    "record_id",
    [
        "not-a-fluid-model-id",
        "partition:work-product-component--WrongType:fluid_model_test_id:",
        "partition:work-product-component--FluidModel",
    ],
)
@pytest.mark.asyncio
async def test_post_tcfm_data_malformed_record_id_returns_422(record_id):
    """A record_id that does not match FM_ID_REGEX_STR must be rejected before any I/O."""
    from tests.test_api.test_routes.osdu.storage_mock_objects import (
        FLUID_MODEL_ENDPOINT_PATH,
        fluid_model_relative_paths_v2,
    )

    data_endpoint_path = (
        f"{FLUID_MODEL_ENDPOINT_PATH}/{record_id}"
        f"{fluid_model_relative_paths_v2.THERMAL_COMPOSITIONAL_FLUID_MODEL}"
    )
    with post_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                data_endpoint_path,
                headers=_headers_json("1.0.0"),
                content=json.dumps(thermal_compositional_fluid_model_mock_objects.TEST_DATA),
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# Thermal Fluid Model — GET /{record_id}/data/thermalcompositionalfluidmodel/{content_id}
# ---------------------------------------------------------------------------

_TCFM_DATA_PATH = f"{TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL}/{thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}"
_TCFM_HEADERS_NO_ACCEPT = {
    "data-partition-id": "opendes",
    "Authorization": "Bearer token",
}


@contextmanager
def _tcfm_get_patches(record_data=None, blob=None):
    """Patch storage/dataset so a thermal GET resolves to the fixture dataframe."""
    if record_data is None:
        record_data = thermal_compositional_fluid_model_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION
    if blob is None:
        blob = build_get_test_data("x-parquet", thermal_compositional_fluid_model_mock_objects.TEST_DATA)
    with patch.object(async_storage_record_service_mock, "get_record", return_value=record_data):
        with patch.object(async_dataset_service_mock, "download_file", return_value=blob) as download:
            yield download


@pytest.mark.parametrize(
    "record_id",
    [
        "not-a-fluid-model-id",
        "partition:work-product-component--WrongType:fluid_model_test_id:",
        "partition:work-product-component--FluidModel",
    ],
)
@pytest.mark.asyncio
async def test_get_tcfm_data_malformed_record_id_returns_422(record_id):
    """A record_id that does not match FM_ID_REGEX_STR must be rejected before any I/O."""
    from tests.test_api.test_routes.osdu.storage_mock_objects import (
        FLUID_MODEL_ENDPOINT_PATH,
        fluid_model_relative_paths_v2,
    )

    data_endpoint_path = (
        f"{FLUID_MODEL_ENDPOINT_PATH}/{record_id}"
        f"{fluid_model_relative_paths_v2.THERMAL_COMPOSITIONAL_FLUID_MODEL}"
        f"/{thermal_compositional_fluid_model_mock_objects.TEST_DATASET_RECORD_ID}"
    )
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(data_endpoint_path, headers=_headers_json("1.0.0"))

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    assert body["reason"] == "Unprocessable entity."
    assert any(
        "work-product-component--FluidModel ID is not provided in expected OSDU pattern" in entry
        for entry in body["errors"]
    )


@pytest.mark.parametrize(
    "content_id",
    [
        "not-a-dataset-id",
        "partition:dataset--File.Wrong:thermalcompositionalfluidmodel-1:",
        "12345678-1234-1234-1234",
    ],
)
@pytest.mark.asyncio
async def test_get_tcfm_data_malformed_content_id_returns_422(content_id):
    """A content_id matching neither the dataset nor the UUID pattern must return 422."""
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{TestContentPathsApiV2.THERMAL_COMPOSITIONAL_FLUID_MODEL}/{content_id}",
                headers=_headers_json("1.0.0"),
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    assert body["reason"] == "Unprocessable entity."
    assert any("content_id string does not match regex" in entry for entry in body["errors"])


@pytest.mark.parametrize("schema_version", ["abc", "1", "1.0.0.0", "v1.0.0", "1..0"])
@pytest.mark.asyncio
async def test_get_tcfm_data_malformed_content_schema_version_returns_422(schema_version):
    """A malformed content_schema_version query parameter must return 422."""
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                _TCFM_DATA_PATH,
                headers=_TCFM_HEADERS_NO_ACCEPT,
                params={"content_schema_version": schema_version},
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert (
        f"Invalid version format in content_schema_version: '{schema_version}'."
        " Expected format: major.minor.patch (e.g. 1.0.0)"
    ) in response.json()["reason"]


@pytest.mark.asyncio
async def test_get_tcfm_data_unimplemented_content_schema_version_returns_404():
    """A well-formed but unimplemented content schema version must return 404, not 422."""
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                _TCFM_DATA_PATH,
                headers=_TCFM_HEADERS_NO_ACCEPT,
                params={"content_schema_version": "9.0.0"},
            )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    reason = response.json()["reason"]
    assert "Model not found for type 'thermalcompositionalfluidmodel'" in reason
    assert "version '9.0.0'" in reason
    assert "1.0.0" in reason


@pytest.mark.asyncio
async def test_get_tcfm_data_no_schema_version_anywhere_returns_406():
    """Neither query parameter nor Accept header supplying a version must return 406."""
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(_TCFM_DATA_PATH, headers=_TCFM_HEADERS_NO_ACCEPT)

    assert response.status_code == status.HTTP_406_NOT_ACCEPTABLE
    assert "No schema version specified or invalid schema format" in response.json()["reason"]


@pytest.mark.asyncio
async def test_get_tcfm_data_query_schema_version_takes_priority_over_accept_header():
    """content_schema_version must win over a bogus version in the deprecated Accept header."""
    with services_overrides():
        with _tcfm_get_patches():
            async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                response = await client.get(
                    _TCFM_DATA_PATH,
                    headers={**_TCFM_HEADERS_NO_ACCEPT, "Accept": "application/json;version=9.0.0"},
                    params={"content_schema_version": "1.0.0"},
                )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize("accept", ["*/*", "application/json"])
@pytest.mark.asyncio
async def test_get_tcfm_data_defaults_to_json_for_absent_or_wildcard_accept(accept):
    """Wildcard or explicit JSON Accept must return JSON, with the version taken from the query.

    ``httpx`` always sends ``Accept: */*`` when the header is not set, so the
    genuinely-absent case is asserted directly against the dependency in
    ``test_get_tcfm_data_response_mime_type_defaults_to_json_without_accept``.
    """
    headers = {**_TCFM_HEADERS_NO_ACCEPT, "Accept": accept}

    with services_overrides():
        with _tcfm_get_patches():
            async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                response = await client.get(
                    _TCFM_DATA_PATH,
                    headers=headers,
                    params={"content_schema_version": "1.0.0"},
                )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("application/json")
    assert set(response.json()["columns"]) == set(thermal_compositional_fluid_model_mock_objects.TEST_DATA["columns"])


def test_get_tcfm_data_response_mime_type_defaults_to_json_without_accept():
    """With no Accept header at all the response MIME type must resolve to JSON."""
    from app.api.dependencies.request import get_response_mime_type
    from app.resources.mime_types import SupportedMimeTypes

    request = _tcfm_cache_request()
    assert get_response_mime_type(request) == SupportedMimeTypes.JSON


@pytest.mark.parametrize(
    "params,expected_message",
    [
        ({"columns_filter": "UnknownColumn"}, "Invalid columns:"),
        ({"rows_filter": "Invalid syntax"}, "Bad rows_filter expression. Correct format"),
        ({"rows_filter": "UnknownColumn,eq,x"}, "For filter select one of"),
        ({"rows_filter": "FluidModelID,equal,x"}, "Invalid comparison operator 'equal'"),
        ({"columns_aggregation": "UnknownColumn,describe"}, "For aggregation select one of"),
        ({"columns_aggregation": "FluidModelID,avg"}, "Invalid aggregation operator 'avg'"),
        ({"columns_aggregation": "FluidModelID"}, "Bad aggregation expression. Correct form"),
    ],
)
@pytest.mark.asyncio
async def test_get_tcfm_data_invalid_filter_params_return_422(params, expected_message):
    """Invalid columns_filter/rows_filter/columns_aggregation must return 422."""
    with services_overrides():
        with _tcfm_get_patches():
            async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                response = await client.get(
                    _TCFM_DATA_PATH,
                    headers=_TCFM_HEADERS_NO_ACCEPT,
                    params={"content_schema_version": "1.0.0", **params},
                )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert expected_message in response.json()["reason"]


def _tcfm_cache_request(token="Bearer token", partition="opendes", query="content_schema_version=1.0.0"):
    """Build a minimal GET request for the thermal data route, for cache key inspection."""
    from starlette.requests import Request

    return Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "server": ("testserver", 80),
            "root_path": "",
            "path": _TCFM_DATA_PATH,
            "raw_path": _TCFM_DATA_PATH.encode(),
            "query_string": query.encode(),
            "headers": [
                (b"authorization", token.encode()),
                (b"data-partition-id", partition.encode()),
            ],
        },
    )


def test_get_tcfm_data_cache_key_is_stable_for_identical_requests():
    """Identical thermal GET requests must resolve to one cache key, differing ones must not.

    The end-to-end TTL behaviour cannot be asserted here: ``tests/conftest.py``
    replaces ``fastapi_cache.decorator.cache`` with a pass-through for the whole
    unit suite.  What is verifiable in-process is the precondition the caching
    acceptance criterion rests on — that the key builder is deterministic per
    request and discriminates on token, partition and query parameters.  The
    served-from-cache behaviour itself is covered by the integration suite
    (``test_black_oil_get_data_returns_identical_response_inside_cache_ttl``)
    against the same shared route handler.
    """
    from app.api.routes.v2.data.endpoints import DynamicContentTypeDataViewV2
    from app.core.helpers.cache.key_builder import key_builder_using_token

    func = DynamicContentTypeDataViewV2.get_data_multiple_content_type

    def build_key(**request_kwargs):
        with patch("fastapi_cache.FastAPICache.get_prefix", return_value="rafs"):
            return key_builder_using_token(
                func,
                "",
                request=_tcfm_cache_request(**request_kwargs),
                response=None,
                args=(),
                kwargs={},
            )

    baseline = build_key()

    assert build_key() == baseline
    assert build_key(token="Bearer other-token") != baseline
    assert build_key(partition="other-partition") != baseline
    assert build_key(query="content_schema_version=1.0.0&columns_filter=FluidModelID") != baseline
# ---------------------------------------------------------------------------
# Issue #768 — lead review feedback: str-column corruption and general
# (non-depth-shift) parquet path coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_data_json_preserves_str_field_exact_value():
    """A str-typed field must round-trip through the JSON ingestion path unchanged.

    pd.read_json infers a numeric dtype for any numeric-looking string value.
    Without a per-column dtype hint, "001" loses its leading zero (becomes the
    float 1.0) before any defensive casting can recover it, and a naive
    str(float) cast renders whole numbers as "1.0" instead of "1". This must
    hold through the general POST /data JSON path, not just be a property of
    a single private helper function.
    """
    columns = transport_test_mock_objects.TEST_DATA["columns"]
    base_row = transport_test_mock_objects.TEST_DATA["data"][0]
    test_number_idx = columns.index("TestNumber")
    test_number_values = ["001", "1", None, "1A"]

    payload = {
        "columns": columns,
        "index": list(range(len(test_number_values))),
        "data": [
            [
                test_number_values[row_idx] if col_idx == test_number_idx else cell
                for col_idx, cell in enumerate(base_row)
            ]
            for row_idx in range(len(test_number_values))
        ],
    }

    uploaded_blobs = []

    class _CapturingDatasetService:
        async def upload_file(self, blob_file, dataset_id=None, parent_record=None):
            uploaded_blobs.append(blob_file)
            return transport_test_mock_objects.TEST_DATASET_RECORD_ID

    async def mock_get_capturing_dataset_service():
        yield _CapturingDatasetService()

    with post_overrides(
        transport_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
        transport_test_mock_objects.TEST_DATASET_RECORD_ID,
        payload,
    ):
        with dependencies.DependencyOverrider(app, {get_async_dataset_service: mock_get_capturing_dataset_service}):
            async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                response = await client.post(
                    TestContentPathsApiV2.TRANSPORT_TEST,
                    headers=_headers_json("1.0.0"),
                    content=json.dumps(payload),
                )

    assert response.status_code == status.HTTP_200_OK
    assert len(uploaded_blobs) == 1

    uploaded_df = pd.read_parquet(io.BytesIO(uploaded_blobs[0]))
    test_numbers = uploaded_df["TestNumber"].tolist()
    assert test_numbers[0] == "001"
    assert test_numbers[1] == "1"
    assert pd.isna(test_numbers[2])
    assert test_numbers[3] == "1A"


@pytest.mark.asyncio
async def test_post_data_parquet_accepts_null_scalar_and_nested_date_fields():
    """The general (non-depth-shift) POST /data parquet path must accept nullable
    optional scalar fields and a nested list field carrying a `date` value, not
    just the happy-path fixtures the shared parametrize list covers.

    Only the depth-shift-specific path had a regression test for nulled/nested
    values after the JSON round-trip workaround was removed from `_read_dataframe`
    (commit 5283b1bc); this exercises the same guarantee on a general record type.
    """
    columns = transport_test_mock_objects.TEST_DATA["columns"]
    base_row = transport_test_mock_objects.TEST_DATA["data"][0]
    test_steps_idx = columns.index("TestSteps")
    test_number_idx = columns.index("TestNumber")
    reservoir_pressure_idx = columns.index("ReservoirPressure")

    row_with_nested_date = list(base_row)
    row_with_nested_date[test_steps_idx] = [
        {
            **base_row[test_steps_idx][0],
            "Remarks": [
                {
                    "RemarkSequenceNumber": 1,
                    "Remark": "Logged during transport test.",
                    "RemarkSource": "Lab",
                    "RemarkDate": date(2024, 1, 1),
                },
            ],
        },
        *base_row[test_steps_idx][1:],
    ]

    row_with_nulls = list(base_row)
    row_with_nulls[test_number_idx] = None
    row_with_nulls[reservoir_pressure_idx] = None
    row_with_nulls[test_steps_idx] = None

    dataframe = pd.DataFrame([row_with_nested_date, row_with_nulls], columns=columns)

    with post_overrides(
        transport_test_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION,
        transport_test_mock_objects.TEST_DATASET_RECORD_ID,
        dataframe,
    ):
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                TestContentPathsApiV2.TRANSPORT_TEST,
                headers=_headers_parquet("1.0.0"),
                content=dataframe.to_parquet(),
            )

    assert response.status_code == status.HTTP_200_OK
