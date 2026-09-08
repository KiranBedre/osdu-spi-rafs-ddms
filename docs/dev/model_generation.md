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
| Tool | `datamodel-codegen` (v0.53.0+) |
| `--output-model-type` | `pydantic_v2.BaseModel` |
| `--use-annotated` | Enabled (produces `Annotated[T, ...]` for constraints) |
| `--disable-future-imports` | Enabled (no `from __future__ import annotations`) |
| `--use-double-quotes` | Enabled |

### RAFS post-processing (`_build_model_for_rafs`)

After codegen, `model_generator.py` automatically:
1. Replaces `pydantic.BaseModel` with `app.models.config.RafsBaseModel`
2. Prepends the Apache 2.0 copyright header

### Alias generation (`_MetaModel = Meta`)

`datamodel-codegen` produces aliases like `_MetaModel = Meta` when a JSON schema has a class name that collides with a field name in the same file. These are **deterministic** — regeneration with the same schema and flags produces the same aliases. Do not remove them manually; they prevent `PydanticSchemaGenerationError` at import time.

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
| `from __future__ import annotations` must stay **disabled** | Enables it turns all annotations into strings at runtime, breaking pydantic v2 field introspection (`model_fields`, `annotation`) |
| `_MetaModel`-style aliases must not be deleted | Removing one triggers `PydanticSchemaGenerationError` — the alias resolves a name collision between a class and a field referencing it |
| `Annotated[T, StringConstraints(...)]` for regex/length | Pydantic v2 replaces `Field(regex=...)` with metadata-based constraints via `Annotated` |
| `Literal` used for const-value fields | Pydantic v2 replaces `const=True` with `Literal["value"]` |
| Generated files excluded from flake8 | `setup.cfg` excludes `app/models/*` — codegen output may have lines WPS/flake8 would flag |
