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
from typing import Iterable, get_args

import pandas as pd
import pandera as pa
from loguru import logger
from pydantic import BaseModel, ValidationError

from app.api.routes.utils.query import divide_chunks, find_osdu_ids_from_string
from app.core.config import get_app_settings
from app.services.storage import StorageService

settings = get_app_settings()

_MAX_RECEIVED_REPR_LEN = 200
_QUALNAME_PATTERN = re.compile(r"(?:[\w]+\.)+(\w+)")


@dataclass
class DataValidator(object):
    data_schema: pa.DataFrameSchema
    storage_service: StorageService
    api_version: str

    async def validate(self, df: pd.DataFrame, bulk_mode: bool = False) -> dict:  # noqa: ASYNC910
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
                errors = self._collect_errors(error_cases, df)

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

    async def _validate_integrity(self, df: pd.DataFrame) -> set:  # noqa: ASYNC910
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

            # Filter NaN in extra columns (column_in_schema with NaN inside row dict)
            if isinstance(failure_case, dict) and self._is_nan_in_extra_field(failure_case, known_fields):
                logger.debug(f"Filtering NaN error for extra field in bulk mode: {failure_case}")
                continue

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

    def _is_nan_in_extra_field(self, failure_case: dict, known_fields: set) -> bool:
        """Check if failure case contains only NaN values in extra (unknown) fields.

        This helper identifies when a row dict contains only NaN values in fields
        that are not defined in the Pydantic schema. These represent harmless
        DataFrame column-alignment artifacts rather than true schema violations.

        :param failure_case: row dict from error
        :param known_fields: set of field names defined in the Pydantic model
        :return: True if all fields in failure_case are extra (unknown) with NaN values
        :rtype: bool
        """
        return all(
            field_name not in known_fields and self._is_scalar_nan(field_value)
            for field_name, field_value in failure_case.items()
        )

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

    # -------------------------------------------------------------------------
    # Pydantic v1 enrichment methods
    # All methods below use Pydantic v1 internals: ModelField.type_,
    # field_info.const, ModelField.default, ValidationError.errors() structure,
    # and error type strings ("value_error.missing", "value_error.extra", ...).
    # When migrating to Pydantic v2 these methods should be replaced as a unit;
    # the DataValidator orchestration above (row recovery, schema lookup) is
    # version-agnostic and can be retained.
    # -------------------------------------------------------------------------

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

        Extracts type constraints (regex patterns, simple type names) and formats
        complex types by removing the 'typing.' module prefix for readability.

        :param field_info: Pydantic v1 FieldInfo object
        :return: expected type description string
        :rtype: str
        """
        if field_info is None:
            return "unknown"

        type_description = "unknown"
        regex = getattr(field_info.type_, "regex", None)
        type_name = getattr(field_info.type_, "__name__", None)

        if regex:
            type_description = f"pattern: {regex.pattern}"
        elif type_name in {"float", "int", "str", "bool", "date", "datetime"}:
            type_description = type_name
        else:
            # Collapse fully-qualified names (e.g. 'typing.List', 'app.models....Meta')
            # down to their bare name for readability.
            type_description = _QUALNAME_PATTERN.sub(r"\1", str(field_info.outer_type_))

        return type_description

    @staticmethod
    def _truncated_repr(received_val) -> str:
        """Repr a value, truncating if it exceeds the max display length.

        :param received_val: the value to represent
        :return: repr string, truncated with a marker if too long
        :rtype: str
        """
        received_repr = repr(received_val)
        if len(received_repr) > _MAX_RECEIVED_REPR_LEN:
            truncated = received_repr[:_MAX_RECEIVED_REPR_LEN]
            received_repr = f"{truncated}...[truncated]"
        return received_repr

    def _enrich_pydantic_error(self, raw_failure: str, index=None, df: pd.DataFrame = None) -> list:
        """Parse a PydanticModel failure_case string into field-level error dicts.

        Re-validates the failing row against the real Pydantic model to recover
        the actual per-field errors (missing/extra/invalid). Pandera's
        failure_case for a row-level PydanticModel check is NOT reliably the
        complete row — it sometimes reports only a subset of fields — so a
        genuine full row is recovered from ``df`` via ``index`` when available;
        otherwise the parsed failure_case is used as a best-effort fallback.

        :param raw_failure: Python-repr dict string from pandera failure_case
        :type raw_failure: str
        :param index: the row index reported in the pandera failure case
        :param df: the dataframe being validated
        :type df: pd.DataFrame
        :return: list of enriched error dicts with field, received, expected keys
        :rtype: list
        """
        try:
            parsed_failure = ast.literal_eval(raw_failure)
        except (ValueError, SyntaxError):
            parsed_failure = None

        if not isinstance(parsed_failure, dict):
            return [{"field": "DataSchema", "received": raw_failure, "expected": "unknown"}]

        true_row = self._resolve_true_row(index, df)
        failed_fields = parsed_failure if true_row is None else true_row

        pydantic_model = self._get_pydantic_model()
        validation_errors = self._revalidate_with_pydantic(pydantic_model, failed_fields)
        if true_row is None:
            validation_errors = self._errors_for_reported_fields(validation_errors, parsed_failure)
        if pydantic_model is not None and validation_errors:
            enriched = self._enrich_from_validation_errors(failed_fields, pydantic_model, validation_errors)
            if enriched:
                return enriched
            # All validation errors had empty loc (e.g. a root validator) — none
            # mapped to a field, so _enrich_from_validation_errors returned [].
            # Fall through to the legacy path so the failure is not dropped.

        # Re-validation couldn't confirm the failure (or produced only
        # locationless errors): fall back to the fields pandera actually
        # reported. The reconstructed full row must not be used here — it
        # would flag every valid column as an error.
        return self._enrich_pydantic_error_legacy(parsed_failure, pydantic_model)

    def _resolve_true_row(self, index, df: pd.DataFrame) -> dict:
        """Recover the actual full input row from the dataframe, if possible.

        :param index: the row index reported in the pandera failure case
        :param df: the dataframe being validated
        :return: the recovered row as a dict, or None if it can't be resolved
        :rtype: dict | None
        """
        row_index = self._resolve_row_index(index, df)
        if row_index is None:
            return None

        row = df.loc[row_index]
        if not isinstance(row, pd.Series):
            # Duplicate index labels: .loc returns a DataFrame and the true
            # row is ambiguous, so fall back to the parsed failure case.
            return None

        return self._row_to_input_dict(row)

    def _row_to_input_dict(self, row: pd.Series) -> dict:
        """Convert a dataframe row back into the input dict Pydantic should see.

        Float-NaN cells for known model fields are dropped so a genuinely absent
        optional field (a DataFrame column-alignment artifact) does not reach
        Pydantic as a literal NaN.  Explicit ``None`` values are preserved: a
        caller-submitted null is a real value, not an absent field, and must be
        validated accordingly.

        Unknown-field float-NaN cells are kept as ``None`` since an extra column
        with a null value is still an extra-column violation.

        :param row: the recovered dataframe row
        :type row: pd.Series
        :return: the row as an input dict
        :rtype: dict
        """
        pydantic_model = self._get_pydantic_model()
        known_fields = set(getattr(pydantic_model, "__fields__", {}).keys()) if pydantic_model else set()

        true_row = {}
        for column_name, cell_value in row.items():
            is_float_nan = self._is_float_nan(cell_value)
            if is_float_nan and column_name in known_fields:
                continue
            true_row[column_name] = None if is_float_nan else cell_value
        return true_row

    @staticmethod
    def _resolve_row_index(index, df: pd.DataFrame):
        """Match the pandera failure-case index to an actual row in ``df``.

        :param index: the row index reported in the pandera failure case
        :param df: the dataframe being validated
        :return: a valid ``df.index`` label, or None if it can't be resolved
        """
        if df is None or index is None:
            return None
        if index in df.index:
            return index
        try:
            candidate = int(index)
        except (TypeError, ValueError):
            candidate = None
        return candidate if candidate in df.index else None

    @staticmethod
    def _is_nan(cell_value) -> bool:
        """Safely check whether a dataframe cell value is NaN.

        :param cell_value: the cell value; may be a scalar, list, or dict
        :return: True if the value is NaN, False otherwise (never raises on
            non-scalar values, unlike a bare ``pd.isna()`` check)
        :rtype: bool
        """
        if isinstance(cell_value, (list, dict)):
            return False
        try:
            return bool(pd.isna(cell_value))
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _is_float_nan(cell_value) -> bool:
        """Check whether a cell value is a NaN float (not an explicit ``None``).

        ``pd.isna`` treats ``None`` and ``float('nan')`` identically, making it
        impossible to distinguish an explicitly-submitted null from an absent
        field.  This method returns ``True`` only for non-``None`` NaN-like
        scalars (typically ``numpy.float64`` column-alignment placeholders),
        so explicit ``None`` values are preserved for downstream reporting.

        :param cell_value: the cell value; may be a scalar, list, or dict
        :return: True only if the value is a non-None NaN scalar
        :rtype: bool
        """
        if cell_value is None or isinstance(cell_value, (list, dict)):
            return False
        try:
            return bool(pd.isna(cell_value))
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _errors_for_reported_fields(validation_errors: list, reported_fields: dict) -> list:
        """Keep only the errors belonging to fields pandera actually reported.

        When the true row can't be recovered, the parsed failure case may be a
        partial row; re-validating it invents 'missing' errors for fields the
        user may well have provided, so those speculative errors are dropped.

        :param validation_errors: ``pydantic.ValidationError.errors()`` for the row
        :param reported_fields: the fields present in the parsed failure case
        :return: the errors whose top-level field was reported by pandera
        :rtype: list
        """
        return [err for err in validation_errors if err.get("loc") and err["loc"][0] in reported_fields]

    @staticmethod
    def _revalidate_with_pydantic(pydantic_model, failed_fields: dict) -> list:
        """Re-run the row through the real Pydantic model to get authoritative errors.

        :param pydantic_model: the Pydantic model class, or None
        :param failed_fields: the raw input row that failed pandera's coerce check
        :return: list of pydantic error dicts (empty if the row actually validates
            in isolation, or the model is unavailable)
        :rtype: list
        """
        if pydantic_model is None:
            return []
        errors: list = []
        try:
            pydantic_model(**failed_fields)
        except ValidationError as exc:
            errors = exc.errors()
        except TypeError:
            errors = []
        return errors

    def _enrich_pydantic_error_legacy(self, failed_fields: dict, pydantic_model) -> list:
        """Fallback enrichment when re-validation can't confirm the failure.

        :param failed_fields: the raw input row that failed pandera's coerce check
        :param pydantic_model: the Pydantic model class, or None
        :return: list of enriched error dicts with field, received, expected keys
        :rtype: list
        """
        model_fields = getattr(pydantic_model, "__fields__", {}) if pydantic_model else {}
        enriched = []
        for field_name, received_val in failed_fields.items():
            field_info = model_fields.get(field_name)
            enriched.append(
                {
                    "field": field_name,
                    "received": self._truncated_repr(received_val),
                    "expected": self._build_expected_desc(field_info) if field_info else "unknown",
                },
            )
        return enriched

    def _enrich_from_validation_errors(self, failed_fields: dict, pydantic_model, validation_errors: list) -> list:
        """Group real Pydantic validation errors by top-level field and enrich each.

        :param failed_fields: the raw input row that failed pandera's coerce check
        :param pydantic_model: the Pydantic model class
        :param validation_errors: ``pydantic.ValidationError.errors()`` for the row
        :return: list of enriched error dicts with field, received, expected keys
        :rtype: list
        """
        model_fields = getattr(pydantic_model, "__fields__", {})
        grouped: dict = {}
        for err in validation_errors:
            loc = err.get("loc", ())
            if loc:
                grouped.setdefault(loc[0], []).append(err)

        enriched = []
        for field_name, field_errors in grouped.items():
            field_info = model_fields.get(field_name)
            top_level_errors = [single_err for single_err in field_errors if len(single_err["loc"]) == 1]
            raw_value = failed_fields.get(field_name)

            if top_level_errors:
                enriched.append(self._build_field_error(field_name, top_level_errors[0], raw_value, field_info))
            elif field_info is None:
                enriched.append(
                    {"field": field_name, "received": self._truncated_repr(raw_value), "expected": "unknown"},
                )
            else:
                enriched.extend(self._enrich_nested_field_errors(field_name, field_info, raw_value))
        return enriched

    def _build_field_error(self, field_name: str, err: dict, raw_value, field_info) -> dict:
        """Build one enriched error dict from a single Pydantic error entry.

        :param field_name: dotted/indexed field path to report (e.g. "Meta[0].kind")
        :param err: a single entry from ``pydantic.ValidationError.errors()``
        :param raw_value: the original value submitted for this field, if resolvable
        :param field_info: the Pydantic FieldInfo for this field, if resolvable
        :return: enriched error dict with field, received, expected keys
        :rtype: dict
        """
        err_type = err.get("type", "")
        if "missing" in err_type:
            return {"field": field_name, "received": "missing", "expected": "required field"}
        if "extra" in err_type:
            received = "null" if raw_value is None else "present"
            return {"field": field_name, "received": received, "expected": "not allowed (extra field)"}
        return {
            "field": field_name,
            "received": self._truncated_repr(raw_value),
            "expected": self._build_expected_desc(field_info) if field_info else "unknown",
        }

    def _enrich_nested_field_errors(self, field_name: str, field_info, raw_value) -> list:
        """Resolve errors nested inside a Union/List-of-submodel field.

        Tries each candidate submodel type (e.g. each member of
        ``Union[Meta, Meta1, Meta2, Meta3]``) against the offending item and picks
        the one with the fewest errors (closest match), so only the relevant
        sub-model's errors are surfaced instead of every union member's.

        :param field_name: the top-level field name (e.g. "Meta")
        :param field_info: the Pydantic FieldInfo for this field
        :param raw_value: the original value submitted for this field
        :return: list of enriched error dicts with field, received, expected keys
        :rtype: list
        """
        candidates = self._extract_submodel_candidates(field_info.type_)
        fallback = [
            {
                "field": field_name,
                "received": self._truncated_repr(raw_value),
                "expected": self._build_expected_desc(field_info),
            },
        ]
        if not candidates:
            return fallback

        is_list = isinstance(raw_value, list)
        row_items = raw_value if is_list else [raw_value]

        enriched = []
        for position, row_item in enumerate(row_items):
            prefix = f"{field_name}[{position}]" if is_list else field_name
            if not isinstance(row_item, dict):
                # Non-dict scalar inside a typed list: report it directly rather
                # than silently skipping, so mixed-list errors are not lost.
                enriched.append(
                    {
                        "field": prefix,
                        "received": self._truncated_repr(row_item),
                        "expected": self._build_expected_desc(field_info),
                    },
                )
                continue
            enriched.extend(self._enrich_item_errors(prefix, row_item, candidates))
        return enriched or fallback

    def _enrich_item_errors(self, prefix: str, row_item: dict, candidates: list) -> list:
        """Enrich the errors for a single nested item against its best-matching candidate.

        :param prefix: the field path prefix for this item (e.g. "Meta[0]")
        :param row_item: the raw nested dict to validate
        :param candidates: list of BaseModel subclasses to try
        :return: list of enriched error dicts with field, received, expected keys
        :rtype: list
        """
        item_errors, item_model_fields = self._best_matching_candidate_errors(candidates, row_item)
        return [self._build_leaf_error(prefix, row_item, item_model_fields, leaf_err) for leaf_err in item_errors]

    def _build_leaf_error(self, prefix: str, row_item: dict, item_model_fields: dict, leaf_err: dict) -> dict:
        """Build one enriched error dict for a single leaf error inside a nested item.

        :param prefix: the field path prefix for this item (e.g. "Meta[0]")
        :param row_item: the raw nested dict the leaf error belongs to
        :param item_model_fields: the ``__fields__`` of the best-matching candidate model
        :param leaf_err: a single entry from ``pydantic.ValidationError.errors()``
        :return: enriched error dict with field, received, expected keys
        :rtype: dict
        """
        leaf_path = leaf_err.get("loc", ())
        path_label = ".".join(str(part) for part in leaf_path) if leaf_path else "unknown"
        leaf_value, leaf_field_info = self._resolve_leaf_context(row_item, item_model_fields, leaf_path)
        return self._build_field_error(f"{prefix}.{path_label}", leaf_err, leaf_value, leaf_field_info)

    @classmethod
    def _resolve_leaf_context(cls, row_item: dict, item_model_fields: dict, leaf_path: tuple) -> tuple:
        """Walk the full error ``loc`` path down to the offending leaf value.

        Resolving only the first path segment would report a whole nested
        object as ``received`` for a deep error such as
        ``Conditions.Pressure``; the traversal follows dict keys and list
        positions to the leaf instead, tracking the matching FieldInfo.

        :param row_item: the raw nested dict the error belongs to
        :param item_model_fields: the ``__fields__`` of the item's model
        :param leaf_path: the ``loc`` tuple from a pydantic error entry
        :return: (leaf value, leaf FieldInfo or None)
        :rtype: tuple
        """
        current_value = row_item
        current_fields = item_model_fields
        leaf_field_info = None
        for path_part in leaf_path:
            if isinstance(path_part, int):
                current_value = cls._value_at_position(current_value, path_part)
                continue
            leaf_field_info = current_fields.get(path_part) if current_fields else None
            current_value = current_value.get(path_part) if isinstance(current_value, dict) else None
            current_fields = cls._nested_model_fields(leaf_field_info)
        return current_value, leaf_field_info

    @staticmethod
    def _value_at_position(container, position: int):
        """Safely index into a list/tuple, returning None when out of range.

        :param container: the value to index into; may not be a sequence
        :param position: the list position from a pydantic error ``loc``
        :return: the element at ``position``, or None if not resolvable
        """
        is_sequence = isinstance(container, (list, tuple))
        if is_sequence and -len(container) <= position < len(container):
            return container[position]
        return None

    @staticmethod
    def _nested_model_fields(model_field) -> dict:
        """Get the ``__fields__`` of a field's submodel type, if it has one.

        :param model_field: a Pydantic ModelField, or None
        :return: the submodel's fields dict, empty if the field isn't a submodel
        :rtype: dict
        """
        nested_type = model_field.type_ if model_field else None
        if isinstance(nested_type, type) and issubclass(nested_type, BaseModel):
            return nested_type.__fields__
        return {}

    @staticmethod
    def _extract_submodel_candidates(field_type) -> list:
        """Extract candidate BaseModel subclasses from a (possibly Union) field type.

        **Pydantic v1 note:** ``field_type`` is expected to be ``ModelField.type_``,
        which pydantic v1 sets to the *innermost* type after stripping ``List``
        and ``Optional`` wrappers.  For a ``List[Union[A, B]]`` field,
        ``type_`` resolves to ``Union[A, B]``, and ``get_args`` correctly returns
        ``(A, B)``.  For ``Optional[A]``, ``type_`` resolves to ``A`` directly.
        This covers all Union/List-of-submodel patterns present in current RAFS
        schemas.  If more complex nesting is needed in future (e.g.
        ``Union[List[A], List[B]]``), consider using ``ModelField.sub_fields``
        instead for a more robust traversal.

        :param field_type: a Pydantic v1 FieldInfo's ``type_`` (already unwrapped of List/Optional)
        :return: list of BaseModel subclasses to try, empty if none apply
        :rtype: list
        """
        args = get_args(field_type)
        if args:
            return [arg for arg in args if isinstance(arg, type) and issubclass(arg, BaseModel)]
        if isinstance(field_type, type) and issubclass(field_type, BaseModel):
            return [field_type]
        return []

    @staticmethod
    def _try_candidate(candidate, candidate_item: dict):
        """Validate one candidate submodel against the item.

        :param candidate: BaseModel subclass to try
        :param candidate_item: the raw nested dict to validate
        :return: list of pydantic errors (empty if fully valid), or None if the
            item's keys aren't even applicable to this candidate
        :rtype: list | None
        """
        try:
            candidate(**candidate_item)
        except ValidationError as exc:
            return exc.errors()
        except TypeError:
            return None
        return []

    @classmethod
    def _narrow_candidates_by_discriminator(cls, candidates: list, candidate_item: dict) -> list:
        """Keep only union members whose const fields match the item's values.

        Union submodels are typically discriminated by a const field such as
        ``kind``. When the item provides that field, candidates declaring a
        different const value cannot be the intended model, even if they
        happen to produce fewer validation errors. Falls back to the full
        candidate list when nothing matches (e.g. the discriminator value
        itself is invalid).

        :param candidates: list of BaseModel subclasses to narrow
        :param candidate_item: the raw nested dict to validate
        :return: the matching candidates, or all of them if none match
        :rtype: list
        """
        matched = [candidate for candidate in candidates if cls._const_fields_match(candidate, candidate_item)]
        return matched or candidates

    @staticmethod
    def _const_fields_match(candidate, candidate_item: dict) -> bool:
        """Check the item's values against the candidate's const-restricted fields.

        :param candidate: BaseModel subclass to check
        :param candidate_item: the raw nested dict to validate
        :return: False if the item contradicts any const field, True otherwise
        :rtype: bool
        """
        for field_name, model_field in getattr(candidate, "__fields__", {}).items():
            is_const = getattr(model_field.field_info, "const", None)
            if not is_const or field_name not in candidate_item:
                continue
            if candidate_item[field_name] != model_field.default:
                return False
        return True

    @classmethod
    def _best_matching_candidate_errors(cls, candidates: list, candidate_item: dict) -> tuple:
        """Try each candidate model against ``candidate_item`` and return the closest match's errors.

        Candidates are first narrowed by const discriminator fields (e.g.
        ``kind``), so the error-count heuristic only breaks ties between
        candidates the item could actually be.

        :param candidates: list of BaseModel subclasses to try
        :param candidate_item: the raw nested dict to validate
        :return: (errors, model_fields) for the best-matching candidate;
            an empty errors list and empty fields dict if some candidate
            actually validates the item
        :rtype: tuple
        """
        scored = []
        for candidate in cls._narrow_candidates_by_discriminator(candidates, candidate_item):
            errors = cls._try_candidate(candidate, candidate_item)
            if errors is None:
                continue
            if not errors:
                return [], {}
            scored.append((errors, candidate))

        if not scored:
            return [], {}
        best_errors, best_candidate = min(scored, key=lambda scored_pair: len(scored_pair[0]))
        return best_errors, getattr(best_candidate, "__fields__", {})

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

    def _enrich_error_with_field_info(self, column_name: str, check: str) -> dict:
        """Enrich missing/extra column errors with field-level details.

        :param column_name: the column name (missing or extra)
        :type column_name: str
        :param check: the check type ("column_in_dataframe" or "column_in_schema")
        :type check: str
        :return: enriched error dict with field, received, expected keys
        :rtype: dict
        """
        if check == "column_in_dataframe":
            # Column is in schema but missing from dataframe
            received = "missing"
            expected = "required column"
        elif check == "column_in_schema":
            # Column is in dataframe but not in schema (extra field)
            received = "present"
            expected = "not allowed (extra field)"
        else:
            # Fallback for unknown check types
            received = "unknown"
            expected = "unknown"

        return {
            "field": column_name,
            "received": received,
            "expected": expected,
        }

    def _should_enrich_column_error(self, column: str, check: str) -> bool:
        """Check if error should be enriched as column_in_dataframe/schema error.

        :param column: column name (None for missing/extra column errors)
        :type column: str
        :param check: the check type
        :type check: str
        :return: True if this is a missing/extra column error to enrich
        :rtype: bool
        """
        return column is None and ("column_in_dataframe" in check or "column_in_schema" in check)

    def _collect_errors(self, error_cases: Iterable, df: pd.DataFrame = None) -> dict:
        """Collect the errors.

        :param error_cases: an iterable with the error cases
        :type error_cases: Iterable
        :param df: the dataframe being validated, used to recover the true
            failing row for PydanticModel errors
        :type df: pd.DataFrame
        :return: A dictionary with errors by case
        :rtype: dict
        """
        errors = {}
        for error_case in error_cases:
            check = self._normalise_check(error_case.get("check", ""))
            column = error_case.get("column", "")
            raw_failure = error_case.get("failure_case", "")
            index = error_case.get("index")

            column, raw_failure = self._unwrap_pydantic_error(column, raw_failure)

            if column == "DataSchema":
                enriched_list = self._enrich_pydantic_error(str(raw_failure), index=index, df=df)
                errors.setdefault(check, []).extend(enriched_list)
                continue

            # Enrich missing/extra column errors (cases 1 & 3)
            if self._should_enrich_column_error(column, check):
                enriched_error = self._enrich_error_with_field_info(str(raw_failure), check)
                errors.setdefault(check, []).append(enriched_error)
                continue

            # If the check type is "column_in_dataframe" or "column_in_schema" the column name is in
            # "failure_case" field, otherwise it is in "column" and "failure_case" contains the field value
            failure_case = str(raw_failure)
            failure_desc = {column: failure_case} if column else failure_case
            errors.setdefault(check, []).append(failure_desc)

        return errors
