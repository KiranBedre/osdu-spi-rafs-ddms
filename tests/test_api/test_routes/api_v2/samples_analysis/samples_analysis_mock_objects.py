from app.resources.paths import (
    CommonRelativePathsV2,
)
from app.models.data_schemas.sample_analysis_api_v2.base import (
    PATH_TO_DATA_MODEL_VERSIONS_API_V2, 
)
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    PARTITION, 
    FILE_GENERIC_TYPE, 
    SAMPLE_TYPE,
    OSDU_GENERIC_RECORD,
    TEST_DATASET_UID, 
    TEST_SAMPLE_ID, 
    TEST_SAMPLE_ID_2,
    TEST_SAMPLES_ANALYSIS_ID,
    BASE_DATA_V2_PATH, 
)

samples_analysis_relative_paths_v2 = CommonRelativePathsV2()

SamplesAnalysisContentPathsV2 = type(
    "SamplesAnalysisContentPathsV2",
    (),
    {
        field_name: f"{BASE_DATA_V2_PATH}{relative_path}"
        for field_name, relative_path in zip(
            samples_analysis_relative_paths_v2._fields, samples_analysis_relative_paths_v2
        )
    },
)

SamplesAnalysisDatasetIDsV2 = type(
    "SamplesAnalysisDatasetIDsV2",
    (),
    {
        field_name: f"{PARTITION}:{FILE_GENERIC_TYPE}:{relative_path.removeprefix('/data/')}-{TEST_DATASET_UID}"
        for field_name, relative_path in zip(
            samples_analysis_relative_paths_v2._fields, samples_analysis_relative_paths_v2
        )
    },
)

SamplesAnalysisDDDMSURNsV2 = type(
    "SamplesAnalysisDDDMSURNsV2",
    (),
    {
        field_name: f"urn://rafs-v2/{relative_path.removeprefix('/data/')}data/"
        f"{TEST_SAMPLES_ANALYSIS_ID}/{getattr(SamplesAnalysisDatasetIDsV2, field_name)}"
        for field_name, relative_path in zip(
            samples_analysis_relative_paths_v2._fields, samples_analysis_relative_paths_v2
        )
    },
)

SamplesAnalysisDDMSURNsWithVersionV2 = type(
    "SamplesAnalysisDDMSURNsWithVersionV2",
    (),
    {
        field_name: {
            version: f"{getattr(SamplesAnalysisDDDMSURNsV2, field_name)}/{version}"
            for version in PATH_TO_DATA_MODEL_VERSIONS_API_V2[relative_path]
        }
        for field_name, relative_path in zip(
            samples_analysis_relative_paths_v2._fields, samples_analysis_relative_paths_v2
        )
    },
)

SamplesAnalysisRecordsV2 = type(
    "SamplesAnalysisRecordsV2",
    (),
    {
        field_name: {
            version: {
                **OSDU_GENERIC_RECORD.model_dump(exclude_none=True),
                "data": {
                    "SampleIDs": [TEST_SAMPLE_ID],
                    "DDMSDatasets": [ddms_urn],
                },
            }
            for version, ddms_urn in getattr(SamplesAnalysisDDMSURNsWithVersionV2, field_name).items()
        }
        for field_name in samples_analysis_relative_paths_v2._fields
    },
)

# ==============================================================================
# Mock objects for testing SampleID consistency between content data and the 
# associated OSDU record's SampleIDs.
# ==============================================================================

SAMPLE_ID_CONSISTENCY_TESTS_EXCLUDED_MODELS = {
    "MULTIPLE_SALINITY", #does not have SampleID column
}

TEST_MISMATCHED_SAMPLE_ID = f"{PARTITION}:{SAMPLE_TYPE}:mismatched_sample_test_id:"

TEST_SAMPLES_ANALYSIS_DATA_PAYLOAD_WITH_MISMATCHED_SAMPLE_ID = {
    "columns":[
        "SamplesAnalysisID",
        "SampleID",
        "Meta",
    ],
    "index":[
        0,
    ],
    "data":[
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_MISMATCHED_SAMPLE_ID, 
            [],
        ]
    ]
}

TEST_SAMPLES_ANALYSIS_MULTI_ROW_DATA_PAYLOAD_WITH_MISMATCHED_SAMPLE_ID = {
    "columns":[
        "SamplesAnalysisID",
        "SampleID",
        "Meta", 
    ],
    "index":[
        0, 
        1, 
    ],
    "data":[
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_SAMPLE_ID, 
            [],
        ], 
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_MISMATCHED_SAMPLE_ID, 
            [], 
        ], 
    ]
}

TEST_SAMPLES_ANALYSIS_MULTI_ROW_DATA_PAYLOAD = {
    "columns":[
        "SamplesAnalysisID",
        "SampleID",
        "Meta",
    ],
    "index":[
        0, 
        1, 
    ],
    "data":[
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_SAMPLE_ID, 
            [], 
        ], 
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_SAMPLE_ID_2, 
            [], 
        ], 
    ]
}

TEST_SAMPLES_ANALYSIS_DATA_PAYLOAD = {
    "columns":[
        "SamplesAnalysisID",
        "SampleID",
        "Meta",
    ],
    "index":[
        0, 
    ],
    "data":[
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_SAMPLE_ID, 
            [], 
        ], 
    ]
}

TEST_SAMPLES_ANALYSIS_DATA_PAYLOAD_WITH_NULL_SAMPLE_ID = {
    "columns":[
        "SamplesAnalysisID",
        "SampleID",
        "Meta",
    ],
    "index":[
        0, 
    ],
    "data":[
        [
            TEST_SAMPLES_ANALYSIS_ID,
            None,
            [], 
        ], 
    ]
}

TEST_SAMPLES_ANALYSIS_RECORD_DATA_WITHOUT_SAMPLE_IDS_FIELD = {
    **OSDU_GENERIC_RECORD.model_dump(exclude_none=True),
    **{
        "data": {
            "DDMSDatasets": [],
        },
    },
}

TEST_SAMPLES_ANALYSIS_RECORD_DATA_WITHOUT_SAMPLE_IDS = {
    **OSDU_GENERIC_RECORD.model_dump(exclude_none=True),
    **{
        "data": {
            "SampleIDs": [],
            "DDMSDatasets": [],
        },
    },
}

SamplesAnalysisRecordsWithMultipleSampleIDsV2 = type(
    "SamplesAnalysisRecordsWithMultipleSampleIDsV2",
    (),
    {
        field_name: {
            version: {
                **OSDU_GENERIC_RECORD.model_dump(exclude_none=True),
                "data": {
                    "SampleIDs": [TEST_SAMPLE_ID, TEST_SAMPLE_ID_2],
                    "DDMSDatasets": [ddms_urn],
                },
            }
            for version, ddms_urn in getattr(SamplesAnalysisDDMSURNsWithVersionV2, field_name).items()
        }
        for field_name in samples_analysis_relative_paths_v2._fields
    },
)
