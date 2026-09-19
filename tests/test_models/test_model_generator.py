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
Tests for scripts/model_generator.py.

Coverage:
  1. _build_model_for_rafs — post-processing transforms applied to codegen output.
  2. run_datamodel_codegen — file-filter logic and subprocess invocation (mocked).
"""

import textwrap
from pathlib import Path
from unittest.mock import call, patch

import pytest

from scripts.model_generator import _build_model_for_rafs, run_datamodel_codegen

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Simulates what `datamodel-codegen --output-model-type pydantic_v2.BaseModel
# --use-annotated --disable-future-imports` produces before post-processing.
_CODEGEN_V2_OUTPUT = textwrap.dedent("""\
    from typing import Annotated, Optional
    from pydantic import BaseModel, Field, StringConstraints


    class RelativePermeabilityModel110(BaseModel):
        SamplesAnalysisID: Annotated[str, StringConstraints(pattern=r"^[\\w]+:work-product-component--SamplesAnalysis:[\\w]+:[0-9]*$")] = Field(
            ..., description="OSDU Identifier.", title="Samples Analysis ID"
        )
        Name: str | None = Field(None, description="The name.", title="Name")
    """)

# Same content but BaseModel is the only pydantic import (edge case).
_CODEGEN_V2_OUTPUT_BASEMODEL_ONLY = textwrap.dedent("""\
    from pydantic import BaseModel


    class SimpleModel100(BaseModel):
        pass
    """)

# Simulates the bad v1-codegen output that must never reach the codebase.
_CODEGEN_V1_OUTPUT = textwrap.dedent("""\
    from __future__ import annotations
    from typing import Optional
    from pydantic import BaseModel, Field
    from pydantic import constr


    class OldModel100(BaseModel):
        Code: Optional[constr(regex=r"^[\\w]+$")] = Field(None, const=True)
    """)


@pytest.fixture()
def codegen_output_file(tmp_path):
    """Write standard v2 codegen output to a temp file and return its path."""
    out = tmp_path / "relative_permeability_data_model_1_1_0.py"
    out.write_text(_CODEGEN_V2_OUTPUT)
    return out


@pytest.fixture()
def codegen_output_file_basemodel_only(tmp_path):
    """Write edge-case codegen output (BaseModel only import) to a temp file."""
    out = tmp_path / "simple_data_model_1_0_0.py"
    out.write_text(_CODEGEN_V2_OUTPUT_BASEMODEL_ONLY)
    return out


# ---------------------------------------------------------------------------
# 1. _build_model_for_rafs post-processing
# ---------------------------------------------------------------------------


class TestBuildModelForRafs:

    def test_rafs_base_model_import_injected(self, codegen_output_file):
        _build_model_for_rafs(codegen_output_file)
        result = codegen_output_file.read_text()
        assert "from app.models.config import RafsBaseModel" in result

    def test_base_class_replaced_with_rafs_base_model(self, codegen_output_file):
        _build_model_for_rafs(codegen_output_file)
        result = codegen_output_file.read_text()
        assert "class RelativePermeabilityModel110(RafsBaseModel):" in result

    def test_pydantic_basemodel_not_in_output(self, codegen_output_file):
        _build_model_for_rafs(codegen_output_file)
        result = codegen_output_file.read_text()
        # "BaseModel" should only remain as part of "RafsBaseModel"
        assert "from pydantic import BaseModel" not in result
        assert "(BaseModel)" not in result

    def test_rafs_import_precedes_pydantic_import(self, codegen_output_file):
        _build_model_for_rafs(codegen_output_file)
        result = codegen_output_file.read_text()
        rafs_pos = result.index("from app.models.config import RafsBaseModel")
        pydantic_pos = result.index("from pydantic import")
        assert rafs_pos < pydantic_pos

    def test_copyright_header_prepended(self, codegen_output_file):
        _build_model_for_rafs(codegen_output_file)
        result = codegen_output_file.read_text()
        assert result.startswith("#  Copyright")
        assert "ExxonMobil Technology and Engineering Company" in result
        assert "Apache License, Version 2.0" in result

    def test_no_future_annotations_import(self, codegen_output_file):
        _build_model_for_rafs(codegen_output_file)
        result = codegen_output_file.read_text()
        assert "from __future__ import annotations" not in result

    def test_stringconstraints_preserved(self, codegen_output_file):
        _build_model_for_rafs(codegen_output_file)
        result = codegen_output_file.read_text()
        assert "StringConstraints" in result

    def test_basemodel_only_import_edge_case(self, codegen_output_file_basemodel_only):
        """When BaseModel is not followed by a comma, the transform still works."""
        _build_model_for_rafs(codegen_output_file_basemodel_only)
        result = codegen_output_file_basemodel_only.read_text()
        assert "from app.models.config import RafsBaseModel" in result
        assert "class SimpleModel100(RafsBaseModel):" in result


class TestBuildModelV1PatternsAbsent:
    """Confirm that a v1 codegen file run through _build_model_for_rafs still
    carries v1 patterns — i.e. the post-processor does NOT silently fix them.
    This documents the contract: the caller (run_datamodel_codegen) must use
    the right codegen flags so the raw output is already v2-clean."""

    def test_v1_constr_not_stripped(self, tmp_path):
        v1_file = tmp_path / "old_data_model_1_0_0.py"
        v1_file.write_text(_CODEGEN_V1_OUTPUT)
        _build_model_for_rafs(v1_file)
        result = v1_file.read_text()
        # post-processor does not remove these — the codegen flags must prevent them
        assert "constr(" in result
        assert "const=True" in result


# ---------------------------------------------------------------------------
# 2. run_datamodel_codegen file-filter and subprocess flags
# ---------------------------------------------------------------------------


class TestRunDatamodelCodegen:

    def _make_source(self, source_dir: Path, filename: str) -> Path:
        schema = source_dir / filename
        schema.write_text('{"title": "Test", "type": "object", "properties": {}}')
        return schema

    def test_matching_file_invokes_subprocess(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        dst = tmp_path / "dst"
        dst.mkdir()
        self._make_source(src, "my_type.1.0.0.json")

        with patch("scripts.model_generator.subprocess.run") as mock_run:
            mock_run.side_effect = lambda cmd, **_: (dst / "my_type_data_model_1_0_0.py").write_text(_CODEGEN_V2_OUTPUT)
            run_datamodel_codegen(str(src), str(dst), "1.0.0.json")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "datamodel-codegen" in cmd
        assert "--output-model-type" in cmd
        assert "pydantic_v2.BaseModel" in cmd
        assert "--use-annotated" in cmd
        assert "--disable-future-imports" in cmd

    def test_non_matching_file_skipped(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        dst = tmp_path / "dst"
        dst.mkdir()
        self._make_source(src, "my_type.1.0.0.json")

        with patch("scripts.model_generator.subprocess.run") as mock_run:
            run_datamodel_codegen(str(src), str(dst), "2.0.0.json")

        mock_run.assert_not_called()

    def test_non_schema_filename_skipped(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        dst = tmp_path / "dst"
        dst.mkdir()
        (src / "README.json").write_text("{}")
        (src / "SOME_FILE.1.0.0.json").write_text("{}")  # uppercase — no match

        with patch("scripts.model_generator.subprocess.run") as mock_run:
            run_datamodel_codegen(str(src), str(dst), "1.0.0.json")

        mock_run.assert_not_called()

    def test_output_file_post_processed_after_codegen(self, tmp_path):
        """Full pipeline: codegen writes v2 output → _build_model_for_rafs transforms it."""
        src = tmp_path / "src"
        src.mkdir()
        dst = tmp_path / "dst"
        dst.mkdir()
        self._make_source(src, "my_type.1.0.0.json")
        output_path = dst / "my_type_data_model_1_0_0.py"

        with patch("scripts.model_generator.subprocess.run") as mock_run:
            mock_run.side_effect = lambda cmd, **_: output_path.write_text(_CODEGEN_V2_OUTPUT)
            run_datamodel_codegen(str(src), str(dst), "1.0.0.json")

        result = output_path.read_text()
        assert "from app.models.config import RafsBaseModel" in result
        assert "(RafsBaseModel)" in result
        assert "from pydantic import BaseModel" not in result
        assert "from __future__ import annotations" not in result

    def test_multiple_files_only_matching_version_processed(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        dst = tmp_path / "dst"
        dst.mkdir()
        self._make_source(src, "type_a.1.0.0.json")
        self._make_source(src, "type_b.1.1.0.json")
        self._make_source(src, "type_c.2.0.0.json")

        calls_seen = []

        def fake_run(cmd, **_):  # noqa: WPS430
            output = Path(cmd[cmd.index("--output") + 1])
            output.write_text(_CODEGEN_V2_OUTPUT)
            calls_seen.append(output.name)

        with patch("scripts.model_generator.subprocess.run", side_effect=fake_run):
            run_datamodel_codegen(str(src), str(dst), "1.0.0.json")

        assert calls_seen == ["type_a_data_model_1_0_0.py"]

    def test_class_name_derived_from_filename(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        dst = tmp_path / "dst"
        dst.mkdir()
        self._make_source(src, "relative_permeability.1.1.0.json")

        with patch("scripts.model_generator.subprocess.run") as mock_run:
            mock_run.side_effect = lambda cmd, **_: (dst / "relative_permeability_data_model_1_1_0.py").write_text(
                _CODEGEN_V2_OUTPUT
            )
            run_datamodel_codegen(str(src), str(dst), "1.1.0.json")

        cmd = mock_run.call_args[0][0]
        class_name_idx = cmd.index("--class-name") + 1
        assert cmd[class_name_idx] == "RelativePermeabilityModel110"
