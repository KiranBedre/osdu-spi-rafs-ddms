import copy

from tests.integration.config import CONFIG, DataFiles, DataTemplates


def test_fluid_create_record_with_x_collaboration_header(api, helper, tests_data, x_collaboration_header):

    create_record_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    create_record_payload["id"] = (
        DataTemplates.ID_FLUID_MODEL.format(partition=CONFIG["DATA_PARTITION"]) + helper.generate_random_record_id()
    )
    response = api.fluid_model.post_record(
        [create_record_payload],
        headers={"x-collaboration": x_collaboration_header},
    )
    assert response["recordCount"] == 1
