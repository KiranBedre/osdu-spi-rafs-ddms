import copy

from tests.integration.config import CONFIG, DataFiles, DataTemplates


def test_fluid_create_record_with_x_collaboration_header(
    api,
    helper,
    tests_data,
    x_collaboration_header,
    fluid_model_collaboration_dependencies,
):

    create_record_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    create_record_payload["id"] = (
        DataTemplates.ID_FLUID_MODEL.format(partition=CONFIG["DATA_PARTITION"]) + helper.generate_random_record_id()
    )
    headers = {"x-collaboration": x_collaboration_header}
    try:
        response = api.fluid_model.post_record([create_record_payload], headers=headers)
        assert response["recordCount"] == 1
    finally:
        api.storage.purge_record(create_record_payload["id"], headers=headers)


def test_fluid_create_record_with_malformed_x_collaboration_header(api, helper, tests_data):
    create_record_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    record_id = DataTemplates.ID_FLUID_MODEL.format(partition=CONFIG["DATA_PARTITION"]) + helper.generate_random_record_id()
    create_record_payload["id"] = record_id

    response = api.fluid_model.post_record(
        [create_record_payload],
        raw=True,
        headers={"x-collaboration": "id=not-a-uuid,application=rafsddms"},
        allowed_codes=[400],
    )
    response_body = response.json()
    assert response.status_code == 400
    assert response_body["code"] == 400
    assert response_body["reason"] == "Validation error."
    assert "invalid directive 'id': 'not-a-uuid'" in response_body["message"]
    assert "'id' must be a valid GUID/UUID" in response_body["message"]

    default_context_response = api.storage.get(
        path=f"/records/{record_id}",
        allowed_codes=[404],
    )
    assert default_context_response.status_code == 404
