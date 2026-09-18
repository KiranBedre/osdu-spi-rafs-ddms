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


def canonicalize_openapi_schema(schema: dict) -> dict:
    """Convert generated schema to a deterministic, plain-data representation."""
    return json.loads(json.dumps(schema, default=str))


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
    output_path = Path(args.output).resolve()
    write_openapi_schema(schema, output_path)
    print(f"Generated OpenAPI spec: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
