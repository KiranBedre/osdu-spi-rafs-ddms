#  Copyright 2026 ExxonMobil Technology and Engineering Company
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

import pytest

from app.resources.common_headers import CACHE_CONTROL
from tests.integration.config import (
    CONFIG,
    SCHEMA_AUTHORITY,
    DataFiles,
    SamplesAnalysisEndpoints,
)

DATA_PARTITION_ID = CONFIG["DATA_PARTITION"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_nmr_max_age_cache_header(api, endpoint, args, record_id, dataset_id_v1, analysis_type):
    """Verify that endpoint returns expected status codes for max-age Cache Control header"""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_kwargs = {name: local_vars[name] for name in args}

    call_kwargs.update(
        {
            "headers": {CACHE_CONTROL: "max-age=120"},
            "raw": True,
        }
    )

    response = method(**call_kwargs)

    # Assert
    assert response.status_code == 200


def test_nmr_create_record_with_kind_matching_semantic_version(api, helper, tests_data, delete_record):
    """Verify record creation with kind matching only semantic version can be retrieved unchanged via GET."""
    # Record creation
    data_payload = copy.deepcopy(tests_data(DataFiles.SAMPLE_ANALYSIS))
    data_payload["kind"] = f"{SCHEMA_AUTHORITY}:wks:work-product-component--SamplesAnalysis:5.23.72"
    response = api.sample_analysis.post_record(body=[data_payload])
    record_id = response["recordIdVersions"][0].rsplit(":", 1)[0]

    # Register record for cleanup
    delete_record(record_id)

    # Retrieve the record by id and prepare baseline
    data_payload["id"] = record_id
    gotten_record = api.sample_analysis.get_record(record_id)

    # Response should contain the same business fields as the original POST body
    helper.compare_responses(gotten_record, data_payload, response_type="json")
