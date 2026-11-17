# Model Generation Guide

## Regenerating Models

### Source schemas

JSON schemas live in `app/models/data_schemas/jsonschema/<schema_group>/`:

```
app/models/data_schemas/jsonschema/
├── depth_shift_v2/
├── reservoir_simulation_rock_physics_v2/
├── sample_analysis_api_v2/
└── saturation_function_set_api_v2/
```

### Command

```bash
python scripts/model_generator.py \
  app/models/data_schemas/jsonschema/<schema_group> \
  app/models/data_schemas/<schema_group> \
  "1.0.0.json"
```

Example (sample analysis):

```bash
python scripts/model_generator.py \
  app/models/data_schemas/jsonschema/sample_analysis_api_v2 \
  app/models/data_schemas/sample_analysis_api_v2 \
  "1.0.0.json"
```

### Output

Generated Python models go to `app/models/data_schemas/<schema_group>/`. These files **are committed** — they are part of the application source.

---

## Generator Configuration

| Setting | Value |
|---------|-------|
| Tool | `datamodel-codegen`, pinned in `scripts/requirements.txt` (currently `0.81.0`) |
| `--output-model-type` | `pydantic_v2.BaseModel` |
| `--use-annotated` | Enabled (produces `Annotated[T, ...]` for constraints) |
| `--disable-future-imports` | Enabled (no `from __future__ import annotations`) |
| `--use-double-quotes` | Enabled |
| `--formatters` | `black isort` (pinned explicitly — as of `datamodel-code-generator` 0.78.0, omitting `--formatters` still defaults to `isort` then `black`, but emits a `FutureWarning` that this default will change to `builtin`; pinning freezes today's output against that future change) |

### RAFS post-processing (`_build_model_for_rafs`)

After codegen, `model_generator.py` automatically:
1. Replaces `pydantic.BaseModel` with `app.models.config.RafsBaseModel`
2. Prepends the Apache 2.0 copyright header
3. Fixes field/class name collisions (see below)

### Field/class name collision fix (`_fix_field_class_name_collisions`)

A field cannot be named identically to a type it references in its own annotation (e.g. `Conditions: Conditions | None`). In a class body, Python binds a field's default value to that name *before* evaluating the annotation — so by the time the annotation is evaluated, the name already refers to the just-bound value (e.g. `None`), not the class. This is plain, ordinary annotation-evaluation behavior; it happens whether or not `from __future__ import annotations` is active.

`datamodel-codegen` avoids this itself by renaming the colliding *field* — e.g. `Conditions` becomes `Conditions_1` with `Field(alias="Conditions")` — but that breaks code in this app that assumes a field's Python attribute name matches its wire-format name (notably `app/bulk_data_validation/data_validation.py`'s nested-error-path builder, and any test helper that builds payloads from `model_fields` directly).

`model_generator.py` post-processes the raw codegen output to fix this a different way: for every field the tool renamed to `X_1` with `Field(alias="X")` — that rename *is* the tool's own collision signal, so no separate detection is needed — it inserts `_XModel = X` right after class `X`'s definition, points the colliding field's annotation at `_XModel` instead of `X`, and restores the field's original name (`X`), dropping the now-unneeded alias. This is fully deterministic and requires no schema-specific judgment. Do not delete a `_XModel = X` line by hand — regenerating recreates it identically, and removing one without also renaming its field back reintroduces the collision, which fails at import time with `PydanticSchemaGenerationError` or a `TypeError` on the annotation.

---

## Validation After Regeneration

Run in order:

```bash
# 1. Unit tests
docker-compose build tests && docker-compose up tests

# 2. OpenAPI sync (must match committed spec)
docker run --rm -v $(pwd):/workspace -w /workspace rafs-tests \
  python scripts/check_openapi_sync.py \
  --app-env test --openapi-prefix "/api/rafs-ddms" --cloud-provider ""

# 3. If OpenAPI drifted, regenerate and re-commit
docker run --rm -v $(pwd):/workspace -w /workspace rafs-tests \
  python scripts/generate_openapi.py

# 4. Linter (CI parity)
docker run --rm -v $(pwd):/workspace rafs-tests \
  flake8 /workspace --config=/workspace/setup.cfg
```

---

## Known Constraints

| Constraint | Reason |
|------------|--------|
| `from __future__ import annotations` must stay **disabled** | This is the tested, verified configuration. Its originally-stated rationale here ("breaks pydantic v2 field introspection") was never actually verified and is not accurate as a general claim — tested directly, pydantic v2 resolves postponed annotations into real types via `model_fields[...].annotation` correctly. The field/class name collision crash this flag was blamed for is a separate, plain-annotation-evaluation bug (see Field/class name collision fix above) that happens with the flag either on or off; it is fixed by the `_XModel` aliasing, not by this flag |
| `_XModel`-style aliases must not be deleted | These are inserted by `model_generator.py`'s post-processing (`_fix_field_class_name_collisions`), not by `datamodel-codegen` itself — regeneration recreates them identically. Deleting one without also renaming its field back to match reintroduces a field/class name collision that fails at import time |
| `Annotated[T, StringConstraints(...)]` for regex/length | Pydantic v2 replaces `Field(regex=...)` with metadata-based constraints via `Annotated` |
| `Literal` used for const-value fields | Pydantic v2 replaces `const=True` with `Literal["value"]` |
| Generated files excluded from flake8 | `setup.cfg` excludes `app/models/*` — codegen output may have lines WPS/flake8 would flag |
