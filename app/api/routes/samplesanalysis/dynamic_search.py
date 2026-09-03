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

import io
import json
import re
from typing import Callable, List, Optional

import pandas as pd
from fastapi import Depends, HTTPException, Request, Response
from fastapi_cache.decorator import cache
from loguru import logger
from starlette import status

from app.core.http_status import HTTP_422_UNPROCESSABLE

from app.api.dependencies.request import get_content_schema_version, get_depth_shift_params
from app.api.dependencies.services import (
    get_async_dataset_service,
    get_async_search_service,
    get_async_storage_service,
    get_blob_storage_service,
)
from app.api.dependencies.validation import (
    get_orient,
    get_search_data_pagination_parameters,
    get_search_scope,
)
from app.api.routes.common.base_search import PaginationParametersType
from app.api.routes.common.dynamic_search import DynamicGenericSearchView
from app.api.routes.utils.records import get_id
from app.core.helpers.cache.coder import ResponseCoder
from app.core.helpers.cache.key_builder import key_builder_using_token
from app.core.helpers.cache.settings import CACHE_DEFAULT_TTL
from app.depth_shift.augmenter import augment_dataframe
from app.depth_shift.extractor import extract_sample_wellbore_id
from app.depth_shift.metadata import get_definitive_wpc_id, resolve_metadata_warning_state
from app.depth_shift.resolver import DepthShiftResolver
from app.models.schemas.depth_shift_query import DepthShiftMetadata, DepthShiftQueryParams, DepthShiftRowData
from app.models.schemas.search_scope import SearchScope
from app.providers.dependencies.blob_storage import IBlobStorage
from app.resources.filters import DataFrameFilterValidator
from app.services import dataset, search, storage


