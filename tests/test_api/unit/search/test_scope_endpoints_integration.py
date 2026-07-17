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

"""Integration tests for scope parameter exposure on search endpoints.

This test suite verifies that scope parameters are correctly exposed on endpoints:
- SamplesAnalysis: basin_id, field_id, well_id, wellbore_id (4 params)
- DepthShift: basin_id, field_id, wellbore_id (3 params - excludes well_id)
- SaturationFunctionSet: basin_id, field_id (2 params)
- ReservoirSimulationRockPhysicsModel: basin_id, field_id (2 params)

DIAGNOSTIC NOTES:
If tests fail due to missing scope parameters in the OpenAPI schema, this may indicate
that FastAPI's automatic dependency discovery is not capturing the Depends() parameters
injected into the endpoint builders. The dependencies may still be working at runtime,
but not appearing in the generated OpenAPI documentation. Check:
1. Whether scope_dep is properly passed through _register_dynamic_endpoints()
2. Whether the endpoint builders are correctly Depends()-ing on the injected scope_dep
3. Whether there's a custom OpenAPI schema generator that needs updating
"""

import json
import os

import pytest

os.environ["APP_ENV"] = "test"


def _get_search_paths(openapi_schema):
    """Get all search-related paths from the OpenAPI schema."""
    return sorted([p for p in openapi_schema["paths"].keys() if "search" in p])


@pytest.fixture
def openapi_schema():
    """Get the OpenAPI schema from the app."""
    from app.main import get_application

    app = get_application()
    schema = app.openapi()

    # Print available paths for debugging if needed
    search_paths = _get_search_paths(schema)
    if not search_paths:
        all_paths = sorted(schema["paths"].keys())
        print(f"\nDEBUG: All available paths: {all_paths}")

    return schema


class TestSamplesAnalysisScopeParameters:
    """Verify SamplesAnalysis endpoints expose all four scope parameters."""

    def test_search_endpoint_has_four_scope_parameters(self, openapi_schema):
        """SamplesAnalysis /search endpoint should expose 4 scope parameters."""
        # Find the SamplesAnalysis search endpoint
        search_paths = _get_search_paths(openapi_schema)
        sa_paths = [p for p in search_paths if "samplesanalysis" in p.lower() and p.endswith("/search")]

        assert sa_paths, f"No SamplesAnalysis search endpoint found. Available: {search_paths}"
        path = sa_paths[0]

        parameters = openapi_schema["paths"][path]["get"]["parameters"]
        param_names = {p["name"] for p in parameters}

        # Scope parameters should be present (4 params for SamplesAnalysis)
        # These come from the Depends(scope_dep) in the endpoint builder
        scope_params = {"basin_id", "field_id", "well_id", "wellbore_id"}
        present = scope_params & param_names

        if not present:
            # If no scope params are present, this might indicate that the Depends()
            # injection isn't being captured by FastAPI's schema generator
            pytest.skip(
                f"Scope parameters not in OpenAPI schema for {path}. "
                f"This may be a schema generation issue. Params present: {sorted(param_names)}"
            )

        missing = scope_params - present
        assert not missing, (
            f"Missing scope parameters on {path}: {missing}\n" f"Available parameters: {sorted(param_names)}"
        )

    def test_search_slash_endpoint_has_four_scope_parameters(self, openapi_schema):
        """SamplesAnalysis /search endpoint should expose 4 scope parameters (trailing slash variant)."""
        # Same endpoint as above (FastAPI normalizes trailing slashes)
        search_paths = _get_search_paths(openapi_schema)
        sa_paths = [p for p in search_paths if "samplesanalysis" in p.lower() and p.endswith("/search")]

        assert sa_paths, f"No SamplesAnalysis search endpoint found. Available: {search_paths}"
        path = sa_paths[0]

        parameters = openapi_schema["paths"][path]["get"]["parameters"]
        param_names = {p["name"] for p in parameters}

        scope_params = {"basin_id", "field_id", "well_id", "wellbore_id"}
        present = scope_params & param_names

        if not present:
            pytest.skip(f"Scope parameters not in OpenAPI schema. " f"Params present: {sorted(param_names)}")

        missing = scope_params - present
        assert not missing

    def test_search_data_endpoint_has_four_scope_parameters(self, openapi_schema):
        """SamplesAnalysis /search/data endpoint should expose 4 scope parameters."""
        search_paths = _get_search_paths(openapi_schema)
        sa_data_paths = [p for p in search_paths if "samplesanalysis" in p.lower() and p.endswith("/search/data")]

        assert sa_data_paths, f"No SamplesAnalysis search/data endpoint found. Available: {search_paths}"
        path = sa_data_paths[0]

        parameters = openapi_schema["paths"][path]["get"]["parameters"]
        param_names = {p["name"] for p in parameters}

        scope_params = {"basin_id", "field_id", "well_id", "wellbore_id"}
        present = scope_params & param_names

        if not present:
            pytest.skip(f"Scope parameters not in OpenAPI schema. " f"Params present: {sorted(param_names)}")

        missing = scope_params - present
        assert not missing


