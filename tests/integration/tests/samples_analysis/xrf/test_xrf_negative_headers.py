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

from starlette import status

from tests.integration.config import (
    SamplesAnalysisTypes,
    SchemaVersions,
)


def test_xrf_negative_getting_dataset_in_different_schema_version_than_stored(api, record_id, dataset_id_v1_1):
    """Check getting dataset in different schema version than stored."""

    response = api.sample_analysis.get_data(
        record_id=record_id,
        dataset_id=dataset_id_v1_1,
        analysis_type=SamplesAnalysisTypes.XRF,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_400_BAD_REQUEST],
        raw=True,
    )

    # Assert
    assert response.status_code == 400
    body = response.json()
    dataset_id = dataset_id_v1_1.rsplit(":", 1)[0]
    assert f"Schema version mismatch for dataset {dataset_id}: requested 1.0.0, stored ['1.1.0']" in body["reason"]
