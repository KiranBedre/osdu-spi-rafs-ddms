#  Copyright 2026 Microsoft Corporation
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

from starlette import status

from tests.integration.config import (
    CONFIG,
    DataFiles,
    SamplesAnalysisTypes,
    SchemaVersions,
)

DATA_PARTITION_ID = CONFIG["DATA_PARTITION"]


def test_nmr_negative_add_data_v1_non_scalar_value_returns_422_not_500(api, tests_data, record_id):
    """Reject bulk upload carrying non-scalar values in a failing row with 422, not 500.

    Regression for the scalar-unsafe NaN check: the bulk validator called
    ``pd.isna()`` directly on optional-field values while filtering validation
    errors. For non-scalar values (nested dict/list, e.g. the ``Meta`` and
    ``NMRTest`` objects) ``pd.isna`` returns an array, which raises
    ``ValueError`` in a boolean context and previously surfaced as an HTTP 500.
    The request must now fail validation with a 422 client error instead of
    crashing.
    """
    data_payload = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    # Invalidate the required SampleID reference while keeping the row's
    # non-scalar Meta/NMRTest objects -- exactly what the scalar-unsafe NaN
    # check used to crash on during error filtering.
    data_payload["data"][0][1] = None

    response = api.sample_analysis.post_data(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.NMR,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
