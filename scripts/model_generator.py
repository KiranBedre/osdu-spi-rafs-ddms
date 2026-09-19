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


def _build_model_for_rafs(model_path):
    """Finalize configuring the model for Rafs."""

    with open(model_path, "r") as fpr:
        model = fpr.read()
        # Replace pydantic BaseModel with RafsBaseModel
        model = model.replace("from pydantic import BaseModel,", "from pydantic import")
        model = model.replace("BaseModel", "RafsBaseModel")
        # Inject RafsBaseModel import after the pydantic import block
        rafs_import = "from app.models.config import RafsBaseModel"
        model = model.replace("from pydantic import", f"{rafs_import}\n\nfrom pydantic import", 1)

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
