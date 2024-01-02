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

import pytest
from httpx import AsyncClient
from starlette import status

from app.main import app
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    SAMPLESANALYSIS_ENDPOINT_PATH,
    TEST_HEADERS,
    TEST_SERVER,
)


@pytest.mark.asyncio
async def test_types_route():
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.get(
            f"{SAMPLESANALYSIS_ENDPOINT_PATH}/analysistypes",
            headers=TEST_HEADERS,
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/json"

    response_json = response.json()
    assert isinstance(response_json, dict)
    assert response_json


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "analysistype", [
        "routinecoreanalysis",
        "constantcompositionexpansion",
        "differentialliberation",
        "transport",
        "multistageseparator",
        "compositionalanalysis",
        "swelling",
        "constantvolumedepletion",
        "wateranalysis",
        "interfacialtension",
        "vaporliquidequilibrium",
        "multiplecontactmiscibility",
        "slimtube",
        "extraction",
        "fractionation",
        "relativepermeability",
        "rockcompressibility",
        "watergasrelativepermeability",
        "capillarypressure",
        "electricalproperties",
        "nmr",
        "multiplesalinitytests",
        "gcmsalkanes",
        "gcmsaromatics",
        "gcmsratios",
        "gaschromatographyanalyses",
        "gascompositionanalyses",
        "isotopes",
        "bulkpyrolysisanalyses",
        "coregamma",
        "uniaxial",
        "gcmsms",
        "cec",
        "triaxial",
        "wettabilityindex",
        "tec",
        "edsmapping",
        "xrf",
        "tensilestrength",
        "xrd",
        "pdp",
        "stocktankoilanalysis",
    ],
)
async def test_content_schemas_route(analysistype):
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.get(
            f"{SAMPLESANALYSIS_ENDPOINT_PATH}/{analysistype}/data/schema",
            headers={**TEST_HEADERS, "Accept": "application/json;version=1.0.0"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/json"

    response_json = response.json()
    assert isinstance(response_json, dict)
    assert response_json


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "analysistype", [
        "routinecoreanalysis",
        "constantcompositionexpansion",
        "differentialliberation",
        "transport",
        "multistageseparator",
        "compositionalanalysis",
        "swelling",
        "constantvolumedepletion",
        "constantvolumedepletion",
        "wateranalysis",
        "interfacialtension",
        "vaporliquidequilibrium",
        "multiplecontactmiscibility",
        "slimtube",
        "extraction",
        "fractionation",
        "relativepermeability",
        "rockcompressibility",
        "watergasrelativepermeability",
        "capillarypressure",
        "electricalproperties",
        "nmr",
        "multiplesalinitytests",
        "gcmsalkanes",
        "gcmsaromatics",
        "gcmsratios",
        "gaschromatographyanalyses",
        "gascompositionanalyses",
        "isotopes",
        "bulkpyrolysisanalyses",
        "coregamma",
        "uniaxial",
        "gcmsms",
        "cec",
        "triaxial",
        "wettabilityindex",
        "tec",
        "edsmapping",
        "xrf",
        "tensilestrength",
        "xrd"
        "pdp",
        "stocktankoilanalysis",
    ],
)
async def test_content_schemas_wrong_version(analysistype):
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.get(
            f"{SAMPLESANALYSIS_ENDPOINT_PATH}/{analysistype}/data/schema",
            headers={**TEST_HEADERS, "Accept": "application/json;version=0.0.0"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["message"] == f"Schema not found for {analysistype} and version 0.0.0"


@pytest.mark.asyncio
async def test_content_schemas_wrong_type():
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.get(
            f"{SAMPLESANALYSIS_ENDPOINT_PATH}/wrongtype/data/schema",
            headers={**TEST_HEADERS, "Accept": "application/json;version=0.0.0"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["message"] == "Schema not found for wrongtype and version 0.0.0"