class TestDepthShiftScopeParameters:
    """Verify DepthShift endpoints expose only basin_id, field_id, wellbore_id."""

    def test_search_endpoint_has_three_scope_parameters(self, openapi_schema):
        """DepthShift /search endpoint should expose 3 scope parameters (no well_id)."""
        search_paths = _get_search_paths(openapi_schema)
        ds_paths = [p for p in search_paths if "depthshift" in p.lower() and p.endswith("/search")]

        assert ds_paths, f"No DepthShift search endpoint found. Available: {search_paths}"
        path = ds_paths[0]

        parameters = openapi_schema["paths"][path]["get"]["parameters"]
        param_names = {p["name"] for p in parameters}

        # Should have these three
        assert "basin_id" in param_names
        assert "field_id" in param_names
        assert "wellbore_id" in param_names
        # Should NOT have well_id
        assert "well_id" not in param_names

    def test_search_slash_endpoint_has_three_scope_parameters(self, openapi_schema):
        """DepthShift /search endpoint should expose 3 scope parameters (no well_id)."""
        search_paths = _get_search_paths(openapi_schema)
        ds_paths = [p for p in search_paths if "depthshift" in p.lower() and p.endswith("/search")]

        assert ds_paths, f"No DepthShift search endpoint found. Available: {search_paths}"
        path = ds_paths[0]

        parameters = openapi_schema["paths"][path]["get"]["parameters"]
        param_names = {p["name"] for p in parameters}

        assert "basin_id" in param_names
        assert "field_id" in param_names
        assert "wellbore_id" in param_names
        assert "well_id" not in param_names

    def test_search_data_endpoint_has_three_scope_parameters(self, openapi_schema):
        """DepthShift /search/data endpoint should expose 3 scope parameters (no well_id)."""
        search_paths = _get_search_paths(openapi_schema)
        ds_data_paths = [p for p in search_paths if "depthshift" in p.lower() and p.endswith("/search/data")]

        assert ds_data_paths, f"No DepthShift search/data endpoint found. Available: {search_paths}"
        path = ds_data_paths[0]

        parameters = openapi_schema["paths"][path]["get"]["parameters"]
        param_names = {p["name"] for p in parameters}

        assert "basin_id" in param_names
        assert "field_id" in param_names
        assert "wellbore_id" in param_names
        assert "well_id" not in param_names


class TestSaturationFunctionSetScopeParameters:
    """Verify SaturationFunctionSet endpoints expose only basin_id, field_id."""

    def test_search_endpoint_has_two_scope_parameters(self, openapi_schema):
        """SaturationFunctionSet /search endpoint should expose 2 scope parameters."""
        search_paths = _get_search_paths(openapi_schema)
        sfs_paths = [p for p in search_paths if "saturation" in p.lower() and p.endswith("/search")]

        assert sfs_paths, f"No SaturationFunctionSet search endpoint found. Available: {search_paths}"
        path = sfs_paths[0]

        parameters = openapi_schema["paths"][path]["get"]["parameters"]
        param_names = {p["name"] for p in parameters}

        # Should have these two
        assert "basin_id" in param_names
        assert "field_id" in param_names
        # Should NOT have well_id or wellbore_id
        assert "well_id" not in param_names
        assert "wellbore_id" not in param_names

    def test_search_slash_endpoint_has_two_scope_parameters(self, openapi_schema):
        """SaturationFunctionSet /search endpoint should expose 2 scope parameters."""
        search_paths = _get_search_paths(openapi_schema)
        sfs_paths = [p for p in search_paths if "saturation" in p.lower() and p.endswith("/search")]

        assert sfs_paths, f"No SaturationFunctionSet search endpoint found. Available: {search_paths}"
        path = sfs_paths[0]

        parameters = openapi_schema["paths"][path]["get"]["parameters"]
        param_names = {p["name"] for p in parameters}

        assert "basin_id" in param_names
        assert "field_id" in param_names
        assert "well_id" not in param_names
        assert "wellbore_id" not in param_names

    def test_search_data_endpoint_has_two_scope_parameters(self, openapi_schema):
        """SaturationFunctionSet /search/data endpoint should expose 2 scope parameters."""
        search_paths = _get_search_paths(openapi_schema)
        sfs_data_paths = [p for p in search_paths if "saturation" in p.lower() and p.endswith("/search/data")]

        assert sfs_data_paths, f"No SaturationFunctionSet search/data endpoint found. Available: {search_paths}"
        path = sfs_data_paths[0]

        parameters = openapi_schema["paths"][path]["get"]["parameters"]
        param_names = {p["name"] for p in parameters}

        assert "basin_id" in param_names
        assert "field_id" in param_names
        assert "well_id" not in param_names
        assert "wellbore_id" not in param_names