class SamplesAnalysisDynamicSearchView(DynamicGenericSearchView):
    """Specialized search view for SamplesAnalysis that supports depth-shift augmentation.

    Extends DynamicGenericSearchView to apply optional depth-shift transformation
    to scoped search results before returning to the client.
    """

    def _build_dynamic_endpoint(self, method_name: str, extractor: Callable, filter_dep, scope_dep=None):
        """Override to implement depth-shift support in get_search_data."""

        if scope_dep is None:
            scope_dep = get_search_scope
        uses_orient = method_name == "get_search_data"

        if uses_orient:
            return self._build_search_data_endpoint_with_depth_shift(extractor, filter_dep, scope_dep)
        return super()._build_dynamic_endpoint(method_name, extractor, filter_dep, scope_dep=scope_dep)

    def _build_search_data_endpoint_with_depth_shift(self, extractor: Callable, filter_dep, scope_dep):
        """Build cached search_data endpoint with optional depth-shift augmentation."""
        parent_method = getattr(self, "get_search_data")

        async def search_endpoint(  # noqa: WPS430,CFQ002,WPS211
            request: Request,
            df_filter: DataFrameFilterValidator = Depends(filter_dep),
            content_schema_version: str = Depends(get_content_schema_version),
            pagination_parameters: PaginationParametersType = Depends(get_search_data_pagination_parameters),
            search_scope: SearchScope = Depends(scope_dep),
            dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
            blob_storage_service: IBlobStorage = Depends(get_blob_storage_service),
            search_service: search.SearchService = Depends(get_async_search_service),
            storage_service: storage.StorageService = Depends(get_async_storage_service),
            orient: str = Depends(get_orient),
            depth_shift_params: Optional[DepthShiftQueryParams] = Depends(get_depth_shift_params),
        ):
            dynamic_param = self._inject_param(request, extractor)

            # Get search results (returns Response with JSON)
            result_response = await parent_method(
                request=request,
                analysis_type=dynamic_param,
                dataset_service=dataset_service,
                blob_storage_service=blob_storage_service,
                search_service=search_service,
                df_filter=df_filter,
                content_schema_version=content_schema_version,
                pagination_parameters=pagination_parameters,
                search_scope=search_scope,
                orient=orient,
            )

            # If no depth shift requested, return as-is
            if depth_shift_params is None:
                return result_response

            # Apply depth shift augmentation, passing search_scope for wellbore context
            return await self._apply_depth_shift_to_search_results(
                search_response=result_response,
                orient=orient,
                depth_shift_params=depth_shift_params,
                storage_service=storage_service,
                dataset_service=dataset_service,
                search_scope=search_scope,
                search_service=search_service,
            )

        return cache(
            expire=CACHE_DEFAULT_TTL,
            coder=ResponseCoder,
            key_builder=key_builder_using_token,
        )(search_endpoint)

    async def _apply_depth_shift_to_search_results(  # noqa: CCR001,CFQ001,WPS238,WPS210,WPS231
        self,
        search_response: Response,
        orient: str,
        depth_shift_params: DepthShiftQueryParams,
        storage_service: storage.StorageService,
        dataset_service: dataset.DatasetService,
        search_scope: SearchScope,
        search_service: Optional[search.SearchService] = None,
    ) -> Response:
        """Apply depth-shift augmentation to scoped search result dataframe.

        :param search_response: Response from get_search_data containing result JSON
        :param orient: pandas orient ('split' or 'records')
        :param depth_shift_params: depth shift parameters (policy, id)
        :param storage_service: storage service for fetching samples
        :param dataset_service: dataset service for depth shift data
        :param search_scope: search scope with wellbore context
        :return: Response with augmented depth-shift data
        :raises HTTPException: on validation or processing errors
        """
        try:
            # Parse search results
            body = search_response.body
            if isinstance(body, (bytes, bytearray)):
                body = body.decode("utf-8")

            search_result = json.loads(body)
            result_data = search_result.get("result", {})

            # Convert to DataFrame
            if isinstance(result_data, dict) and orient == "split":
                base_df = pd.read_json(io.StringIO(json.dumps(result_data)), orient="split")
            elif isinstance(result_data, list) and orient == "records":
                base_df = pd.DataFrame(result_data)
            else:
                base_df = pd.DataFrame()

            # Validate wellbore scope is provided
            if not search_scope.wellbore_id:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE,
                    detail="Depth shift requires a wellbore-scoped search. Please provide wellbore_id parameter.",
                )

            # Empty results are returned as-is; there is nothing to shift.
            if base_df.empty:
                return search_response

            # depth_shift_policy was explicitly requested, so SampleID is mandatory for non-empty data.
            if "SampleID" not in base_df.columns:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE,
                    detail=(
                        "Depth-shift augmentation requires a SampleID column in non-empty search results. "
                        + "Only analysis types with per-row SampleID support depth-shift retrieval."
                    ),
                )

            # Extract sample IDs and fetch records
            resolver = DepthShiftResolver(
                storage_service=storage_service,
                dataset_service=dataset_service,
            )

            sample_ids = base_df["SampleID"].dropna().astype(str).unique().tolist()
            sample_records = await resolver.fetch_sample_records(sample_ids)

            self._validate_single_wellbore_scope(sample_records, search_scope.wellbore_id)
            n_samples = len(sample_ids)
            logger.info("Depth shift: using wellbore scope {0} for {1} samples", search_scope.wellbore_id, n_samples)

            # Resolve depth shift ID
            if depth_shift_params.is_definitive:
                wpc_id = resolver.resolve_definitive_wpc_id(sample_records)
                shift_source = "definitive"
            else:
                wpc_id = await resolver.resolve_depth_shift_wpc_id(depth_shift_params)
                shift_source = "user-provided"

            # Fetch depth shift data and augment
            shift_set, shift_meta, shift_wellbore = await resolver.fetch_coretolog_depth_shift_data(wpc_id)

            augmented_df, warnings = augment_dataframe(
                base_df=base_df,
                resolver=resolver,
                shift_set=shift_set,
                shift_wellbore=shift_wellbore,
                sample_records=sample_records,
                shift_meta=shift_meta,
            )

            logger.info("Depth-shift augmentation applied to {0} samples; WPC {1}", len(sample_ids), wpc_id)

            # Build response with depth shift metadata
            ds_cols = [
                "SampleTop",
                "SampleBase",
                "SampleMean",
                "ShiftedSampleTop",
                "ShiftedSampleBase",
                "ShiftedSampleMean",
                "DepthShiftWarnings",
            ]
            depth_shift_data = [
                DepthShiftRowData(
                    SampleTop=row["SampleTop"],
                    SampleBase=row["SampleBase"],
                    SampleMean=row["SampleMean"],
                    ShiftedSampleTop=row["ShiftedSampleTop"],
                    ShiftedSampleBase=row["ShiftedSampleBase"],
                    ShiftedSampleMean=row["ShiftedSampleMean"],
                    DepthShiftWarnings=row["DepthShiftWarnings"] if isinstance(row["DepthShiftWarnings"], list) else [],
                ).model_dump()
                for _, row in augmented_df[ds_cols].iterrows()
            ]
            clean_df = augmented_df.drop(columns=ds_cols)

            # Convert to requested orient
            if orient == "records":
                augmented_result = clean_df.to_dict(orient="records")
            else:
                augmented_result = clean_df.to_dict(orient=orient)

            # Build metadata
            definitive_available, metadata_warnings = resolve_metadata_warning_state(
                sample_records=sample_records,
                applied_wpc_id=wpc_id,
                used_definitive=depth_shift_params.is_definitive,
            )

            # Return augmented response
            augmented_search_result = {
                "result": augmented_result,
                "offset": search_result.get("offset", 0),
                "page_limit": search_result.get("page_limit", 100),
                "total_size": search_result.get("total_size", len(augmented_df)),
                "DepthShiftData": depth_shift_data,
                "DepthShiftMetadata": DepthShiftMetadata(
                    appliedDepthShiftId=wpc_id,
                    source=shift_source,
                    definitiveDepthShiftAvailable=definitive_available,
                    usedDefinitive=depth_shift_params.is_definitive,
                    warnings=metadata_warnings,
                ).model_dump(),
            }

            return Response(
                content=json.dumps(augmented_search_result),
                media_type="application/json",
            )

        except HTTPException:  # noqa: WPS329
            raise
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Depth-shift error: {exc}",
            )
        except Exception as exc:  # noqa: B902
            logger.exception("Error applying depth shift to search results")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error applying depth shift: {0}".format(exc),
            )

    @staticmethod
    def _escape_query_value(raw_value: str) -> str:
        return raw_value.replace('"', r"\"")

    @staticmethod
    def _expand_id_variants(record_id: str) -> List[str]:  # noqa: CFQ004
        if not record_id:
            return []
        variants: List[str] = [record_id]
        if record_id.endswith(":"):
            variants.append(record_id[:-1])
            return list(dict.fromkeys(variants))
        version_match = re.match(r"^(.*):(\d+)$", record_id)
        if version_match:
            base_id = version_match.group(1)
            variants.extend([base_id, f"{base_id}:"])
            return list(dict.fromkeys(variants))
        variants.append(f"{record_id}:")
        return list(dict.fromkeys(variants))

    @staticmethod
    def _get_definitive_wpc_id(record: dict) -> Optional[str]:
        """Read DefinitiveDepthShiftID from a Sample record."""
        return get_definitive_wpc_id(record)

    @staticmethod
    def _extract_sample_wellbore_id(sample_record: dict) -> Optional[str]:
        """Resolve the sample wellbore from nested acquisition data when present."""
        return extract_sample_wellbore_id(sample_record)

    def _collect_wellbore_scope(self, sample_records: dict) -> tuple[set[str], list[str]]:
        """Collect normalized wellbore ids and sample ids missing wellbore."""
        wellbore_ids: set[str] = set()
        missing_wellbore_samples: list[str] = []
        for sample_id, record in sample_records.items():
            wid = self._extract_sample_wellbore_id(record)
            if wid:
                wellbore_ids.add(get_id(wid))
            else:
                missing_wellbore_samples.append(sample_id)
        return wellbore_ids, missing_wellbore_samples

    @staticmethod
    def _raise_missing_wellbore_samples(missing_wellbore_samples: list[str]) -> None:
        """Raise a 422 when any sample record does not resolve a WellboreID."""
        if not missing_wellbore_samples:
            return
        missing_ids = sorted(str(sample_key) for sample_key in missing_wellbore_samples)
        msg = (
            "Depth shift requires every sample record to resolve to a WellboreID. "
            + "Missing WellboreID for sample ids: {0}."
        ).format(missing_ids)
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail=msg,
        )

    @staticmethod
    def _validate_resolved_wellbore_ids(wellbore_ids: set[str]) -> None:
        """Validate that exactly one wellbore is resolved from sample records."""
        if not wellbore_ids:
            msg = (
                "Depth shift requires sample records to resolve to a WellboreID."
                + " Provide a wellbore-scoped search result set."
            )
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail=msg,
            )

        if len(wellbore_ids) > 1:
            sorted_ids = sorted(wellbore_ids)
            msg = "Depth shift requires wellbore-scoped results. Resolved multiple WellboreIDs: {0}.".format(sorted_ids)
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail=msg,
            )

    @staticmethod
    def _validate_requested_wellbore_match(wellbore_ids: set[str], requested_wellbore_id: Optional[str]) -> None:
        """Validate resolved sample wellbore matches requested wellbore scope."""
        if not requested_wellbore_id:
            return

        requested_normalized = get_id(requested_wellbore_id)
        resolved_wellbore = next(iter(wellbore_ids))
        if resolved_wellbore != requested_normalized:
            msg = (
                "Depth shift requires sample records to match requested wellbore_id. "
                + "Requested: {0}; resolved from samples: {1}."
            ).format(requested_normalized, resolved_wellbore)
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail=msg,
            )

    def _validate_single_wellbore_scope(
        self,
        sample_records: dict,
        requested_wellbore_id: Optional[str] = None,
    ) -> None:
        """Reject depth-shift requests that span multiple wellbores."""
        wellbore_ids, missing_wellbore_samples = self._collect_wellbore_scope(sample_records)
        self._raise_missing_wellbore_samples(missing_wellbore_samples)
        self._validate_resolved_wellbore_ids(wellbore_ids)
        self._validate_requested_wellbore_match(wellbore_ids, requested_wellbore_id)
