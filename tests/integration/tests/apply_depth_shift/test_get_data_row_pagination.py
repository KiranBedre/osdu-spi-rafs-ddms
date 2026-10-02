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

import pytest

from app.resources.common_headers import ACCEPT
from tests.integration.config import SamplesAnalysisTypes, SchemaVersions


@pytest.mark.parametrize("analysis_type", [SamplesAnalysisTypes.SATURATION_TEST])
def test_get_data_depth_shift_pagination_with_parquet_accept_returns_parquet(
    api,
    create_apply_depth_shift_case,
    depth_shift_record_id,
    depth_shift_dataset_id,
    helper,
    analysis_type,
):
    """Paginate the augmented rows and preserve the Parquet representation."""
    row_ids = [f"depth-shift-row-{number}" for number in range(3)]
    case = create_apply_depth_shift_case(
        data_column_values={"TestNumber": row_ids},
    )
    response = api.sample_analysis.get_data(
        record_id=case["sample_analysis_record_id"],
        dataset_id=case["sample_analysis_dataset_id"],
        analysis_type=analysis_type,
        schema_version=SchemaVersions.V1_0_0,
        params={
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
            "row_limit": 2,
            "row_offset": 1,
        },
        headers={ACCEPT: "application/x-parquet"},
        raw=True,
    )

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/x-parquet")
    body = helper.load_parquet_data(response.content, content_type="parquet")
    test_number_index = body["columns"].index("TestNumber")
    assert [row[test_number_index] for row in body["data"]] == row_ids[1:]
    assert response.headers["X-Total-Rows"] == "3"
    assert response.headers["X-Row-Offset"] == "1"
