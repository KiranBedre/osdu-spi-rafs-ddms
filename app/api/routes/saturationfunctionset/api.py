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
    get_geo_context_scope,
    validate_filters_for_domain_inferred_model,
    validate_saturation_function_set_v2_payload,
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
from app.api.routes.saturationfunctionset.endpoints import (
    SaturationFunctionSetRecordView,
)
from app.api.routes.v2.data.endpoints import DynamicContentTypeDataViewV2
from app.models.data_schemas.base import MAPS_TO_DATA_MODEL
from app.resources.paths import SATURATION_FUNCTION_SET_STR
from app.search.saturation_function_set_ids_fetcher import (
    SearchServiceSaturationFunctionSetIdsFetcher,
)

SFS_ID_REGEX_STR = r"^[\w\-\.]+:work-product-component--SaturationFunctionSet:[\w\-\.\:\%]+$"

sfs_record_router_v2 = APIRouter(redirect_slashes=False)

# declare before SaturationFunctionSetRecordView for single content type to avoid path collision
DynamicGenericSearchView(
    router=sfs_record_router_v2,
    ddms_dataset_ids_fetcher_class=SearchServiceSaturationFunctionSetIdsFetcher,
    endpoints_config=[
        {
            "path": "/search",
            "handler": "get_search",
            "param_name": None,
            "filter_dep": validate_filters_for_domain_inferred_model,
            "scope_dep": get_geo_context_scope,
            "description": get_search_description_template("SaturationFunctionSet"),
        },
        {
            "path": "/search/",  # declare the path with '/' to avoid collision with get wpc
            "handler": "get_search",
            "param_name": None,
            "filter_dep": validate_filters_for_domain_inferred_model,
            "scope_dep": get_geo_context_scope,
            "description": get_search_description_template("SaturationFunctionSet"),
            "include_in_schema": False,
        },
        {
            "path": "/search/data",
            "handler": "get_search_data",
            "param_name": None,
            "filter_dep": validate_filters_for_domain_inferred_model,
            "scope_dep": get_geo_context_scope,
            "description": get_search_data_description_template("SaturationFunctionSet"),
        },
    ],
)

SaturationFunctionSetRecordView(
    router=sfs_record_router_v2,
    id_regex_str=SFS_ID_REGEX_STR,
    validate_records_payload=validate_saturation_function_set_v2_payload,
    record_type="SaturationFunctionSet",
)

GenericSchemasView(
    router=sfs_record_router_v2,
    endpoint_config={
        "path": "/data/schema",
        "mapping": MAPS_TO_DATA_MODEL["v2"][SATURATION_FUNCTION_SET_STR],
        "param_extractor": infer_content_type_from_url,
        "description": "Get the (`content schema`) for `{SaturationFunctionSet}`. <br><br>"
        "Use the `content_schema_version` query parameter to specify content schema version "  # noqa: WPS326
        "(e.g. `?content_schema_version=1.0.0`). The `Accept` header versioning is deprecated.",  # noqa: WPS326
    },
)

DynamicContentTypeDataViewV2(
    router=sfs_record_router_v2,
    id_regex_str=SFS_ID_REGEX_STR,
    single_content_type=SATURATION_FUNCTION_SET_STR,
    record_id_column="SaturationFunctionSetID",
)
