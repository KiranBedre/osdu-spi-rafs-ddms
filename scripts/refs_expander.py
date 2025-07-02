import argparse
import json
import os

import jsonref


def expand_schema(directory_path: str, filename: str):
    base_uri_path = os.path.abspath(directory_path).replace("\\", "/")
    file_path = os.path.abspath(os.path.join(directory_path, filename))
    with open(file_path) as fr:
        exp_schema = jsonref.load(
            fr, base_uri=f"file:///{base_uri_path}/", merge_props=True,
        )

    with open(file_path, "w") as fw:
        json.dump(exp_schema, fw, indent=2)


def process_directory(directory_path):
    for filename in os.listdir(directory_path):
        if filename.endswith("DataSchema.1.0.0.json"):
            expand_schema(directory_path, filename)


if __name__ == "__main__":
    # run as python refs_expander.py Generated/content
    parser = argparse.ArgumentParser(description="Process JSON schema files in a specified directory.")
    parser.add_argument("directory", type=str, help="Path to the directory containing JSON schema files.")
    args = parser.parse_args()

    # Call the function with the provided directory path
    process_directory(args.directory)
