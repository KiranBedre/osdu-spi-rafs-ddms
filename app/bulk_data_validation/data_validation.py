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

import ast
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

_MAX_RECEIVED_REPR_LEN = 200


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
            return schema_errors  # noqa: ASYNC910

        data_integrity_errors = await self._validate_integrity(df)
        if data_integrity_errors:
            return {  # noqa: ASYNC910
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
        df_string = df.to_json()
        ids_to_check = find_osdu_ids_from_string(df_string)

        missing_records = set()
        for ids_to_check_batch in divide_chunks(list(ids_to_check), settings.storage_query_limit):
            missing_records.update(await self._find_missing_records(ids_to_check=ids_to_check_batch))

        return missing_records  # noqa: ASYNC910

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
        # Get Pydantic model and known fields once, before the loop
        pydantic_model = self._get_pydantic_model()
        known_fields = set(getattr(pydantic_model, "__fields__", {}).keys()) if pydantic_model else set()

        filtered_errors = []

        for error_case in error_cases:
            failure_case = error_case.get("failure_case", "")

            # Check if this error contains NaN in an optional field
            if self._is_nan_in_optional_field(failure_case, required_fields, known_fields, pydantic_model):
                logger.debug(f"Filtering NaN error for optional field in bulk mode: {failure_case}")
                continue

            # Keep all other errors (including NaN in required fields)
            filtered_errors.append(error_case)

        return filtered_errors

    def _is_nan_in_optional_field(self, failure_case, required_fields: set, known_fields: set, pydantic_model) -> bool:
        """Check if failure case is a NaN error in an optional field only.

        Returns True only when the sole cause of failure is NaN values in
        optional fields that are known to the schema. Returns False for:
        - Extra (unknown) columns — those are real schema violations.
        - Type/constraint violations that co-exist with optional NaN fields.

        :param failure_case: the failure case from pandera error
        :param required_fields: set of required field names
            :param known_fields: set of field names defined in the Pydantic model
            :param pydantic_model: the Pydantic model class, or None
        :return: True only if this error is purely NaN in optional known fields
        :rtype: bool
        """
        if isinstance(failure_case, str):
            return self._is_str_nan_in_optional_field(failure_case, known_fields, required_fields)

        if isinstance(failure_case, dict):
            return self._is_dict_nan_in_optional_field(failure_case, known_fields, required_fields, pydantic_model)

        return False

    def _is_str_nan_in_optional_field(self, failure_case: str, known_fields: set, required_fields: set) -> bool:
        """Check string-form failure case (e.g. \"{'Field': nan}\") for optional NaN.

        :param failure_case: string representation of the failure case
        :param known_fields: set of field names defined in the Pydantic model
        :param required_fields: set of required field names
        :return: True if the only NaN fields are optional known fields
        :rtype: bool
        """
        if "nan" not in failure_case.lower():
            return False
        field_matches = re.findall(r"['\"](\w+)['\"]:\s*nan", failure_case)
        return (
            bool(field_matches)
            and all(field in known_fields for field in field_matches)
            and all(field not in required_fields for field in field_matches)
        )

    def _is_dict_nan_in_optional_field(
        self,
        failure_case: dict,
        known_fields: set,
        required_fields: set,
        pydantic_model,
    ) -> bool:
        """Check dict failure case (full row) for optional NaN only.

        Rejects immediately if any field is unknown (extra-column violation).
        Re-validates the row with NaN optional fields removed to ensure no
        other constraint violations are masked.

        :param failure_case: row dict from PydanticModel coerce error
        :param known_fields: set of field names defined in the Pydantic model
        :param required_fields: set of required field names
        :param pydantic_model: the Pydantic model class, or None
        :return: True only if removing NaN optional fields makes the row valid
        :rtype: bool
        """
        if any(field_name not in known_fields for field_name in failure_case):
            return False

        cleaned = {
            field_name: field_value
            for field_name, field_value in failure_case.items()
            if not (self._is_scalar_nan(field_value) and field_name not in required_fields)
        }
        # True when at least one NaN optional field was stripped; pydantic
        # re-validation below may still set this to False.
        validation_result = cleaned != failure_case

        if pydantic_model:
            try:
                pydantic_model(**cleaned)
            except ValueError:
                validation_result = False

        return validation_result

    @staticmethod
    def _is_scalar_nan(field_value) -> bool:
        """Check if a value is a scalar NaN (not a list, dict, or array).

        :param field_value: the value to check
        :return: True only if value is a scalar NaN
        :rtype: bool
        """
        if isinstance(field_value, (list, dict)):
            return False
        try:
            return bool(pd.isna(field_value))
        except (ValueError, TypeError):
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

    @staticmethod
    def _unwrap_pydantic_error(column, raw_failure):
        """Unwrap pandera PydanticModel dtype errors.

        Pandera sets column="failure_case" for PydanticModel dtype errors
        and nests the row data inside the failure_case dict. Use "DataSchema"
        as a consistent column name to match other PydanticModel error cases.

        :param column: column name from pandera error
        :param raw_failure: raw failure_case value from pandera error
        :return: corrected (column, failure_case) tuple
        :rtype: tuple
        """
        if column == "failure_case" and isinstance(raw_failure, dict):
            return "DataSchema", raw_failure
        return column, raw_failure

    @staticmethod
    def _build_expected_desc(field_info) -> str:
        """Build a human-readable expected-type description from a Pydantic FieldInfo.

        :param field_info: Pydantic v1 FieldInfo object
        :return: expected type description string
        :rtype: str
        """
        regex = getattr(field_info.type_, "regex", None)
        type_name = getattr(field_info.type_, "__name__", None)

        if regex:
            return f"pattern: {regex.pattern}"
        if type_name in {"float", "int", "str", "bool", "date", "datetime"}:
            return type_name
        return str(field_info.outer_type_)

    def _enrich_pydantic_error(self, raw_failure: str) -> list:
        """Parse a PydanticModel failure_case string into field-level error dicts.

        :param raw_failure: Python-repr dict string from pandera failure_case
        :type raw_failure: str
        :return: list of enriched error dicts with field, received, expected keys
        :rtype: list
        """
        try:
            failed_fields = ast.literal_eval(raw_failure)
        except (ValueError, SyntaxError):
            return [{"field": "DataSchema", "received": raw_failure, "expected": "unknown"}]

        if not isinstance(failed_fields, dict):
            return [{"field": "DataSchema", "received": raw_failure, "expected": "unknown"}]

        pydantic_model = self._get_pydantic_model()
        model_fields = getattr(pydantic_model, "__fields__", {}) if pydantic_model else {}

        enriched = []
        for field_name, received_val in failed_fields.items():
            field_info = model_fields.get(field_name)
            expected_desc = self._build_expected_desc(field_info) if field_info else "unknown"
            received_repr = repr(received_val)
            if len(received_repr) > _MAX_RECEIVED_REPR_LEN:
                received_repr = received_repr[:_MAX_RECEIVED_REPR_LEN]
                received_repr = f"{received_repr}...[truncated]"
            enriched.append(
                {
                    "field": field_name,
                    "received": received_repr,
                    "expected": expected_desc,
                },
            )
        return enriched

    @staticmethod
    def _normalise_check(check: str) -> str:
        """Map a pandera check name to a canonical error category key.

        :param check: raw check name from pandera
        :type check: str
        :return: canonical check key
        :rtype: str
        """
        if check in {"column_in_dataframe", "column_in_schema"}:
            return check
        return "invalid_type" if "dtype" in check else "invalid_value"

    def _collect_errors(self, error_cases: Iterable) -> dict:
        """Collect the errors.

        :param error_cases: an iterable with the error cases
        :type error_cases: Iterable
        :return: A dictionary with errors by case
        :rtype: dict
        """
        errors = {}
        for error_case in error_cases:
            check = self._normalise_check(error_case.get("check", ""))
            column = error_case.get("column", "")
            raw_failure = error_case.get("failure_case", "")

            column, raw_failure = self._unwrap_pydantic_error(column, raw_failure)

            if column == "DataSchema":
                enriched_list = self._enrich_pydantic_error(str(raw_failure))
                errors.setdefault(check, []).extend(enriched_list)
                continue

            # If the check type is "column_in_dataframe" or "column_in_schema" the column name is in
            # "failure_case" field, otherwise it is in "column" and "failure_case" contains the field value
            failure_case = str(raw_failure)
            failure_desc = {column: failure_case} if column else failure_case
            errors.setdefault(check, []).append(failure_desc)

        return errors
