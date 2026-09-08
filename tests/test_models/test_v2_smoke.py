#  Copyright 2026 ExxonMobil Technology and Engineering Company
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
"""
Pydantic v2 model smoke tests.

Three layers of coverage:
  1. Import — every *_data_model_*.py must load without error.
  2. Instantiation — every class registered in base.py must accept
     a minimal valid payload.
  3. Constraint — SamplesAnalysisID pattern must reject garbage input.

These tests catch v1-codegen patterns (const=, constr(regex=), Extra)
that silently survive linting but explode at import or instantiation time.
"""

import importlib
import pathlib

import pytest
from pydantic import ValidationError

import app.models.data_schemas.sample_analysis_api_v2.base as _sar_base

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent

_MODEL_DIRS = [
    _PROJECT_ROOT / "app/models/data_schemas/sample_analysis_api_v2",
    _PROJECT_ROOT / "app/models/data_schemas/depth_shift_v2",
]

_VALID_SAR_ID = "opendes:work-product-component--SamplesAnalysis:smoke-test:1"
_VALID_SAMPLE_ID = "opendes:master-data--Sample:smoke-test:1"
# Minimal Meta entry: only `kind` is needed; everything else is optional.
_VALID_META = [{"kind": "Unit"}]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _module_params():
    """Yield pytest params for every *_data_model_*.py in the model dirs."""
    for d in _MODEL_DIRS:
        for path in sorted(d.glob("*_data_model_*.py")):
            rel = path.relative_to(_PROJECT_ROOT)
            mod_name = ".".join(rel.parts).removesuffix(".py")
            yield pytest.param(mod_name, id=path.stem)


def _registered_model_params():
    """Yield pytest params for every class in the SAR base registry."""
    for attr in sorted(dir(_sar_base)):
        obj = getattr(_sar_base, attr)
        if not (isinstance(obj, dict) and attr.endswith("_MODELS")):
            continue
        for _ver, cls in obj.items():
            yield pytest.param(cls, id=cls.__name__)


def _minimal_payload(cls) -> dict:
    """Build the smallest payload that satisfies a model's required fields."""
    required = {name for name, fi in cls.model_fields.items() if fi.is_required()}
    payload: dict = {}
    if "SamplesAnalysisID" in required:
        payload["SamplesAnalysisID"] = _VALID_SAR_ID
    if "SampleID" in required:
        payload["SampleID"] = _VALID_SAMPLE_ID
    if "Meta" in required:
        payload["Meta"] = _VALID_META
    if "SampleMass" in required:
        payload["SampleMass"] = 1.0
    return payload


# ---------------------------------------------------------------------------
# 1. Import smoke tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("module_name", list(_module_params()))
def test_model_module_imports_cleanly(module_name):
    """Every model module must import without raising under Pydantic v2.

    Catches v1 codegen patterns (const=, constr(regex=), Extra) that
    survive static analysis but blow up at import time.
    """
    importlib.import_module(module_name)


# ---------------------------------------------------------------------------
# 2. Instantiation smoke tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("model_cls", list(_registered_model_params()))
def test_registered_model_instantiates(model_cls):
    """Every class registered in base.py must accept a minimal valid payload."""
    payload = _minimal_payload(model_cls)
    instance = model_cls(**payload)
    assert instance is not None


# ---------------------------------------------------------------------------
# 3. Constraint validation tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("model_cls", list(_registered_model_params()))
def test_model_rejects_invalid_sar_id(model_cls):
    """SamplesAnalysisID must enforce its regex pattern constraint."""
    required = {name for name, fi in model_cls.model_fields.items() if fi.is_required()}
    if "SamplesAnalysisID" not in required:
        pytest.skip("model has no required SamplesAnalysisID")

    payload = _minimal_payload(model_cls)
    payload["SamplesAnalysisID"] = "not-a-valid-id"
    with pytest.raises(ValidationError):
        model_cls(**payload)
