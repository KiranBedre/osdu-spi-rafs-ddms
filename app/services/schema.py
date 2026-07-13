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

import datetime
import re
from typing import Any, Optional

import jsonschema
from async_lru import alru_cache
from dateutil import parser as date_parser
from fastapi_cache.decorator import cache
from httpx import HTTPStatusError
from loguru import logger
from starlette import status

from app.core.helpers.cache.key_builder import key_builder_for_service_methods
from app.core.helpers.cache.settings import CACHE_DEFAULT_TTL
from app.core.settings.app import AppSettings
from app.models.schemas.user import User
from app.services.error_handlers import handle_core_services_http_status_error
from app.services.osdu_clients.schema_client import SchemaServiceApiClient

# Create a custom format checker instance
custom_format_checker = jsonschema.FormatChecker()


@custom_format_checker.checks("date-time", raises=jsonschema.exceptions.FormatError)
def validate_date_time(str_value: str) -> bool:
    """Check if a date-time value follows formats specified in indexer:

    :param value: date-time value
    :type value: str
    :return: does date-time value follow Indexer's format.
    :rtype: bool
    """
    if not isinstance(str_value, str):
        return False

    try:
        # Check if a date-time value's format is "EEE MMM dd HH:mm:ss zzz yyyy".
        # If it is not, assume that value follows ISO 8601 standart.
        if re.fullmatch(r"\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2} \w{3} \d{4}", str_value):
            date_parser.parse(str_value)
        else:
            date_parser.isoparse(str_value)
        return True
    except (date_parser.ParserError, ValueError):
        return False


@custom_format_checker.checks("time", raises=jsonschema.exceptions.FormatError)
def validate_time(str_value: str) -> bool:
    """Check if a time value follows isoformat:

    :param value: time value
    :type value: str
    :return: does time value follow isoformat.
    :rtype: bool
    """
    try:
        datetime.time.fromisoformat(str_value)
        return True
    except (TypeError, ValueError):
        return False


class OSDURefResolver(jsonschema.RefResolver):
    """Extends base jsonschema resolver for OSDU.

    Note: RefResolver is deprecated as of jsonschema v4.18.0 in favor of the
    'referencing' library. Migration to the new API requires significant
    refactoring to preserve the custom $id handling behavior.
    TODO: Migrate to jsonschema.referencing library (see https://github.com/python-jsonschema/referencing)
    """

    def resolve_fragment(self, document: dict, fragment: str) -> dict:
        """Add deleting $id field, as long as RefResolver uses the "$id" for
        resolving references instead of searching for these references in
        "definitions" field.

        :param document: The schema document
        :type document: dict
        :param fragment: schema fragment
        :type fragment: str
        :return: The updated schema document
        :rtype: dict
        """
        document = super().resolve_fragment(document, fragment)
        # /definitions/<OsduID> -> [..., <OsduID>]
        fragment_parts = fragment.split("/")
        if len(fragment_parts) > 1:
            document["$id"] = ""
        return document


class SchemaService(object):
    """Class to get and validate wks schemas."""

    def __init__(
        self,
        data_partition_id: str,
        settings: AppSettings,
        user: User,
        extra_headers: dict,
    ) -> None:
        self.schema_client = SchemaServiceApiClient(
            base_url=settings.service_host_schema,
            data_partition_id=data_partition_id,
            bearer_token=user.access_token,
            extra_headers=extra_headers,
        )
        self._schema_validators = {}

    @handle_core_services_http_status_error(
        expected_codes=[
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ],
        detail="Failed to fetch schema from SchemaService.",
    )
    @alru_cache(maxsize=None)
    @cache(expire=CACHE_DEFAULT_TTL, key_builder=key_builder_for_service_methods)
    async def get_schema(self, schema_id: str) -> dict:
        """Get schema from schema service.

        :param schema_id: schema id
        :type schema_id: str
        :return: the schema
        :rtype: dict
        """
        logger.info(f"Fetching {schema_id}")
        return await self.schema_client.get_schema(schema_id)

    async def validate(self, record: dict, schema_id: str, optional_id: Optional[str] = None) -> Optional[dict]:
        """Validate a record against its schema using jsonschema.

        :param record: the record
        :type record: dict
        :param schema_id: the schema id
        :type schema_id: str
        :param optional_id: optional id in case no default id is
            provided, defaults to None
        :type optional_id: Optional[str], optional
        :return: a dict with list of errors if found
        :rtype: Optional[dict]
        """
        logger.info(f"Validating {schema_id}")
        logger.info(record["kind"])
        try:
            errors = [error.message for error in await self._validate_against_schema(record, schema_id)]
        except HTTPStatusError as exc:
            if exc.response.status_code == status.HTTP_404_NOT_FOUND:
                logger.warning(f"Schema '{schema_id}' not found in schema service, skipping validation.")
                return None  # noqa: ASYNC910
            raise
        if errors:
            error_dict = {
                "id": record.get("id", optional_id),
                "kind": schema_id,
                "errors": errors,
            }
            logger.debug(error_dict)
            return error_dict

    def _get_schema_validator(self, schema: dict, schema_id: str) -> Any:
        """Get custom schema validator for OSDU Forum schemas.

        :param schema: the schema definition
        :type schema: dict
        :param schema_id: the schema id
        :type schema_id: str
        :return: validator
        :rtype: Any
        """
        if self._schema_validators.get(schema_id):
            return self._schema_validators[schema_id]

        validator_class = jsonschema.validators.validator_for(schema)
        resolver = OSDURefResolver(
            base_uri=schema.get("$id", ""),
            referrer=schema,
            cache_remote=True,
        )
        validator = validator_class(
            schema=schema,
            resolver=resolver,
            format_checker=custom_format_checker,
        )
        self._schema_validators[schema_id] = validator
        return validator

    async def _validate_against_schema(self, record: dict, schema_id: str) -> list:
        """Validate a record agains its schema.

        :param record: the record
        :type record: dict
        :param schema_id: the schema id
        :type schema_id: str
        :return: list of errors if any
        :rtype: list
        """
        schema = await self.get_schema(schema_id)
        validator = self._get_schema_validator(schema, schema_id)
        return validator.iter_errors(record)
