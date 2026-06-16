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

import io
import json
from typing import Annotated, List, Optional

import pandas as pd
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi_cache.decorator import cache
from loguru import logger
from starlette import status

from app.api.dependencies.request import (
    get_content_schema_version,
    get_depth_shift_params,
    validate_json_content_type,
)
from app.api.dependencies.services import (
    get_async_dataset_service,
    get_async_storage_service,
    get_blob_storage_service,
)
from app.api.dependencies.validation import get_orient, validate_filters
from app.api.routes.osdu.storage_records import BaseStorageRecordView
from app.api.routes.utils.api_description_helper import APIDescriptionHelper
from app.api.routes.v2.data.endpoints import BaseDataViewV2
from app.core.helpers.cache.coder import ResponseCoder
from app.core.helpers.cache.key_builder import key_builder_using_token
from app.core.helpers.cache.settings import CACHE_DEFAULT_TTL
from app.depth_shift.augmenter import augment_dataframe
from app.depth_shift.resolver import DepthShiftResolver
from app.models.schemas.depth_shift_query import DepthShiftMetadata, DepthShiftQueryParams, DepthShiftRowData
from app.models.schemas.osdu_storage import (
    OsduStorageRecord,
    StorageUpsertResponse,
)
from app.providers.dependencies.blob_storage import IBlobStorage
from app.resources.filters import DataFrameFilterValidator
from app.resources.load_model_example import load_data_example
from app.services import dataset, storage

SAMPLESANALYSIS_ID_REGEX_STR = r"^[\w\-\.]+:work-product-component--SamplesAnalysis:[\w\-\.\:\%]+$"


def _get_definitive_wpc_id(record: dict) -> Optional[str]:
    """Read DefinitiveDepthShiftID from a Sample record, checking both storage paths.

    Sample 3.1.0 stores it nested: data.DefinitiveDepthShift.DefinitiveDepthShiftID.
    Older or flat-stored records may use: data.DefinitiveDepthShiftID.
    """
    record_data = record.get("data", {})
    nested = record_data.get("DefinitiveDepthShift", {})
    return (nested.get("DefinitiveDepthShiftID") if nested else None) or record_data.get("DefinitiveDepthShiftID")


class SamplesAnalysisRecordView(BaseStorageRecordView):
    def __init__(
        self,
        router: APIRouter,
        validate_records_payload: callable,
        record_type: str,
    ) -> None:
        super().__init__(
            router=router,
            id_regex_str=SAMPLESANALYSIS_ID_REGEX_STR,
            validate_records_payload=validate_records_payload,
            record_type=record_type,
        )

    async def post_records(
        self,
        request: Request,
        request_records: Annotated[
            List[dict],
            Body(
                openapi_examples={
                    "example": {
                        "value": load_data_example("samples_analysis.json"),
                    },
                },
            ),
        ],
        storage_service: storage.StorageService = Depends(get_async_storage_service),
    ) -> StorageUpsertResponse:
        return await super().post_records(request, request_records, storage_service)

    def _prepare_post_records_route(self) -> None:
        """Add api route for post_records without dependencies."""

        async def validate_request_records(
            request_records: List[OsduStorageRecord],
            storage_service: storage.StorageService = Depends(get_async_storage_service),
        ) -> List[dict]:
            """Validate request records.

            :param request_records: request records
            :type request_records: List[OsduStorageRecord]
            :param storage_service: storage service instance, defaults
                  to Depends(get_async_storage_service)
            :type storage_service: storage.StorageService, optional
            :return: validated records
            :rtype: List[dict]
            """
            return await self._validate_records_payload(request_records, storage_service)

        self._router.add_api_route(
            path="",
            endpoint=self.post_records,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            response_model=StorageUpsertResponse,
            response_model_by_alias=False,
            description=APIDescriptionHelper.append_manage_roles(
                f"Create or update `{self._record_type}` record(s).",
            ),
            dependencies=[
                Depends(validate_request_records),
                Depends(validate_json_content_type),
            ],
        )


