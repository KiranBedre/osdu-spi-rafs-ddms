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

from fastapi import APIRouter

from app.api.dependencies.validation import validate_master_data_records_payload
from app.api.routes.osdu.storage_records import BaseStorageRecordView
from app.api.routes.utils.records import parse_kind
from app.models.domain.osdu.base import MASTER_DATA_KINDS_V2

RECORD_TYPE_STR = f"({'|'.join(MASTER_DATA_KINDS_V2)})"  # noqa: WPS237
SUPPORTED_TYPES = f"({'|'.join([parse_kind(kind)['entity_type'] for kind in MASTER_DATA_KINDS_V2])})"  # noqa: WPS237
MD_ID_REGEX_STR = f"^[\w\-\.]+:{SUPPORTED_TYPES}:[\w\-\.\:\%]+$"  # noqa: W605

md_router = APIRouter()

BaseStorageRecordView(
    router=md_router,
    id_regex_str=MD_ID_REGEX_STR,
    validate_records_payload=validate_master_data_records_payload,
    record_type=RECORD_TYPE_STR,
)
