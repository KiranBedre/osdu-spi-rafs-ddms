from app.api.dependencies.request import get_x_collaboration_header


def test_get_x_collaboration_header_returns_original_header():
    header = "id=not-a-uuid,application=myapp"

    result = get_x_collaboration_header(x_collaboration=header)

    assert result == header


def test_get_x_collaboration_header_returns_none_when_header_missing():
    result = get_x_collaboration_header(x_collaboration=None)

    assert result is None