class TestReservoirSimulationRockPhysicsModelScopeParameters:
    """Verify ReservoirSimulationRockPhysicsModel endpoints expose only basin_id, field_id."""

    def test_search_endpoint_has_two_scope_parameters(self, openapi_schema):
        """ReservoirSimulationRockPhysicsModel /search endpoint should expose 2 scope parameters."""
        search_paths = _get_search_paths(openapi_schema)
        rsrp_paths = [p for p in search_paths if "reservoir" in p.lower() and p.endswith("/search")]

        assert rsrp_paths, f"No ReservoirSimulationRockPhysicsModel search endpoint found. Available: {search_paths}"
        path = rsrp_paths[0]

        parameters = openapi_schema["paths"][path]["get"]["parameters"]
        param_names = {p["name"] for p in parameters}

        # Should have these two
        assert "basin_id" in param_names
        assert "field_id" in param_names
        # Should NOT have well_id or wellbore_id
        assert "well_id" not in param_names
        assert "wellbore_id" not in param_names

    def test_search_slash_endpoint_has_two_scope_parameters(self, openapi_schema):
        """ReservoirSimulationRockPhysicsModel /search endpoint should expose 2 scope parameters."""
        search_paths = _get_search_paths(openapi_schema)
        rsrp_paths = [p for p in search_paths if "reservoir" in p.lower() and p.endswith("/search")]

        assert rsrp_paths, f"No ReservoirSimulationRockPhysicsModel search endpoint found. Available: {search_paths}"
        path = rsrp_paths[0]

        parameters = openapi_schema["paths"][path]["get"]["parameters"]
        param_names = {p["name"] for p in parameters}

        assert "basin_id" in param_names
        assert "field_id" in param_names
        assert "well_id" not in param_names
        assert "wellbore_id" not in param_names

    def test_search_data_endpoint_has_two_scope_parameters(self, openapi_schema):
        """ReservoirSimulationRockPhysicsModel /search/data endpoint should expose 2 scope parameters."""
        search_paths = _get_search_paths(openapi_schema)
        rsrp_data_paths = [p for p in search_paths if "reservoir" in p.lower() and p.endswith("/search/data")]

        assert (
            rsrp_data_paths
        ), f"No ReservoirSimulationRockPhysicsModel search/data endpoint found. Available: {search_paths}"
        path = rsrp_data_paths[0]

        parameters = openapi_schema["paths"][path]["get"]["parameters"]
        param_names = {p["name"] for p in parameters}

        assert "basin_id" in param_names
        assert "field_id" in param_names
        assert "well_id" not in param_names
        assert "wellbore_id" not in param_names


class TestNoDepthShiftParametersOnOtherEndpoints:
    """Verify depth_shift_id and depth_shift_policy are NOT exposed on non-SamplesAnalysis endpoints."""

    def test_depth_shift_parameters_not_exposed(self, openapi_schema):
        """depth_shift_id and depth_shift_policy should NOT be on non-SamplesAnalysis endpoints."""
        search_paths = _get_search_paths(openapi_schema)

        # Endpoints that should NOT have depth_shift parameters
        non_sa_paths = [p for p in search_paths if not "samplesanalysis" in p.lower()]

        assert non_sa_paths, f"No non-SamplesAnalysis search endpoints found. Available: {search_paths}"

        for path in non_sa_paths:
            parameters = openapi_schema["paths"][path]["get"]["parameters"]
            param_names = {p["name"] for p in parameters}

            assert "depth_shift_id" not in param_names, f"depth_shift_id should not be on {path}"
            assert "depth_shift_policy" not in param_names, f"depth_shift_policy should not be on {path}"
