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

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Extra, Field


class StorageUpsertResponse(BaseModel):
    recordCount: int = Field(alias="record_count")
    recordIdVersions: List[str] = Field(alias="record_id_versions")
    skippedRecordCount: int = Field(alias="skipped_record_count")


class Acl(BaseModel):
    viewers: List[str]
    owners: List[str]

    class Config:
        extra = Extra.forbid


class Legal(BaseModel):
    legaltags: List[str]
    otherRelevantDataCountries: List[str]
    status: Optional[str]

    class Config:
        extra = Extra.forbid


class OsduStorageRecord(BaseModel):
    id: Optional[str] = None
    kind: str
    acl: Acl
    legal: Legal
    data: Dict[str, Any]
    meta: Optional[list] = None
    ancestry: Optional[dict] = None
    tags: Optional[dict] = None
    version: Optional[int] = None
    createUser: Optional[str] = None
    createTime: Optional[str] = None
    modifyUser: Optional[str] = None
    modifyTime: Optional[str] = None
