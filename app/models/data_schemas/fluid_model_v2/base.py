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

from app.models.data_schemas.version import ContentSchemaVersion
from app.models.data_schemas.fluid_model_v2.black_oil_fluid_model_data_model_1_0_0 import BlackOilFluidModelModel100
from app.models.data_schemas.fluid_model_v2.compositional_fluid_model_data_model_1_0_0 import CompositionalFluidModelModel100
from app.models.data_schemas.fluid_model_v2.thermal_compositional_fluid_model_data_model_1_0_0 import ThermalCompositionalFluidModelModel100
from app.resources.paths import FluidModelRelativePathsV2

BLACK_OIL_FLUID_MODEL_MODELS = {
    ContentSchemaVersion.V_1_0_0: BlackOilFluidModelModel100,
}

COMPOSITIONAL_FLUID_MODEL_MODELS = {
    ContentSchemaVersion.V_1_0_0: CompositionalFluidModelModel100,
}

THERMAL_COMPOSITIONAL_FLUID_MODEL_MODELS = {
    ContentSchemaVersion.V_1_0_0: ThermalCompositionalFluidModelModel100,
}

fluid_model_paths_api_v2 = FluidModelRelativePathsV2()
MAP_TO_FLUID_MODEL_MODELS_API_V2 = {
    fluid_model_paths_api_v2.BLACK_OIL_FLUID_MODEL: BLACK_OIL_FLUID_MODEL_MODELS,
    fluid_model_paths_api_v2.COMPOSITIONAL_FLUID_MODEL: COMPOSITIONAL_FLUID_MODEL_MODELS,
    fluid_model_paths_api_v2.THERMAL_COMPOSITIONAL_FLUID_MODEL: THERMAL_COMPOSITIONAL_FLUID_MODEL_MODELS
}
