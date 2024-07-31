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

from fastapi import APIRouter, Depends

from app.api.dependencies.request import require_data_partition_id
from app.dev.api.routes.v_dev.index import api as index_api
from app.dev.api.routes.v_dev.samplesanalysis import api as sampleanalysis_api

COMMON_DEPENDENCIES = [
    Depends(require_data_partition_id),
]

SAMPLES_ANALYSIS_PREFIX = "/samplesanalysis"
router = APIRouter()

router.include_router(
    sampleanalysis_api.sa_router,
    prefix=SAMPLES_ANALYSIS_PREFIX,
    tags=["dev-samplesanalysis"],
    dependencies=COMMON_DEPENDENCIES,
)

router.include_router(
    index_api.ix_router,
    prefix="",
    tags=["index"],
    dependencies=COMMON_DEPENDENCIES,
)
