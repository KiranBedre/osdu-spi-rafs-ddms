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

from pandera import pandas as pa

TEST_SCHEMA = pa.DataFrameSchema(
    {
        "SampleDepth": pa.Column(float),
        "SampleNumber": pa.Column(int, required=False),
        "GrainDensity": pa.Column(float, nullable=True, required=False),
        "Remarks": pa.Column(str, required=False),
    }
)

CORRECT_TEST_BULK_DATA = """{
    "columns": [
        "SampleDepth",
        "SampleNumber",
        "GrainDensity",
        "Remarks"
    ],
    "index": [1, 2],
    "data": [
        [1000, 1, 100.0, "Comment"],
        [1000.5, 2, 100.5, "01-01-2023"]
    ]
}"""

INCORRECT_TEST_BULK_DATA = """{
    "columns": [
        "SampleDepth",
        "SampleNumber",
        "GrainDensity",
        "Remarks"
    ],
    "index": [1, 2],
    "data": [
        [1000, 1, 100.0, "Comment"],
        ["wrong_string", 2, 100.5, "01-01-2023"]
    ]
}"""


TEST_RECORD = {
    "id": "test_id",
    "kind": "test_kind",
    "data": {
        "NotInTheList": "NotInTheList",
        "StringID": "partition:master-data--SomeType:StringID:",
        "ListIDs": [
            "partition:reference-data--SomeType:ListID1:",
            "partition:reference-data--SomeType:ListID2:",
        ],
        "DictIDs": {
            "StringID": "partition:work-product-component--SomeType:DictStringID:",
            "ListIDs": [
                "partition:work-product-component--SomeType:DictListID1:",
                "partition:work-product-component--SomeType:DictListID2:",
            ],
        },
        "ListOfDicts": [
            {
                "ListOfDictsStringID": "partition:master-data--SomeType:ListOfDictsStringID:",
                "NotIdentifier": "NotIdentifier",
            },
        ],
    },
}

TEST_ID_MISSING_FIELD = ["MissingField"]

TEST_IDS_FIELDS = ["StringID", "ListIDs", "DictIDs", "ListOfDicts"]

EXPECTED_IDS_LIST = [
    "partition:master-data--SomeType:StringID",
    "partition:reference-data--SomeType:ListID1:"
    "partition:reference-data--SomeType:ListID2:"
    "partition:work-product-component--SomeType:DictStringID:",
    "partition:work-product-component--SomeType:DictListID1:",
    "partition:work-product-component--SomeType:DictListID2:",
    "partition:master-data--SomeType:ListOfDictsStringID:",
]
