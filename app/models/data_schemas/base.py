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

from app.models.data_schemas.sample_analysis_api_v2.base import PATH_TO_DATA_MODEL_VERSIONS_API_V2
from app.models.data_schemas.reservoir_simulation_rock_physics_v2.base import MAP_TO_RSRP_MODELS_API_V2
from app.resources.paths import RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR
from app.models.data_schemas.saturation_function_set_api_v2.base import MAP_TO_SFS_MODELS_API_V2
from app.resources.paths import SATURATION_FUNCTION_SET_STR
from app.models.data_schemas.depth_shift_v2.base import MAP_TO_DEPTH_SHIFT_MODELS_API_V2
from app.resources.paths import DEPTH_SHIFT_STR
from app.models.data_schemas.fluid_model_v2.base import MAP_TO_FLUID_MODEL_MODELS_API_V2
from app.resources.paths import FLUID_MODEL_STR

SAMPLES_ANALYSIS = "samplesanalysis"


MAPS_TO_DATA_MODEL = {
    "v2": {
        SAMPLES_ANALYSIS: PATH_TO_DATA_MODEL_VERSIONS_API_V2,
        RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR: MAP_TO_RSRP_MODELS_API_V2,
        SATURATION_FUNCTION_SET_STR: MAP_TO_SFS_MODELS_API_V2,
        DEPTH_SHIFT_STR: MAP_TO_DEPTH_SHIFT_MODELS_API_V2,
        FLUID_MODEL_STR: MAP_TO_FLUID_MODEL_MODELS_API_V2
    },
    "dev": {
        SAMPLES_ANALYSIS: PATH_TO_DATA_MODEL_VERSIONS_API_V2,
    },
}

MULTIPLE_CONTENT_TYPE_PARAMS = {
    "fluid_model_type"
}

ALL_PATHS_TO_DATA_MODEL = PATH_TO_DATA_MODEL_VERSIONS_API_V2

CONTENT_PATTERNS = ("/data/{analysistype}", "{analysistype}")
