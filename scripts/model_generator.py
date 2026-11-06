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

import argparse
import os
import re
import subprocess
from datetime import date

COPYRIGHT = f"""#  Copyright {date.today().year} ExxonMobil Technology and Engineering Company
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


# Matches a field datamodel-codegen renamed to avoid a field/class name collision,
# e.g. "Conditions_1: Annotated[Conditions | None, Field(\n    alias=\"Conditions\", ...".
# That rename is the tool's own collision signal - no separate detection needed.
# Whitespace around "Annotated[", the type/Field boundary, and inside the alias
# kwarg is deliberately flexible (\s* / ,?\s*) rather than hard-coded newlines:
# black wraps the Field(...) call onto multiple lines with `alias=` on its own
# line when it has several kwargs, but collapses it to one line - or to just
# `Field(alias="X")` with nothing else - when it's short, and both shapes occur
# across real schemas (e.g. Meta fields vs. simple UOM-wrapper fields). The
# lookahead terminator finds the `)` that is actually followed by Annotated's
# closing `]` (rather than the first `)` at all, which could sit inside a
# description string), so it still ends the match at the true Field(...) close
# even when a kwarg value itself contains parentheses.
_COLLISION_FIELD_RE = re.compile(
    r'(?P<name>\w+)_1: Annotated\[\s*'
    r'(?P<type>.+?),\s*'
    r'Field\(\s*alias="(?P=name)",?\s*'
    r'(?P<extra>.*?)'
    r'\)(?=,?\s*\])',
    re.DOTALL,
)


def _fix_field_class_name_collisions(model):
    """Replace datamodel-codegen's field-rename collision fix with a type-alias.

    A field cannot be named identically to a type it references in its own
    annotation (e.g. `Conditions: Conditions | None`): Python binds the field's
    default value to that name before evaluating the annotation, so the
    annotation resolves to the just-bound value instead of the class - this
    happens with plain, ordinary evaluation, `--disable-future-imports` does not
    change it. datamodel-codegen avoids this by renaming the *field*
    (`Conditions_1`, `Field(alias="Conditions")`), but that breaks code in this
    app that assumes a field's Python name matches its wire-format name. Instead,
    alias the *class* (`_ConditionsModel = Conditions`) and point the field's
    annotation at the alias, keeping the field's own name unchanged.
    """
    names = sorted({found.group("name") for found in _COLLISION_FIELD_RE.finditer(model)})

    for name in names:
        class_start = re.search(rf"^class {name}\(RafsBaseModel\):\n", model, re.MULTILINE)
        next_class = re.search(r"\n\nclass ", model[class_start.end():])
        insert_at = class_start.end() + (next_class.start() if next_class else len(model) - class_start.end())
        model = f"{model[:insert_at]}\n\n_{name}Model = {name}\n{model[insert_at:]}"

    def _rewrite_field(match):
        name = match.group("name")
        aliased_type = re.sub(rf"\b{name}\b", f"_{name}Model", match.group("type"))
        extra = match.group("extra").strip()
        if extra.endswith(","):
            extra = extra[:-1].rstrip()
        field_call = f"Field({extra})" if extra else "Field()"
        return f"{name}: Annotated[\n        {aliased_type},\n        {field_call}"

    return _COLLISION_FIELD_RE.sub(_rewrite_field, model)


def _drop_basemodel_from_pydantic_import(model):
    """Remove `BaseModel` from the `from pydantic import ...` line, wherever it sits in the list.

    datamodel-codegen does not always emit `BaseModel` as the first name on that line
    (e.g. `from pydantic import AwareDatetime, BaseModel, ConfigDict, Field`) - a naive
    `.replace("from pydantic import BaseModel,", ...)` only matches when it is first, so it
    silently no-ops otherwise, leaving `BaseModel` to be caught by the later blanket
    `BaseModel` -> `RafsBaseModel` rename *inside the import line itself*, which then tries
    (and fails) to import `RafsBaseModel` from `pydantic`.
    """
    import_line = re.search(r"^from pydantic import (?P<names>.+)$", model, re.MULTILINE)
    if not import_line:
        return model

    names = [name.strip() for name in import_line.group("names").split(",")]
    if "BaseModel" not in names:
        return model

    remaining = [name for name in names if name != "BaseModel"]
    replacement = f"from pydantic import {', '.join(remaining)}" if remaining else ""
    return f"{model[:import_line.start()]}{replacement}{model[import_line.end():]}"


def _build_model_for_rafs(model_path):
    """Finalize configuring the model for Rafs."""

    with open(model_path, "r") as fpr:
        model = fpr.read()
        # Replace pydantic BaseModel with RafsBaseModel
        model = _drop_basemodel_from_pydantic_import(model)
        model = model.replace("BaseModel", "RafsBaseModel")
        # Inject RafsBaseModel import after the pydantic import block
        rafs_import = "from app.models.config import RafsBaseModel"
        if "from pydantic import" in model:
            model = model.replace("from pydantic import", f"{rafs_import}\n\nfrom pydantic import", 1)
        elif "from typing import" in model:
            model = model.replace("from typing import", f"{rafs_import}\n\nfrom typing import", 1)
        else:
            # Neither anchor is present - e.g. the pydantic import line contained only
            # `BaseModel`, which _drop_basemodel_from_pydantic_import removed entirely.
            model = f"{rafs_import}\n\n{model.lstrip()}"
        model = _fix_field_class_name_collisions(model)

    with open(model_path, "w") as fpw:
        fpw.write(f"{COPYRIGHT}{model}")


def run_datamodel_codegen(source_directory: str, target_directory: str, end_filter: str):
    """Run the pydantic data model code generator with source schemas.

    :param source_directory: source directory of json schemas
    :type source_directory: str
    :param target_directory: target directory of pydantic models
    :type target_directory: str
    :param end_filter: a filter check file ending
    :type end_filter: str
    """
    # Iterate over each file in the specified directory
    for filename in os.listdir(source_directory):

        # Assumes `analysis_type.major.minor.patch.json` naming convention
        if not re.match(r"^[a-z_]+(?:\.[0-9]+\.[0-9]+\.[0-9]+)?\.json$", filename):  # noqa: W605
            continue

        if filename.endswith(end_filter):
            # Extract the schema name to build model name
            schema_name, major, minor, patch, *_ = filename.split(".")
            py_model_name = f"{schema_name}_data_model_{major}_{minor}_{patch}.py"

            # Define the input and output paths
            input_path = os.path.join(source_directory, filename)
            output_path = os.path.join(target_directory, py_model_name)

            # define the content model class name
            schema_name = "".join([name.capitalize() for name in schema_name.split("_")])
            model_class_name = f"{schema_name}Model{major}{minor}{patch}"

            # Construct the command
            command = [  # noqa: WPS317
                "datamodel-codegen",
                "--input",
                input_path,
                "--input-file-type",
                "jsonschema",
                "--output",
                output_path,
                "--class-name",
                model_class_name,
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--use-annotated",
                "--disable-future-imports",
                "--use-double-quotes",
                "--formatters",
                "black",
                "isort",
            ]

            # Print the command (for debugging purposes)
            command_str = " ".join(command)
            print(f"Running command: {command_str}")

            # Execute the command
            subprocess.run(command, check=True)

            # add copyright and rafs base model
            _build_model_for_rafs(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process JSON schema files in a specified directory.")
    parser.add_argument("source_directory", type=str, help="Path to the directory containing JSON schema files.")
    parser.add_argument("target_directory", type=str, help="Pydantic models directory")
    parser.add_argument("end_filter", type=str, default="1.0.0.json")
    args = parser.parse_args()

    run_datamodel_codegen(args.source_directory, args.target_directory, args.end_filter)