class SamplesAnalysisDataView(BaseDataViewV2):
    """BaseDataViewV2 subclass that adds optional depth-shift augmentation.

    When the caller supplies ?depth_shift_id=<WPC_ID> the GET data response
    is augmented with four extra columns: SampleTop, SampleBase,
    ShiftedSampleTop, ShiftedSampleBase, and a DepthShiftWarnings field.
    When neither depth-shift parameter is supplied the response is identical
    to the parent implementation.
    """

    @cache(expire=CACHE_DEFAULT_TTL, coder=ResponseCoder, key_builder=key_builder_using_token)
    async def get_data_v2(  # noqa: CFQ002, WPS211
        self,
        request: Request,
        record_id: str,
        analysis_type: str,
        content_id: str,
        dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
        storage_service: storage.StorageService = Depends(get_async_storage_service),
        blob_storage_service: IBlobStorage = Depends(get_blob_storage_service),
        df_filter: DataFrameFilterValidator = Depends(validate_filters),
        content_schema_version: str = Depends(get_content_schema_version),
        orient: str = Depends(get_orient),
        depth_shift_params: Optional[DepthShiftQueryParams] = Depends(get_depth_shift_params),
    ) -> Response:
        """Get record data, optionally augmented with depth-shift columns.

        :param request: request
        :type request: Request
        :param record_id: record id
        :type record_id: str
        :param analysis_type: the samples analysis type
        :type analysis_type: str
        :param content_id: content identifier (dataset id or blob uuid)
        :type content_id: str
        :param dataset_service: dataset service
        :type dataset_service: dataset.DatasetService
        :param storage_service: storage service
        :type storage_service: storage.StorageService
        :param blob_storage_service: blob storage service
        :type blob_storage_service: IBlobStorage
        :param df_filter: df filter validator
        :type df_filter: DataFrameFilterValidator
        :param content_schema_version: the version used for content schema
            validation
        :type content_schema_version: str
        :param orient: JSON output format ('split' or 'records')
        :type orient: str
        :param depth_shift_params: optional depth-shift query parameters
        :type depth_shift_params: Optional[DepthShiftQueryParams]
        :return: dataset data (augmented when depth_shift_params is not None)
        :rtype: Response
        """
        if depth_shift_params is None:
            return await self._get_data(
                request,
                record_id,
                content_id,
                dataset_service,
                storage_service,
                df_filter,
                content_schema_version,
                orient,
            )

        return await self._get_data_with_depth_shift(
            request=request,
            record_id=record_id,
            analysis_type=analysis_type,
            content_id=content_id,
            dataset_service=dataset_service,
            storage_service=storage_service,
            blob_storage_service=blob_storage_service,
            df_filter=df_filter,
            content_schema_version=content_schema_version,
            orient=orient,
            depth_shift_params=depth_shift_params,
        )

    async def _get_data_with_depth_shift(
        self,
        request: Request,
        record_id: str,
        analysis_type: str,
        content_id: str,
        dataset_service: dataset.DatasetService,
        storage_service: storage.StorageService,
        blob_storage_service: IBlobStorage,
        df_filter: DataFrameFilterValidator,
        content_schema_version: str,
        orient: str,
        depth_shift_params: DepthShiftQueryParams,
    ) -> Response:
        """Execute the depth-shift pipeline and return an augmented response.

        :param request: incoming request
        :type request: Request
        :param record_id: SA WPC record ID
        :type record_id: str
        :param analysis_type: analysis type path segment
        :type analysis_type: str
        :param content_id: dataset or blob content ID
        :type content_id: str
        :param dataset_service: dataset service
        :type dataset_service: dataset.DatasetService
        :param storage_service: storage service
        :type storage_service: storage.StorageService
        :param blob_storage_service: blob storage service
        :type blob_storage_service: IBlobStorage
        :param df_filter: dataframe filter validator
        :type df_filter: DataFrameFilterValidator
        :param content_schema_version: content schema version string
        :type content_schema_version: str
        :param orient: JSON orient ('split' or 'records')
        :type orient: str
        :param depth_shift_params: non-None depth-shift parameters
        :type depth_shift_params: DepthShiftQueryParams
        :return: augmented JSON response
        :rtype: Response
        :raises HTTPException: 404 when the abstract path record has no DefinitiveDepthShiftID
        :raises HTTPException: 400 on domain errors (missing SampleID, etc.)
        """
        try:
            return await self._run_depth_shift_pipeline(
                request=request,
                record_id=record_id,
                analysis_type=analysis_type,
                content_id=content_id,
                dataset_service=dataset_service,
                storage_service=storage_service,
                blob_storage_service=blob_storage_service,
                df_filter=df_filter,
                content_schema_version=content_schema_version,
                orient=orient,
                depth_shift_params=depth_shift_params,
            )
        except NotImplementedError as exc:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=str(exc),
            )
        except (ValueError, KeyError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Depth-shift error: {exc}",
            )

    async def _run_depth_shift_pipeline(
        self,
        request: Request,
        record_id: str,
        analysis_type: str,
        content_id: str,
        dataset_service: dataset.DatasetService,
        storage_service: storage.StorageService,
        blob_storage_service: IBlobStorage,
        df_filter: DataFrameFilterValidator,
        content_schema_version: str,
        orient: str,
        depth_shift_params: DepthShiftQueryParams,
    ) -> Response:
        """Core depth-shift pipeline: resolve → fetch → augment → respond.

        Two execution paths depending on *depth_shift_params.depth_shift_policy*:

        - ``id_provided``: resolve WPC ID first, then fetch base data and samples.
        - ``definitive``: fetch base data and samples first so the WPC ID can be
          resolved from the sample records before downloading the CoreToLog parquet.

        :return: augmented JSON response
        :rtype: Response
        """
        resolver = DepthShiftResolver(
            storage_service=storage_service,
            dataset_service=dataset_service,
        )

        if not depth_shift_params.is_definitive:
            # id_provided path: WPC ID is explicit, resolve it first.
            wpc_id = await resolver.resolve_depth_shift_wpc_id(depth_shift_params)
            shift_set, shift_meta, shift_wellbore = await resolver.fetch_coretolog_depth_shift_data(wpc_id)

            base_response = await self._get_data(
                request,
                record_id,
                content_id,
                dataset_service,
                storage_service,
                df_filter,
                content_schema_version,
                "split",
            )

            if base_response.status_code != status.HTTP_200_OK:
                return base_response

            base_df = self._response_to_dataframe(base_response, "split")
            if "SampleID" not in base_df.columns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Depth-shift augmentation requires a 'SampleID' column in the "
                        "bulk data, but it was not found. Only analysis types that carry "
                        "per-row SampleID are supported for depth-shift retrieval."
                    ),
                )
            sample_ids = [sid.rstrip(":") for sid in base_df["SampleID"].dropna().astype(str).unique().tolist()]
            sample_records = await resolver.fetch_sample_records(sample_ids)

        else:
            # definitive path: need sample records first to resolve the WPC ID.
            base_response = await self._get_data(
                request,
                record_id,
                content_id,
                dataset_service,
                storage_service,
                df_filter,
                content_schema_version,
                "split",
            )

            if base_response.status_code != status.HTTP_200_OK:
                return base_response

            base_df = self._response_to_dataframe(base_response, "split")
            if "SampleID" not in base_df.columns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Depth-shift augmentation requires a 'SampleID' column in the "
                        "bulk data, but it was not found. Only analysis types that carry "
                        "per-row SampleID are supported for depth-shift retrieval."
                    ),
                )
            sample_ids = [sid.rstrip(":") for sid in base_df["SampleID"].dropna().astype(str).unique().tolist()]
            sample_records = await resolver.fetch_sample_records(sample_ids)

            # May raise 422 if no DefinitiveDepthShift or samples disagree.
            wpc_id = resolver.resolve_definitive_wpc_id(sample_records)
            shift_set, shift_meta, shift_wellbore = await resolver.fetch_coretolog_depth_shift_data(wpc_id)

        # --- Build DepthShiftMetadata ---
        definitive_available = any(_get_definitive_wpc_id(record) for record in sample_records.values())
        used_definitive = depth_shift_params.is_definitive
        source = "definitive" if used_definitive else "user-provided"

        # Collect extra warnings before augmentation (id_provided + definitive conflict).
        extra_warnings: List[str] = []
        if not used_definitive and definitive_available:
            definitive_id = next(
                (
                    _get_definitive_wpc_id(record)
                    for record in sample_records.values()
                    if _get_definitive_wpc_id(record)
                ),
                None,
            )
            if definitive_id and definitive_id != wpc_id:
                extra_warnings.append(
                    f"Sample references a definitive depth shift ({definitive_id}) that differs from "
                    f"the requested depth_shift_id ({wpc_id}). RAFS applied the requested depth_shift_id "
                    f"because depth_shift_policy=id_provided."
                )

        augmented_df, warnings = augment_dataframe(
            base_df=base_df,
            resolver=resolver,
            shift_set=shift_set,
            shift_wellbore=shift_wellbore,
            sample_records=sample_records,
            shift_meta=shift_meta,
        )

        logger.info(
            f"Depth-shift augmentation applied for WPC {wpc_id}; " f"{len(sample_ids)} unique samples.",
        )

        _ds_cols = ["SampleTop", "SampleBase", "ShiftedSampleTop", "ShiftedSampleBase", "DepthShiftWarnings"]
        depth_shift_data = [
            DepthShiftRowData(
                SampleTop=row["SampleTop"],
                SampleBase=row["SampleBase"],
                ShiftedSampleTop=row["ShiftedSampleTop"],
                ShiftedSampleBase=row["ShiftedSampleBase"],
                DepthShiftWarnings=row["DepthShiftWarnings"] if isinstance(row["DepthShiftWarnings"], list) else [],
            ).dict()
            for _, row in augmented_df[_ds_cols].iterrows()
        ]
        clean_df = augmented_df.drop(columns=_ds_cols)

        if orient == "records":
            result = {"data": json.loads(clean_df.to_json(orient="records"))}
        else:
            result = json.loads(clean_df.to_json(orient=orient))

        result["DepthShiftData"] = depth_shift_data
        result["DepthShiftMetadata"] = DepthShiftMetadata(
            appliedDepthShiftId=wpc_id,
            source=source,
            definitiveDepthShiftAvailable=definitive_available,
            usedDefinitive=used_definitive,
            warnings=extra_warnings,
        ).dict()
        return Response(
            content=json.dumps(result),
            media_type="application/json",
        )

    def _response_to_dataframe(self, response: Response, response_orient: str = "split") -> pd.DataFrame:
        """Deserialise a JSON Response body into a DataFrame.

        :param response: JSON response from the base get_data_v2
        :type response: Response
        :param response_orient: the pandas orient used to produce the response
            body ('split' or 'records'); defaults to 'split'
        :type response_orient: str
        :return: DataFrame
        :rtype: pd.DataFrame
        """
        body = response.body
        if isinstance(body, (bytes, bytearray)):
            body = body.decode("utf-8")
        return pd.read_json(io.StringIO(body), orient=response_orient)
