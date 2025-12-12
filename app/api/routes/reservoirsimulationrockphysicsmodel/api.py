#  Copyright 2025 ExxonMobil Technology and Engineering Company
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

from fastapi import APIRouter

from app.api.dependencies.validation import (
    validate_filters_for_domain_inferred_model,
    validate_reservoir_sim_rock_physics_payload,
)
from app.api.routes.common.dynamic_search import (
    DynamicGenericSearchView,
    get_search_data_description_template,
    get_search_description_template,
)
from app.api.routes.common.endpoints import (
    GenericSchemasView,
    infer_content_type_from_url,
)
from app.api.routes.reservoirsimulationrockphysicsmodel.endpoints import (
    ReservoirSimulationRockPhysicsRecordView,
)
from app.api.routes.v2.data.endpoints import DynamicContentTypeDataViewV2
from app.models.data_schemas.base import MAPS_TO_DATA_MODEL
from app.resources.paths import RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR
from app.search.res_sim_rock_physics_ids_fetcher import (
    SearchServiceResSimRockPhysicsIdsFetcher,
)

RSRP_ID_REGEX_STR = r"^[\w\-\.]+:work-product-component--ReservoirSimulationRockPhysicsModel:[\w\-\.\:\%]+$"
rsrp_router = APIRouter(redirect_slashes=False)
RECORD_TYPE = "ReservoirSimulationRockPhysicsModel"


# declare before ReservoirSimulationRockPhysicsRecordView for single content type to avoid path collision
DynamicGenericSearchView(
    router=rsrp_router,
    ddms_dataset_ids_fetcher_class=SearchServiceResSimRockPhysicsIdsFetcher,
    endpoints_config=[
        {
            "path": "/search",
            "handler": "get_search",
            "param_name": None,
            "filter_dep": validate_filters_for_domain_inferred_model,
            "description": get_search_description_template("ReservoirSimulationRockPhysicsModel"),
        },
        {
            "path": "/search/",  # declare the path with '/' to avoid collision with get wpc
            "handler": "get_search",
            "param_name": None,
            "filter_dep": validate_filters_for_domain_inferred_model,
            "description": get_search_description_template("ReservoirSimulationRockPhysicsModel"),
            "include_in_schema": False,
        },
        {
            "path": "/search/data",
            "handler": "get_search_data",
            "param_name": None,
            "filter_dep": validate_filters_for_domain_inferred_model,
            "description": get_search_data_description_template("ReservoirSimulationRockPhysicsModel"),
        },
    ],
)

ReservoirSimulationRockPhysicsRecordView(
    router=rsrp_router,
    id_regex_str=RSRP_ID_REGEX_STR,
    validate_records_payload=validate_reservoir_sim_rock_physics_payload,
    record_type=RECORD_TYPE,
)

GenericSchemasView(
    router=rsrp_router,
    endpoint_config={
        "path": "/data/schema",
        "mapping": MAPS_TO_DATA_MODEL["v2"][RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR],
        "param_extractor": infer_content_type_from_url,
        "description": " ".join([
            "Get the (`content schema`) for `{ReservoirSimulationRockPhysicsModel}`. <br><br>",
            "Use the `Accept` request header to specify content schema version ",
            "(example header `Accept: application/json;version=1.0.0` is supported).",
        ]),
    },
)

DynamicContentTypeDataViewV2(
    router=rsrp_router,
    id_regex_str=RSRP_ID_REGEX_STR,
    single_content_type=RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR,
)
