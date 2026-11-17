import re

FIXTURE_RECORD_ID = re.compile(r"(?<![\w.:-])[\w.-]+:(?:master-data|work-product-component)--\w+:[\w.%+-]+")


def scope_fixture_ids(value: str, namespace: str) -> str:
    """Scope fixture record IDs without changing reference data or versions."""
    if not namespace:
        return value

    def replace(match: re.Match) -> str:
        record_id = match.group()
        suffix = f"_{namespace}"
        return record_id if record_id.endswith(suffix) else record_id + suffix

    return FIXTURE_RECORD_ID.sub(replace, value)
