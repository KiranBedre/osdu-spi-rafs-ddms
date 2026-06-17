import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Type

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_PATH = REPO_ROOT / "docs" / "spec" / "openapi.json"
DEFAULT_API_VERSION_SEGMENT = "v2"
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
        help="Path to the generated OpenAPI JSON file.",
    )
    parser.add_argument(
        "--yaml-output",
        default=None,
        help=(
            "Path to the generated OpenAPI YAML file. "
            "If omitted, defaults to docs/api/community/v<detected>/openapi.yaml. "
            "Use an empty value to skip YAML generation."
        ),
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


def sync_schema_app_metadata(schema: dict, app_name: str, app_version: str) -> dict:
    """Keep OpenAPI info metadata aligned with code-level app settings."""
    info = schema.setdefault("info", {})
    info["title"] = app_name
    info["version"] = app_version
    return schema


def detect_api_version_segment(schema: dict) -> str:
    """Detect highest /v<integer> path segment in OpenAPI paths."""
    versions = []
    for path in schema.get("paths", {}).keys():
        matches = re.findall(r"/v(\d+)(?:/|$)", path)
        versions.extend(int(match) for match in matches)

    if not versions:
        return DEFAULT_API_VERSION_SEGMENT

    return f"v{max(versions)}"


def get_default_yaml_output_path(schema: dict) -> Path:
    """Compute community OpenAPI path using the detected API version."""
    version_segment = detect_api_version_segment(schema)
    return REPO_ROOT / "docs" / "api" / "community" / version_segment / "openapi.yaml"


def write_openapi_schema(schema: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_openapi_yaml_schema(schema: dict, output_path: Path) -> None:
    """Write classic block-style YAML for community scanners."""

    class NoAliasSafeDumper(yaml.SafeDumper):
        def ignore_aliases(self, data):  # noqa: WPS110
            return True

    # Normalize pydantic/url subclasses to plain JSON-native types.
    normalized_schema = json.loads(json.dumps(schema, ensure_ascii=False, sort_keys=True))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.dump(
            normalized_schema,
            Dumper=NoAliasSafeDumper,
            allow_unicode=True,
            sort_keys=True,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    configure_environment(args)
    schema = load_openapi_schema()
    schema = mark_content_schema_version_required(schema)
    schema = sync_schema_app_metadata(schema, args.app_name, args.app_version)
    output_path = Path(args.output).resolve()
    write_openapi_schema(schema, output_path)
    print(f"Generated OpenAPI JSON spec: {output_path}")

    if args.yaml_output == "":
        return 0

    if args.yaml_output is None:
        yaml_output_path = get_default_yaml_output_path(schema).resolve()
    else:
        yaml_output_path = Path(args.yaml_output).resolve()

    if yaml_output_path:
        write_openapi_yaml_schema(schema, yaml_output_path)
        print(f"Generated OpenAPI YAML spec: {yaml_output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
