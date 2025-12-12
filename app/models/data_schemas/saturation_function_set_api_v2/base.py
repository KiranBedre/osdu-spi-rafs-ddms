from app.models.data_schemas.version import ContentSchemaVersion
from app.models.data_schemas.saturation_function_set_api_v2.saturation_function_set_data_model_1_0_0 import SaturationFunctionSetModel100
from app.resources.paths import SATURATION_FUNCTION_SET_STR

SATURATION_FUNCTION_SET_MODELS = {
    ContentSchemaVersion.V_1_0_0: SaturationFunctionSetModel100,
}

MAP_TO_SFS_MODELS_API_V2 = {
    SATURATION_FUNCTION_SET_STR: SATURATION_FUNCTION_SET_MODELS
}
