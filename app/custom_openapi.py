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

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.settings.app import AppSettings
from app.models.schemas.osdu_storage import OsduStorageRecord
from app.models.schemas.pandas_dataframe import OrientSplit
from app.resources.load_model_example import load_data_example


def get_custom_openapi_schema(app: FastAPI, settings: AppSettings) -> dict:
    """Override openapi with custom values.

    :param FastAPI app: FastAPI app
    :param AppSettings settings: App Settings
    :return dict: The openapi schema modified
    """
    custom_openapi_schema = get_openapi(
        title=settings.app_name,
        openapi_version="3.0.3",
        version=settings.app_version,
        routes=app.routes,
        description="OSDU Rock and Fluid Sample DDMS",
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
        },
    )
    base_path = custom_openapi_schema["paths"]
    # overrides
    base_path = custom_openapi_schema["paths"]
    content_post_v2_route = f"{settings.openapi_prefix}/v2/samplesanalysis/{{record_id}}/data/{{analysis_type}}"
    base_path[content_post_v2_route]["post"]["requestBody"] = {
        "content": {
            "application/json": {
                "schema": OrientSplit.schema(),
                "example": load_data_example("multiple_salinity.json"),
            },
        },
    }
    content_post_v2_route = f"{settings.openapi_prefix}/v2/saturationfunctionset/{{record_id}}/data"
    base_path[content_post_v2_route]["post"]["requestBody"] = {
        "content": {
            "application/json": {
                "schema": OrientSplit.schema(),
                "example": load_data_example("saturation_function_set_post_content_example.json"),
            },
        },
    }
    sampleanalysis_record_post_v2_route = f"{settings.openapi_prefix}/v2/samplesanalysis"
    request_body = base_path[sampleanalysis_record_post_v2_route]["post"]["requestBody"]
    samples_analysis_schema = request_body["content"]["application/json"]["schema"]
    base_path[sampleanalysis_record_post_v2_route]["post"]["requestBody"] = {
        "content": {
            "application/json": {
                "schema": samples_analysis_schema,
                "example": load_data_example("samples_analysis_v2.json"),
            },
        },
    }
    masterdata_record_post_v2_route = f"{settings.openapi_prefix}/v2/masterdata"
    base_path[masterdata_record_post_v2_route]["post"]["requestBody"] = {
        "content": {
            "application/json": {
                "schema": {
                    "title": "MasterDataRecords",
                    "description": "Master Data records payload",
                    "type": "array",
                    "items": OsduStorageRecord.schema(),
                },
                "example": load_data_example("master_data.json"),
            },
        },
    }
    rsrpm = "reservoirsimulationrockphysicsmodel"
    res_sim_content_post_v2_route = f"{settings.openapi_prefix}/v2/{rsrpm}/{{record_id}}/data"
    base_path[res_sim_content_post_v2_route]["post"]["requestBody"] = {
        "content": {
            "application/json": {
                "schema": OrientSplit.schema(),
                "example": load_data_example("reservoir_simulation_rock_physics_content_model.json"),
            },
        },
    }

    return custom_openapi_schema
