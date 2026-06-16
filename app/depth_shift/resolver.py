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

"""DepthShiftResolver: orchestrates OSDU round-trips to prepare shift data."""

import io
from typing import Dict, List, Optional, Tuple

import pandas as pd
from fastapi import HTTPException
from httpx import HTTPStatusError
from starlette import status

from app.api.routes.utils.records import find_dataset_id
from app.depth_shift.calculator import validate_shift_values
from app.models.schemas.depth_shift_query import DepthShiftQueryParams
from app.resources.paths import DEPTH_SHIFT_STR
from app.services import dataset as dataset_module
from app.services import storage as storage_module

SAMPLE_BATCH_SIZE = 100


class DepthShiftResolver:
    """Fetch and resolve the data needed to perform depth-shift augmentation.

    All heavy I/O (Storage API, Dataset API) is isolated here so the
    augmenter and calculator remain pure.
    """

    def __init__(
        self,
        storage_service: storage_module.StorageService,
        dataset_service: dataset_module.DatasetService,
    ) -> None:
        self._storage = storage_service
        self._dataset = dataset_service

    async def resolve_depth_shift_wpc_id(
        self,
        shift_params: DepthShiftQueryParams,
    ) -> str:
        """Return the DepthShift WPC record ID for the ``id_provided`` policy.

        Returns *depth_shift_id* directly from *shift_params*.  This method is
        only called when ``depth_shift_policy == "id_provided"``; the
        ``"definitive"`` policy uses ``resolve_definitive_wpc_id`` instead.

        :param shift_params: validated depth-shift query params
        :type shift_params: DepthShiftQueryParams
        :return: DepthShift WPC record ID
        :rtype: str
        """
        return shift_params.depth_shift_id

    def resolve_definitive_wpc_id(self, sample_records: Dict[str, dict]) -> str:
        """Resolve the DepthShift WPC ID from already-fetched sample records.

        Iterates *sample_records* and reads
        ``record["data"]["DefinitiveDepthShift"]["DefinitiveDepthShiftID"]``
        from each record that carries the field.  All samples must agree on the
        same WPC ID.

        :param sample_records: mapping of sample record ID → full OSDU record dict
        :type sample_records: Dict[str, dict]
        :return: DepthShift WPC record ID
        :rtype: str
        :raises HTTPException: 422 when no sample has a DefinitiveDepthShift
        :raises HTTPException: 422 when samples reference different WPC IDs
        """
        found_ids = set()
        for record in sample_records.values():
            record_data = record.get("data", {})
            nested = record_data.get("DefinitiveDepthShift") or {}
            wpc_id = nested.get("DefinitiveDepthShiftID") or record_data.get("DefinitiveDepthShiftID")
            if wpc_id:
                found_ids.add(wpc_id)

        if not found_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No DefinitiveDepthShift found in any sample record.",
            )
        if len(found_ids) > 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Samples reference multiple different definitive depth shifts.",
            )
        return found_ids.pop()

    async def fetch_coretolog_depth_shift_data(  # noqa: WPS210
        self,
        depth_shift_wpc_id: str,
    ) -> Tuple[List[dict], List[dict], Optional[str]]:
        """Download and unpack the CoreToLog parquet for *depth_shift_wpc_id*.

        Returns a 3-tuple: (shift_set, shift_meta, shift_wellbore).
        - shift_set: list of DepthShiftSet interval dicts (from DepthShiftSet column)
        - shift_meta: list of Meta dicts (from Meta column); empty list when absent.
        - shift_wellbore: WellboreID from the WPC record (None when absent).

        The WPC record is fetched exactly once here; the WellboreID is returned
        alongside the parquet data so callers need not re-fetch the same record.

        :param depth_shift_wpc_id: DepthShift WPC record ID
        :type depth_shift_wpc_id: str
        :return: (shift_set, shift_meta, shift_wellbore)
        :rtype: Tuple[List[dict], List[dict], Optional[str]]
        :raises HTTPException: 404 if the WPC or its dataset is not found
        :raises HTTPException: 400 if the parquet is missing DepthShiftSet
        :raises HTTPException: 422 if the CoreToLog parquet contains more than one row
        """
        wpc_record = await self._storage.get_record(depth_shift_wpc_id)
        record_kind = wpc_record.get("kind", "")
        if "work-product-component--DepthShift" not in record_kind:
            kind_str = record_kind if record_kind else "(missing)"
            detail = "Record {0} is not a DepthShift WPC (kind: {1}).".format(depth_shift_wpc_id, kind_str)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        ddms_datasets = wpc_record.get("data", {}).get("DDMSDatasets", [])
        dataset_id = find_dataset_id(ddms_datasets, DEPTH_SHIFT_STR)
        if dataset_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No CoreToLog dataset found in DepthShift WPC {depth_shift_wpc_id}.",
            )
        parquet_bytes = await self._download_parquet(dataset_id, depth_shift_wpc_id)
        df = pd.read_parquet(io.BytesIO(parquet_bytes))
        if len(df) != 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "CoreToLog content for DepthShift WPC {0} must contain exactly 1 row, "
                    "but {1} rows were found. Each DepthShift WPC must reference a single "
                    "CoreToLog record.".format(depth_shift_wpc_id, len(df))
                ),
            )
        shift_set = self._extract_depth_shift_set(df, depth_shift_wpc_id)
        shift_meta = self._extract_meta(df)
        return (shift_set, shift_meta, wpc_record.get("data", {}).get("WellboreID"))

    async def fetch_sample_records(
        self,
        sample_ids: List[str],
    ) -> Dict[str, dict]:
        """Batch-fetch Sample records from Storage and return a keyed dict.

        Uses chunked batching with SAMPLE_BATCH_SIZE to respect the
        Storage API's maximum batch size.

        :param sample_ids: list of Sample OSDU record IDs
        :type sample_ids: List[str]
        :return: dict mapping record ID → full record dict
        :rtype: Dict[str, dict]
        """
        unique_ids = list(dict.fromkeys(sample_ids))
        records_by_id: Dict[str, dict] = {}

        for start in range(0, len(unique_ids), SAMPLE_BATCH_SIZE):
            batch = unique_ids[start : start + SAMPLE_BATCH_SIZE]
            response = await self._storage.query_records(batch)  # noqa: WPS476
            for record in response.get("records", []):
                record_id = record.get("id", "").rstrip(":")
                if record_id:
                    records_by_id[record_id] = record

        return records_by_id

    async def _download_parquet(self, dataset_id: str, wpc_id: str) -> bytes:
        """Download parquet bytes from the Dataset Service with error normalisation.

        :param dataset_id: OSDU dataset record ID
        :type dataset_id: str
        :param wpc_id: DepthShift WPC ID (used in error messages)
        :type wpc_id: str
        :return: raw parquet bytes
        :rtype: bytes
        :raises HTTPException: 400 when the Dataset Service rejects the request
        :raises HTTPException: 404 when the dataset has no content
        """
        try:
            parquet_bytes = await self._dataset.download_file(dataset_id)
        except HTTPStatusError as exc:
            if exc.response.status_code == status.HTTP_400_BAD_REQUEST:
                upstream = exc.response.text
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "The OSDU Dataset Service rejected the retrieval request for DepthShift "
                        "dataset '{0}' (WPC: {1}). "
                        "This usually means the dataset kind is not registered with a DMS handler "
                        "in the Dataset Service for this partition. "
                        "Verify that the DepthShift WPC record kind contains "
                        "'work-product-component--DepthShift' and that the Dataset Service in "
                        "the target partition has a handler registered for that kind. "
                        "Upstream error: {2}".format(dataset_id, wpc_id, upstream)
                    ),
                ) from exc
            raise
        if not parquet_bytes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"CoreToLog dataset {dataset_id} has no content.",
            )
        return parquet_bytes

    def _extract_depth_shift_set(
        self,
        df: pd.DataFrame,
        wpc_id: str,
    ) -> List[dict]:
        """Pull the DepthShiftSet nested list from the parquet DataFrame.

        :param df: parquet DataFrame (one row, with DepthShiftSet column)
        :type df: pd.DataFrame
        :param wpc_id: WPC id (used in error messages)
        :type wpc_id: str
        :return: list of interval dicts
        :rtype: List[dict]
        :raises HTTPException: 400 if DepthShiftSet column is missing
        """
        if "DepthShiftSet" not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"DepthShift WPC {wpc_id} parquet is missing 'DepthShiftSet' column.",
            )

        raw = df["DepthShiftSet"].iloc[0]
        shift_set = None
        if isinstance(raw, list):
            shift_set = raw
        elif hasattr(raw, "tolist"):
            as_list = raw.tolist()
            if isinstance(as_list, list):
                shift_set = as_list

        if not shift_set:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"DepthShift WPC {wpc_id} has an empty or invalid 'DepthShiftSet'.",
            )
        try:
            validate_shift_values(shift_set)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        return shift_set

    def _extract_meta(self, df: pd.DataFrame) -> List[dict]:
        """Extract Meta list from the CoreToLog parquet DataFrame.

        :param df: parquet DataFrame
        :type df: pd.DataFrame
        :return: list of Meta dicts, or empty list when column is absent
        :rtype: List[dict]
        """
        if "Meta" not in df.columns:
            return []
        raw = df["Meta"].iloc[0]
        try:
            meta_list = raw if isinstance(raw, list) else raw.tolist()
        except AttributeError:
            return []
        return meta_list if isinstance(meta_list, list) else []
