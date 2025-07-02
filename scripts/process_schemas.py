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
import json
import os
import re


def transform_filename(filename: str) -> str:
    """Transform from AnalysisTypeDataSchema.1.0.0.json to
    analysis_type.1.0.0.json."""

    match = re.match(r"([A-Za-z]+)DataSchema(\.\d+\.\d+\.\d+\.json)", filename)
    if not match:
        return filename  # Return as is if the pattern does not match

    prefix, version_ext = match.groups()
    snake_case_prefix = re.sub(r"([a-z])([A-Z])", r"\1_\2", prefix).lower()

    return f"{snake_case_prefix}{version_ext}"


def update_id(schema, filename):
    schema["$id"] = filename
    try:
        del schema["x-osdu-schema-source"]
        del schema["x-osdu-inheriting-from-kind"]
    except KeyError:
        pass


def update_additional_properties(properties):
    """Set additionalProperties to False."""

    for _, value in properties.items():
        if isinstance(value, dict):
            # Recursively process nested properties
            if "properties" in value:
                update_additional_properties(value["properties"])
                if not "additionalProperties" in value:
                    value["additionalProperties"] = False

            # Handle arrays of objects
            elif value.get("type") == "array" and "items" in value:
                items = value["items"]
                if isinstance(items, dict):
                    if "properties" in items:
                        update_additional_properties(items["properties"])
                        if not "additionalProperties" in items:
                            items["additionalProperties"] = False
                elif isinstance(items, list):
                    for elem in items:
                        if "properties" in elem:
                            update_additional_properties(elem["properties"])
                        if not "additionalProperties" in elem:
                            elem["additionalProperties"] = False

                    # If there’s only one type of item, simplify the array
                    if len(items) == 1:
                        value["items"] = items[0]

        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and "properties" in item:
                    update_additional_properties(item["properties"])


def process_schema_file(directory_path, old_filename, new_filename):
    """Process the schema with the updates."""

    old_filepath = os.path.join(directory_path, old_filename)
    new_filepath = os.path.join(directory_path, new_filename)

    with open(old_filepath, "r") as file:
        schema = json.load(file)

    # Update the properties in the schema
    if "properties" in schema:
        update_additional_properties(schema["properties"])
        if not "additionalProperties" in schema:
            schema["additionalProperties"] = False

    update_id(schema, new_filename)

    # Write the updated schema back to the new file and delete old one
    os.remove(old_filepath)
    with open(new_filepath, "w", encoding="utf-8") as file:
        json.dump(schema, file, indent=2, ensure_ascii=False)


def process_directory(directory_path: str, end_filter: str = "DataSchema.1.0.0.json"):
    for filename in os.listdir(directory_path):
        if filename.endswith(end_filter):
            new_filename = transform_filename(filename)
            if filename != new_filename:
                process_schema_file(directory_path, filename, new_filename)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process JSON schema files in a specified directory.")
    parser.add_argument("directory", type=str, help="Path to the directory containing JSON schema files.")
    parser.add_argument("end_filter", type=str, help="End of file filter", default="DataSchema.1.0.0.json")
    args = parser.parse_args()

    # Call the function with the provided directory path
    process_directory(args.directory, args.end_filter)
