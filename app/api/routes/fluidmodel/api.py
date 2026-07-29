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

from app.api.dependencies.validation import validate_fluid_model_v2_payload
from app.api.routes.common.endpoints import (
    GenericSchemasView,
    build_extractor_for_param_name,
)
from app.api.routes.fluidmodel.endpoints import FluidModelRecordView
from app.api.routes.v2.data.endpoints import DynamicContentTypeDataViewV2
from app.models.data_schemas.base import MAPS_TO_DATA_MODEL
from app.resources.paths import FLUID_MODEL_STR

FM_ID_REGEX_STR = r"^[\w\-\.]+:work-product-component--FluidModel:[\w\-\.\:\%]+$"

fm_record_router_v2 = APIRouter(redirect_slashes=False)

FluidModelRecordView(
    router=fm_record_router_v2,
    id_regex_str=FM_ID_REGEX_STR,
    validate_records_payload=validate_fluid_model_v2_payload,
    record_type="FluidModel",
)

GenericSchemasView(
    router=fm_record_router_v2,
    endpoint_config={
        "path": "/{fluid_model_type}/data/schema",
        "mapping": MAPS_TO_DATA_MODEL["v2"][FLUID_MODEL_STR],
        "param_extractor": build_extractor_for_param_name("fluid_model_type"),
        "description": " ".join(
            [
                "Get the (`content schema`) for a given `{fluid_model_type}`. <br><br>",
                "Use the `content_schema_version` query parameter to specify content schema version ",
                "(e.g. `?content_schema_version=1.0.0`). The `Accept` header versioning is deprecated.",
            ],
        ),
    },
)

DynamicContentTypeDataViewV2(
    router=fm_record_router_v2,
    id_regex_str=FM_ID_REGEX_STR,
    multiple_content_type_param="fluid_model_type",
    record_id_column="FluidModelID",
)
