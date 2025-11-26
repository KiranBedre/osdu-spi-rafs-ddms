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

import re
from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import pandera as pa
from loguru import logger

from app.api.routes.utils.query import divide_chunks, find_osdu_ids_from_string
from app.core.config import get_app_settings
from app.services.storage import StorageService

settings = get_app_settings()


@dataclass
class DataValidator(object):
    data_schema: pa.DataFrameSchema
    storage_service: StorageService
    api_version: str

    async def validate(self, df: pd.DataFrame, bulk_mode: bool = False) -> dict:
        """Validate dataframe.

        :param df: dataframe
        :type df: pd.DataFrame
        :param bulk_mode: if True, use relaxed validation that allows NaN in optional object fields
        :type bulk_mode: bool
        :return: errors or empty dict
        :rtype: dict
        """
        schema_errors = self._validate_schema(df, bulk_mode=bulk_mode)
        if schema_errors:
            return schema_errors

        data_integrity_errors = await self._validate_integrity(df)
        if data_integrity_errors:
            return {
                "missing_records": list(data_integrity_errors),
            }

        return {}

    def _validate_schema(self, df: pd.DataFrame, bulk_mode: bool = False) -> dict:
        """Validate dataframe using validator schema.

        :param df: dataframe
        :type df: pd.DataFrame
        :param bulk_mode: if True, use relaxed validation for NaN in optional fields
        :type bulk_mode: bool
        :return: errors or empty dict
        :rtype: dict
        """
        errors = {}

        try:
            self.data_schema.validate(df, lazy=True)
        except pa.errors.SchemaErrors as err:
            error_cases = list(err.failure_cases.iloc(0))

            if bulk_mode:
                # In bulk mode, filter out errors related to NaN in optional object fields
                error_cases = self._filter_nan_errors(error_cases, df)

            if error_cases:
                errors = self._collect_errors(error_cases)

        return errors

    async def _find_missing_records(self, ids_to_check: list) -> set:
        """From a list of ids find if there is any record missing in storage.

        :param ids_to_check: list of ids to check
        :type ids_to_check: list
        :return: returns the set of missing (invalid) record ids
        :rtype: set
        """
        logger.debug(f"The list of ids to check exist on storage: {ids_to_check}")
        storage_response = await self.storage_service.query_records(ids_to_check)
        return set(storage_response["invalidRecords"])

    async def _validate_integrity(self, df: pd.DataFrame) -> set:
        """Validate data referential integrity.

        :param df: dataframe
        :type df: pd.DataFrame
        :return: missing records
        :rtype: list
        """
        df_string = df.to_string()
        ids_to_check = find_osdu_ids_from_string(df_string)

        missing_records = set()
        for ids_to_check_batch in divide_chunks(list(ids_to_check), settings.storage_query_limit):
            missing_records.update(await self._find_missing_records(ids_to_check=ids_to_check_batch))

        return missing_records

    def _get_excluded_records(self, records: Iterable, skip_types: Iterable) -> set:
        """Get excluded record ids from a list given skip types."""
        excluded_records = set()
        for record in records:
            for skip_type in skip_types:
                if skip_type in record:
                    excluded_records.add(record)
        return excluded_records

    def _filter_nan_errors(self, error_cases: Iterable, df: pd.DataFrame) -> list:
        """Filter out NaN-related errors for optional object fields in bulk mode.

        In bulk ingestion, DataFrame column alignment forces NaN values for absent
        optional fields. This method filters those validation errors to provide a
        pragmatic workaround for the DataFrame limitation.

        Only filters NaN errors for fields that are actually optional (not required)
        in the Pydantic model, ensuring required fields are still validated.

        :param error_cases: list of error cases from pandera
        :type error_cases: Iterable
        :param df: the dataframe being validated
        :type df: pd.DataFrame
        :return: filtered list of error cases
        :rtype: list
        """
        # Get required fields from the Pydantic model
        required_fields = self._get_required_fields()

        filtered_errors = []

        for error_case in error_cases:
            failure_case = error_case.get("failure_case", "")

            # Check if this error contains NaN in an optional field
            if self._is_nan_in_optional_field(failure_case, required_fields):
                logger.debug(f"Filtering NaN error for optional field in bulk mode: {failure_case}")
                continue

            # Keep all other errors (including NaN in required fields)
            filtered_errors.append(error_case)

        return filtered_errors

    def _is_nan_in_optional_field(self, failure_case, required_fields: set) -> bool:
        """Check if failure case is a NaN error in an optional field.

        :param failure_case: the failure case from pandera error
        :param required_fields: set of required field names
        :return: True if this is a NaN error in an optional field
        :rtype: bool
        """
        # Handle string representation of dict (e.g., "{'FieldName': nan}")
        if isinstance(failure_case, str) and "nan" in failure_case.lower():
            field_matches = re.findall(r"['\"](\w+)['\"]:\s*nan", failure_case)
            return any(field not in required_fields for field in field_matches)

        # Handle dict failure case
        if isinstance(failure_case, dict):
            return any(
                pd.isna(field_value) and field_name not in required_fields
                for field_name, field_value in failure_case.items()
            )

        return False

    def _get_required_fields(self) -> set:
        """Extract required field names from the Pydantic model.

        Required fields are those defined with Field(...) in Pydantic models,
        which translates to fields without a default value.

        :return: set of required field names
        :rtype: set
        """
        required_fields = set()

        try:
            required_fields = self._extract_required_from_schema()
            logger.debug(f"Identified required fields: {required_fields}")
        except (AttributeError, TypeError) as exc:
            logger.warning(f"Could not extract required fields from schema: {exc}")
            # If we can't determine required fields, don't filter any errors
            # This is the safe fallback

        return required_fields

    def _extract_required_from_schema(self) -> set:
        """Helper to extract required fields from pandera schema.

        :return: set of required field names
        :rtype: set
        """
        required_fields = set()

        pydantic_model = self._get_pydantic_model()
        if not pydantic_model:
            return required_fields

        # Get required fields from Pydantic model
        model_fields = getattr(pydantic_model, "__fields__", None)
        if model_fields:
            for field_name, field_info in model_fields.items():
                if field_info.required:
                    required_fields.add(field_name)

        return required_fields

    def _get_pydantic_model(self):
        """Get Pydantic model from pandera schema.

        :return: Pydantic model or None
        """
        dtype = getattr(self.data_schema, "dtype", None)
        if not dtype:
            return None

        return getattr(dtype, "type", None)

    def _collect_errors(self, error_cases: Iterable) -> dict:
        """Collect the errors.

        :param error_cases: an iterable with the error cases
        :type error_cases: Iterable
        :return: A dictionary with errors by case
        :rtype: dict
        """
        errors = {}
        for error_case in error_cases:
            check = error_case.get("check", "")
            column = error_case.get("column", "")
            failure_case = str(error_case.get("failure_case", ""))

            if check not in {"column_in_dataframe", "column_in_schema"}:
                check = "invalid_type" if "dtype" in check else "invalid_value"

            # If the check type is "column_in_dataframe" or "column_in_schema" the column name is in
            # "failure_case" field, otherwise it is in "column" and "failure_case" contains the field value
            failure_desc = {column: failure_case} if column else failure_case

            errors.setdefault(check, []).append(failure_desc)

        return errors
