#  Copyright 2024 ExxonMobil Technology and Engineering Company
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

from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from app.dataframe.blob_parquet_loader import BlobParquetLoader
from app.dataframe.parquet_loader import DFPayload
from app.exceptions.exceptions import NotFoundException


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "blob_ids, blob_data, df_filter_processor, expected_result",
    [
        (  # Test with valid parquet files
            ["family1/type1/v1/uuid1"],
            pd.DataFrame().to_parquet(),
            None,
            DFPayload("family1/type1/v1/uuid1", pd.DataFrame(), None),
        ),
        (  # Test with a missing file
            ["family2/type2/v2/uuid2"],
            None,
            None,
            DFPayload(
                "family2/type2/v2/uuid2",
                pd.DataFrame(),
                "Unable to fetch: family2/type2/v2/uuid2. Not found, status code: 404",
            ),
        ),
        (  # Test with filter processor
            ["family3/type3/v3/uuid3"],
            pd.DataFrame().to_parquet(),
            MagicMock(),
            DFPayload("family3/type3/v3/uuid3", pd.DataFrame(), None),
        ),
    ],
)
async def test_read_parquet_files(blob_ids, blob_data, df_filter_processor, expected_result):
    blob_loader = BlobParquetLoader()

    # Mock IBlobStorage
    mock_blob_storage_service = AsyncMock()
    if blob_data:
        mock_blob_storage_service.get_blob.return_value = MagicMock(
            blob_data=blob_data,
        )
    else:
        mock_blob_storage_service.get_blob.side_effect = NotFoundException("Not Found")

    # Mock FilterProcessor
    if df_filter_processor:
        df_filter_processor.get_filters_without_aggregation.return_value = df_filter_processor
        df_filter_processor.apply_filters_from_bytes.return_value = pd.DataFrame()

    # Run the method
    result = await blob_loader.read_parquet_files(
        blob_ids=blob_ids,
        blob_storage_service=mock_blob_storage_service,
        df_filter_processor=df_filter_processor,
    )

    # Validate results
    assert len(result) == len(blob_ids)
    assert result[0].content_id == expected_result.content_id
    assert result[0].error_msg == expected_result.error_msg
    assert result[0].df.equals(expected_result.df)


@pytest.mark.asyncio
async def test_read_parquet_handles_pyarrow_exception():
    blob_loader = BlobParquetLoader()

    # Mock IBlobStorage
    mock_blob_storage_service = AsyncMock()
    mock_blob_storage_service.get_blob.return_value = MagicMock(blob_data=b"invalid data")

    # Run the method
    result = await blob_loader._read_parquet(
        blob_id="family4/type4/v4/uuid4",
        blob_storage_service=mock_blob_storage_service,
    )

    # Validate results
    assert result.content_id == "family4/type4/v4/uuid4"
    assert result.df.empty
    assert "PyArrowException" in result.error_msg
