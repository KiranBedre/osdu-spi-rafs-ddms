import io
import json
from typing import Any

import pandas as pd
from IPython.display import Markdown, display
from requests import Response

# Constants for output formatting
SEPARATOR_WIDTH = 90


def print_json(json_data: dict, length=None, title=None):
    json_dumped = json.dumps(json_data, indent=4)
    print("*" * SEPARATOR_WIDTH)
    if title:
        print(title.upper())
    print(json_dumped[:length])
    if length and len(json_dumped) > length:
        print("...")
    print("*" * SEPARATOR_WIDTH)


def get_id_from_response(response_dict: dict, position: int = 0) -> str:
    return ":".join(response_dict["recordIdVersions"][position].split(":")[:-1])


def get_dataset_id_from_urn(dataset_urn: str) -> str:
    return ":".join(dataset_urn.split("/")[-1].split(":")[:-1])


def update_datasets(record_dict: dict, dataset_response: Response):
    dataset_id = dataset_response.json()["datasetRegistries"][0]["id"]
    record_dict["data"]["Datasets"].append(f"{dataset_id}:")


def display_json_as_table(json_data: dict, rows_num=10):
    dumped_json = json.dumps(json_data)
    df = pd.read_json(dumped_json, orient="split")

    display(df[:rows_num])


def load_wpc_payload(path: str, conf: dict) -> dict:
    with open(path, "r") as fp:
        wpc_payload = json.load(fp)
    wpc_payload_str = json.dumps(wpc_payload)

    for conf_k, conf_v in conf.items():
        wpc_payload_str = wpc_payload_str.replace(f"{{{conf_k}}}", conf_v)

    return json.loads(wpc_payload_str)


def display_parquet(path: str):
    pd.set_option("display.width", None)
    pd.set_option("display.max_colwidth", None)
    df = pd.read_parquet(path)
    display(df)


def update_parquet(path: str, row_index: int, column_name: str, new_value: Any):
    df = pd.read_parquet(path)
    df.at[row_index, column_name] = new_value
    df.to_parquet(path, index=False)
    display(Markdown("**Updated parquet:**"))
    display_parquet(path)


def get_parquet_cell_value(path: str, row_index: int, column_name) -> Any:
    df = pd.read_parquet(path)
    return df.at[row_index, column_name]


def get_parquet_as_binary(path: str) -> bytes:
    df = pd.read_parquet(path)
    return df.to_parquet(index=False)


def get_parquet_from_json(path: str):
    df = pd.read_json(path, orient="split")
    return df.to_parquet(index=False)


def build_parquet_from_json(json_path: str, parquet_path, data_partition_id="opendes"):
    with open(json_path) as fp:
        data_str = fp.read().replace("{data_partition_id}", data_partition_id)
    df = pd.read_json(io.StringIO(data_str), orient="split")
    df.to_parquet(parquet_path, index=False)
    display(Markdown("**Created parquet:**"))
    display_parquet(parquet_path)
