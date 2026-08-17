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

from fastapi import APIRouter

from app.api.dependencies.validation import (
    validate_filters,
    validate_samplesanalysis_records_v2_payload,
)
from app.api.routes.common.dynamic_search import (
    get_search_data_description_template,
    get_search_description_template,
)
from app.api.routes.common.endpoints import (
    GenericSchemasView,
    GenericTypesView,
    build_extractor_for_param_name,
)
from app.api.routes.osdu.storage_records import BaseStorageRecordView
from app.api.routes.samplesanalysis.dynamic_search import SamplesAnalysisDynamicSearchView
from app.api.routes.samplesanalysis.endpoints import (
    SAMPLESANALYSIS_ID_REGEX_STR,
    SamplesAnalysisDataView,
)
from app.models.data_schemas.base import ALL_PATHS_TO_SA_DATA_MODEL, MAPS_TO_DATA_MODEL, SAMPLES_ANALYSIS
from app.search.ddms_dataset_ids_fetcher import (
    SearchServiceSamplesAnalysisTypeIdsFetcher,
)

sa_router = APIRouter()
RECORD_TYPE = "SamplesAnalysis"

GenericTypesView(
    router=sa_router,
    endpoint_path="/analysistypes",
    paths_to_data_model=ALL_PATHS_TO_SA_DATA_MODEL,
)

BaseStorageRecordView(
    router=sa_router,
    id_regex_str=SAMPLESANALYSIS_ID_REGEX_STR,
    validate_records_payload=validate_samplesanalysis_records_v2_payload,
    record_type=RECORD_TYPE,
)

GenericSchemasView(
    router=sa_router,
    endpoint_config={
        "path": "/{analysistype}/data/schema",
        "mapping": MAPS_TO_DATA_MODEL["v2"][SAMPLES_ANALYSIS],
        "param_extractor": build_extractor_for_param_name("analysistype"),
        "description": " ".join(
            [
                "Get the (`content schema`) for a given `{analysistype}`. <br><br>",
                "Use the `content_schema_version` query parameter to specify content schema version ",
                "(e.g. `?content_schema_version=1.0.0`). The `Accept` header versioning is deprecated.",
            ],
        ),
    },
)

SamplesAnalysisDataView(
    router=sa_router,
    id_regex_str=SAMPLESANALYSIS_ID_REGEX_STR,
)


SamplesAnalysisDynamicSearchView(
    router=sa_router,
    ddms_dataset_ids_fetcher_class=SearchServiceSamplesAnalysisTypeIdsFetcher,
    endpoints_config=[
        {
            "path": "/{analysis_type}/search",
            "handler": "get_search",
            "param_name": "analysis_type",
            "filter_dep": validate_filters,
            "description": get_search_description_template("{analysis_type}"),
        },
        {
            "path": "/{analysis_type}/search/data",
            "handler": "get_search_data",
            "param_name": "analysis_type",
            "filter_dep": validate_filters,
            "description": get_search_data_description_template("{analysis_type}"),
        },
    ],
)
