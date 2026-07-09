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
    get_depth_shift_scope,
    validate_depth_shift_v2_payload,
    validate_filters_for_domain_inferred_model,
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
from app.api.routes.depthshift.endpoints import DepthShiftDataViewV2, DepthShiftRecordView
from app.models.data_schemas.base import MAPS_TO_DATA_MODEL
from app.resources.paths import DEPTH_SHIFT_STR
from app.search.depth_shift_ids_fetcher import SearchServiceDepthShiftIdsFetcher

DS_ID_REGEX_STR = r"^[\w\-\.]+:work-product-component--DepthShift:[\w\-\.\:\%]+$"

ds_record_router_v2 = APIRouter(redirect_slashes=False)

# declare before DepthShiftRecordView for single content type to avoid path collision
DynamicGenericSearchView(
    router=ds_record_router_v2,
    ddms_dataset_ids_fetcher_class=SearchServiceDepthShiftIdsFetcher,
    endpoints_config=[
        {
            "path": "/search",
            "handler": "get_search",
            "param_name": None,
            "filter_dep": validate_filters_for_domain_inferred_model,
            "scope_dep": get_depth_shift_scope,
            "description": get_search_description_template("DepthShift"),
        },
        {
            "path": "/search/",  # declare the path with '/' to avoid collision with get wpc
            "handler": "get_search",
            "param_name": None,
            "filter_dep": validate_filters_for_domain_inferred_model,
            "scope_dep": get_depth_shift_scope,
            "description": get_search_description_template("DepthShift"),
            "include_in_schema": False,
        },
        {
            "path": "/search/data",
            "handler": "get_search_data",
            "param_name": None,
            "filter_dep": validate_filters_for_domain_inferred_model,
            "scope_dep": get_depth_shift_scope,
            "description": get_search_data_description_template("DepthShift"),
        },
    ],
)

DepthShiftRecordView(
    router=ds_record_router_v2,
    id_regex_str=DS_ID_REGEX_STR,
    validate_records_payload=validate_depth_shift_v2_payload,
    record_type="DepthShift",
)

GenericSchemasView(
    router=ds_record_router_v2,
    endpoint_config={
        "path": "/data/schema",
        "mapping": MAPS_TO_DATA_MODEL["v2"][DEPTH_SHIFT_STR],
        "param_extractor": infer_content_type_from_url,
        "description": "Get the (`content schema`) for `{DepthShift}`. <br><br>"
        "Use the `content_schema_version` query parameter to specify content schema version "  # noqa: WPS326
        "(e.g. `?content_schema_version=1.0.0`). The `Accept` header versioning is deprecated.",  # noqa: WPS326
    },
)

DepthShiftDataViewV2(
    router=ds_record_router_v2,
    id_regex_str=DS_ID_REGEX_STR,
    single_content_type=DEPTH_SHIFT_STR,
    record_id_column="DepthShiftWPCID",
)
