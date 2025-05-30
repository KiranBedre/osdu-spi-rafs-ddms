#  Copyright 2023 ExxonMobil Technology and Engineering Company
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

import json
import os
from dataclasses import dataclass
from typing import Optional

from tests.integration.config import (
    CONFIG,
    DATA_DIR,
    SCHEMA_VERSION,
    TEST_DATA_STORE,
    SamplesAnalysisTypes,
)
from tests.integration.helpers import CommonHelper


@dataclass
class RecordValues(object):
    data_partition_id: str
    schema_authority: str
    custom_schema_authority: str
    acl_viewers: str
    acl_owners: str


azure_values = RecordValues(
    data_partition_id="opendes",
    schema_authority="osdu",
    custom_schema_authority="rafsddms",
    acl_viewers="data.default.viewers@opendes.contoso.com",
    acl_owners="data.default.owners@opendes.contoso.com",
)

aws_values = RecordValues(
    data_partition_id="opendes",
    schema_authority="osdu",
    custom_schema_authority="rafsddms",
    acl_viewers="data.default.viewers@opendes.example.com",
    acl_owners="data.default.owners@opendes.example.com",
)

def create_gc_values(data_partition_id: str) -> RecordValues:
    return RecordValues(
        data_partition_id=data_partition_id,
        schema_authority="osdu",
        custom_schema_authority="rafsddms",
        acl_viewers=f"data.default.viewers@{data_partition_id}.group",
        acl_owners=f"data.default.owners@{data_partition_id}.group"
    )


def load_test_data(file_name: str, analysis_type: Optional[SamplesAnalysisTypes] = None) -> dict:
    data_values = None
    if CONFIG["CLOUD_PROVIDER"] == "azure":
        data_values = azure_values
    elif CONFIG["CLOUD_PROVIDER"] == "aws":
        data_values = aws_values
    elif CONFIG["CLOUD_PROVIDER"] == "gc":
        data_values = create_gc_values(CONFIG["DATA_PARTITION"])
    with open(os.path.join(DATA_DIR, file_name)) as json_file:
        data_str = (
            json_file.read(
            ).replace(
                "{record_id}", f"{CommonHelper.generate_random_record_id()}",
            ).replace(
                "{sar_v2_record_id}", TEST_DATA_STORE.get("sar_v2_record_id", ""),
            ).replace(
                "{schema_version}", SCHEMA_VERSION,
            ).replace(
                "{data_partition_id}", data_values.data_partition_id,
            ).replace(
                "{schema_authority}", data_values.schema_authority,
            ).replace(
                "{custom_schema_authority}", data_values.custom_schema_authority,
            ).replace(
                "{acl_viewers}", data_values.acl_viewers,
            ).replace(
                "{acl_owners}", data_values.acl_owners,
            ).replace(
                "{legal_tag}", TEST_DATA_STORE.get("legal_tag"),
            )
        )
        return json.loads(data_str)
