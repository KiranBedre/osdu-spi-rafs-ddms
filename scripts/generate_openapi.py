import argparse
import json
import os
import sys
from pathlib import Path
from typing import Type

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_PATH = REPO_ROOT / "docs" / "api" / "community" / "v2" / "openapi.yaml"
FALLBACK_APP_NAME = "Rock and Fluid Sample DDMS"
FALLBACK_APP_VERSION = "0.2.0"

sys.path.insert(0, str(REPO_ROOT))


def _get_model_field_default(model_class: Type[object], field_name: str, fallback: str) -> str:
    model_fields = getattr(model_class, "model_fields", None)
    if model_fields and field_name in model_fields:
        return model_fields[field_name].default

    legacy_fields = getattr(model_class, "__fields__", None)
    if legacy_fields and field_name in legacy_fields:
        return legacy_fields[field_name].default

    return fallback


def get_default_app_metadata() -> tuple[str, str]:
    from app.core.settings.app import AppSettings  # noqa: WPS433

    return (
        _get_model_field_default(AppSettings, "app_name", FALLBACK_APP_NAME),
        _get_model_field_default(AppSettings, "app_version", FALLBACK_APP_VERSION),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the committed OpenAPI specification from the RAFS FastAPI application.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path to the generated OpenAPI YAML file.",
    )
    parser.add_argument(
        "--app-env",
        default="test",
        help="Application environment used during spec generation.",
    )
    parser.add_argument(
        "--openapi-prefix",
        default="/api/rafs-ddms",
        help="OpenAPI prefix used during spec generation.",
    )
    parser.add_argument(
        "--cloud-provider",
        default="",
        help="Cloud provider value used during spec generation.",
    )
    parser.add_argument(
        "--app-name",
        default=None,
        help="Application name used during spec generation.",
    )
    parser.add_argument(
        "--app-version",
        default=None,
        help="Application version used during spec generation.",
    )
    return parser.parse_args()


def configure_environment(args: argparse.Namespace) -> None:
    os.environ["APP_ENV"] = args.app_env
    os.environ["OPENAPI_PREFIX"] = args.openapi_prefix
    os.environ["CLOUD_PROVIDER"] = args.cloud_provider

    default_app_name, default_app_version = get_default_app_metadata()
    if args.app_name is None:
        args.app_name = default_app_name
    if args.app_version is None:
        args.app_version = default_app_version

    os.environ["APP_NAME"] = args.app_name
    os.environ["APP_VERSION"] = args.app_version


def load_openapi_schema() -> dict:
    from app.main import app  # noqa: WPS433

    return app.openapi()


def mark_content_schema_version_required(schema: dict) -> dict:
    """Mark content_schema_version query parameter as required in all endpoints.

    The parameter is optional in code to support the deprecated Accept header
    versioning fallback, but it should be shown as required in the spec to
    guide clients towards the preferred usage.
    """
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            for param in operation.get("parameters", []):
                if param.get("name") == "content_schema_version" and param.get("in") == "query":
                    param["required"] = True
    return schema


def normalize_openapi_schema(schema: dict) -> dict:
    """Normalize schema keys for deterministic and spec-compliant output.

    Some generated nodes may contain `app_name` where `title` is expected.
    This pass rewrites those keys recursively.
    """

    components = schema.setdefault("components", {}) if isinstance(schema, dict) else {}
    component_schemas = components.setdefault("schemas", {}) if isinstance(components, dict) else {}

    def _normalize(value: object) -> object:
        if isinstance(value, dict):
            normalized: dict = {}
            for key, item in value.items():
                if key == "definitions" and isinstance(item, dict):
                    # OpenAPI 3 does not allow `definitions`; move entries to components/schemas.
                    for schema_name, schema_value in item.items():
                        component_schemas.setdefault(schema_name, _normalize(schema_value))
                    continue

                target_key = "title" if key == "app_name" else key

                # OpenAPI 3 requires exclusiveMinimum/exclusiveMaximum as booleans.
                if key == "exclusiveMinimum" and isinstance(item, (int, float)) and not isinstance(item, bool):
                    normalized["minimum"] = item
                    normalized["exclusiveMinimum"] = True
                    continue
                if key == "exclusiveMaximum" and isinstance(item, (int, float)) and not isinstance(item, bool):
                    normalized["maximum"] = item
                    normalized["exclusiveMaximum"] = True
                    continue

                normalized[target_key] = _normalize(item)

            ref_value = normalized.get("$ref")
            if isinstance(ref_value, str) and ref_value.startswith("#/definitions/"):
                normalized["$ref"] = ref_value.replace("#/definitions/", "#/components/schemas/", 1)
            return normalized
        if isinstance(value, list):
            return [_normalize(item) for item in value]
        return value

    return _normalize(schema)


def canonicalize_openapi_schema(schema: dict) -> dict:
    """Convert generated schema to a deterministic, plain-data representation."""
    clean_schema = json.loads(json.dumps(schema, default=str))
    return normalize_openapi_schema(clean_schema)


def write_openapi_schema(schema: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean_schema = canonicalize_openapi_schema(schema)
    output_path.write_text(
        yaml.dump(clean_schema, default_flow_style=False, allow_unicode=True, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    configure_environment(args)
    schema = load_openapi_schema()
    schema = mark_content_schema_version_required(schema)
    output_path = Path(args.output).resolve()
    write_openapi_schema(schema, output_path)
    print(f"Generated OpenAPI spec: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
