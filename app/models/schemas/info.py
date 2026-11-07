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

from pydantic import BaseModel


class InfoResponse(BaseModel):
    name: str = None
    app_version: str = None
    build_time: str = None
    branch: str = None
    commit_id: str = None
    commit_message: str = None
    release_version: str = None


class CommonInfoResponse(BaseModel):
    """Build information using the field names common to all OSDU services."""

    groupId: str = None
    artifactId: str = None
    version: str = None
    buildTime: str = None
    branch: str = None
    commitId: str = None
    commitMessage: str = None
