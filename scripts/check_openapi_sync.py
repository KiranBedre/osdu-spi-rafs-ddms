import argparse
import difflib
import json
from pathlib import Path

import yaml

from scripts.generate_openapi import (
    DEFAULT_OUTPUT_PATH,
    configure_environment,
    load_openapi_schema,
    mark_content_schema_version_required,
    canonicalize_openapi_schema,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check that the committed OpenAPI specification matches the generated FastAPI schema.",
    )
    parser.add_argument(
        "--spec-path",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path to the committed OpenAPI YAML file.",
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


def format_schema(schema: dict) -> str:
    return yaml.dump(schema, default_flow_style=False, allow_unicode=True, sort_keys=True)


def load_committed_schema(spec_path: Path) -> dict:
    return yaml.safe_load(spec_path.read_text(encoding="utf-8"))


def print_diff(expected_text: str, generated_text: str, spec_path: Path) -> None:
    diff_lines = difflib.unified_diff(
        expected_text.splitlines(),
        generated_text.splitlines(),
        fromfile=str(spec_path),
        tofile="generated-openapi.yaml",
        lineterm="",
    )
    print("OpenAPI spec drift detected. Regenerate the committed spec with:")
    print("python scripts/generate_openapi.py")
    print("")
    print("\n".join(diff_lines))


def main() -> int:
    args = parse_args()
    configure_environment(args)

    spec_path = Path(args.spec_path).resolve()
    try:
        committed_schema = load_committed_schema(spec_path)
    except FileNotFoundError:
        print(f"Committed spec not found: {spec_path}")
        return 1
    except (json.JSONDecodeError, yaml.YAMLError) as error:
        print(f"Committed spec is not valid: {spec_path}: {error}")
        return 1

    generated_schema = load_openapi_schema()
    generated_schema = mark_content_schema_version_required(generated_schema)
    generated_schema = canonicalize_openapi_schema(generated_schema)

    if committed_schema == generated_schema:
        print(f"OpenAPI spec is in sync: {spec_path}")
        return 0

    print_diff(format_schema(committed_schema), format_schema(generated_schema), spec_path)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
