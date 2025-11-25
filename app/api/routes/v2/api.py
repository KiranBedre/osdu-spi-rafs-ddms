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

from fastapi import APIRouter, Depends

from app.api.dependencies.request import require_data_partition_id
from app.api.routes.reservoirsimulationrockphysicsmodel import (
    api as reservoirsimulationrockphysics_api,
)
from app.api.routes.samplesanalysesreport import (
    api as sampleanalysesreport_api,
)
from app.api.routes.samplesanalysis import api as sampleanalysis_api
from app.api.routes.saturationfunctionset import (
    api as saturationfunctionset_api,
)
from app.api.routes.v2.master_data import api as masterdata_api
from app.resources.paths import RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR

COMMON_DEPENDENCIES = (
    Depends(require_data_partition_id),
)

SAMPLES_ANALYSIS_PREFIX = "/samplesanalysis"
router = APIRouter()

router.include_router(
    sampleanalysesreport_api.sar_record_router_v2,
    prefix="/samplesanalysesreport",
    tags=["samplesanalysesreport"],
    dependencies=COMMON_DEPENDENCIES,
)
router.include_router(
    sampleanalysis_api.sa_router,
    prefix=SAMPLES_ANALYSIS_PREFIX,
    tags=["samplesanalysis"],
    dependencies=COMMON_DEPENDENCIES,
)
router.include_router(
    saturationfunctionset_api.sfs_record_router_v2,
    prefix="/saturationfunctionset",
    tags=["saturationfunctionset"],
    dependencies=COMMON_DEPENDENCIES,
)

router.include_router(
    masterdata_api.md_router,
    prefix="/masterdata",
    tags=["masterdata"],
    dependencies=COMMON_DEPENDENCIES,
)

router.include_router(
    reservoirsimulationrockphysics_api.rsrp_router,
    prefix=f"/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
    tags=[RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR],
    dependencies=COMMON_DEPENDENCIES,
)
