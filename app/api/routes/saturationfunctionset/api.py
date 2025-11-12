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

from fastapi import APIRouter

from app.api.dependencies.validation import (
    validate_saturation_function_set_v2_payload,
)
from app.api.routes.saturationfunctionset.endpoints import (
    SaturationFunctionSetView,
)

SFS_ID_REGEX_STR = r"^[\w\-\.]+:work-product-component--SaturationFunctionSet:[\w\-\.\:\%]+$"

sfs_record_router_v2 = APIRouter()

SaturationFunctionSetView(
    router=sfs_record_router_v2,
    id_regex_str=SFS_ID_REGEX_STR,
    validate_records_payload=validate_saturation_function_set_v2_payload,
    record_type="SaturationFunctionSet",
)
