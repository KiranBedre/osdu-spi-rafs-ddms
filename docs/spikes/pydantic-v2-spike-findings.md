# Pydantic v2 Migration — Spike Findings (Issue #768)

**Date:** 2026-05-15  
**Branch:** `feature/pydantic-v2-migration`  
**Author:** Edgar Rivera  
**Spike commit:** `22c3a066`

---

## 0. Background

Pydantic v1 entered maintenance-only mode in June 2023 and will not receive new features or security fixes. Pydantic v2 (released June 2023) offers 5–50× faster validation via a Rust core (`pydantic-core`), stricter type enforcement at model-definition time, and native `pydantic-settings` split that is already required for settings management. This spike evaluates whether the migration is feasible for RAFS, documents every breaking change encountered, and estimates full migration effort — so the team can make a go/no-go decision with full information.

**Scope of the spike:** Requirements, settings layer, all generated data schema models, all domain models. The API layer and test assertions were intentionally left for the full migration (see Section 7).

---

## 1. Feasibility

**Migration is feasible.** The pilot demonstrated end-to-end migration of the full data schema layer (54 models in `sample_analysis_api_v2`, plus `reservoir_simulation_rock_physics_v2`, `saturation_function_set_api_v2`, all domain models, all settings classes) and reached **1345 / 1710 tests passing (79%)** on a single commit with no manual per-file editing of business logic.

The remaining 21% failures (347 tests) map to exactly **three well-scoped root causes** that were not part of the pilot scope — see Section 7.

---

## 2. Dependency Compatibility

`pip-compile` was run against the updated `requirements.in` (pydantic v2 pins) inside the CI Docker image to verify the full dependency tree resolves without conflicts.

**Result: no conflicts.**

| Package | Current | Resolves with pydantic v2 |
|---|---|---|
| `fastapi` | 0.121.1 | ✅ compatible (pydantic v2 support since 0.95.0) |
| `fastapi-cache2` | 0.2.1 | ✅ |
| `pandera` | 0.25.0 | ✅ (already requires pydantic v2) |
| `prometheus-fastapi-instrumentator` | 6.1.0 | ✅ |
| `opentelemetry-instrumentation-fastapi` | 0.48b0 | ✅ |

**New packages entering the dependency tree:**

| Package | Version | Purpose |
|---|---|---|
| `pydantic-core` | 2.46.4 | Rust validation backend (new transitive dep of pydantic v2) |
| `pydantic-settings` | 2.14.1 | Settings management (replaces `pydantic[dotenv]`) |
| `annotated-types` | 0.7.0 | Transitive dep of pydantic v2 |
| `typing-inspection` | 0.4.2 | Transitive dep of pydantic-settings |

No existing package in the tree requires `pydantic<2`. **No version downgrade or package swap is needed.**

---

## 3. Representative Model Used

**File:** `app/models/data_schemas/sample_analysis_api_v2/routine_core_analysis_data_model_1_0_0.py`

Chosen because it covers the maximum number of v2 breaking-change categories in one file:
- `RafsBaseModel` inheritance (`Extra.forbid` cascade)
- Local `class Config: extra = Extra.forbid` overrides
- `constr(regex=...)` — 8 occurrences
- `Field(const=True, ...)` — 4 `kind` fields
- `List[Union[Meta, Meta1, Meta2, Meta3]]` — union type schema generation

---

## 4. Issues Encountered (Step by Step)

### 3.1 `BaseSettings` — Hard Import Error (Blocker)

**What:** `from pydantic import BaseSettings` raises `PydanticImportError` in v2. Pydantic v2 completely removes `BaseSettings` from the core package — it is in `pydantic-settings` now.

**Severity:** Hard blocker. Unlike `Extra`, `constr`, and `validator` (which emit deprecation warnings but still work), `BaseSettings` raises a hard error at import time and cascades through the entire app.

**Fix:** Add `pydantic-settings>=2.7,<3` to requirements. Replace `from pydantic import BaseSettings` with `from pydantic_settings import BaseSettings`. Replace `class Config(object): env_file = ".env"` with `model_config = SettingsConfigDict(env_file=".env", extra="ignore")`.

**Files affected:** 7 app files + 1 test file + 3 settings subclasses.

**Key lesson:** `BaseSettings` migration cannot be deferred or done incrementally — it must be bundled with the requirements change in the same commit. Any file that imports the old form will fail immediately.

---

### 3.2 Settings Subclass `class Config` Inheritance Broken

**What:** `class DevAppSettings(AppSettings): class Config(AppSettings.Config): env_file = ".env"` raises `AttributeError: Config` in v2 because pydantic v2 models no longer have a `.Config` class attribute.

**Fix:** Replace `class Config(AppSettings.Config)` with either `pass` (if inheriting the same env_file) or `model_config = SettingsConfigDict(env_file="other.env")` for overrides.

---

### 3.3 Unannotated Field Override in Subclass — Hard Error

**What:** `class TestAppSettings(AppSettings): enable_gc_collect = False` (overriding a field without re-annotating it) raises `PydanticUserError: Field '...' defined on a base class was overridden by a non-annotated attribute`.

**Fix:** Add the type annotation: `enable_gc_collect: bool = False`.

**Scope:** Any subclass that overrides a field without its type annotation. Grep: `^    \w+ = ` inside classes that inherit from a `BaseSettings` or `BaseModel`.

---

### 3.4 `str = None` Fields Fail Validation — Hard Error

**What:** `commit_id: str = None` in a `BaseSettings` subclass raises `ValidationError: Input should be a valid string` when the settings are instantiated (the default `None` fails the `str` validator).

**Reason:** Pydantic v1 was lenient about `None` defaults on non-Optional fields. Pydantic v2 strictly enforces type annotations.

**Fix:** Change `field: str = None` to `field: Optional[str] = None`. This applies to ALL settings and model classes.

**Scope:** ~18 occurrences in `app/core/settings/` and `app/providers/config.py`. Grep: `:\s+str = None` and `:\s+int = None` across the codebase.

---

### 3.5 `Field(const=True, ...)` — Hard Error

**What:** `kind: str = Field("Unit", const=True, ...)` raises `PydanticUserError: 'const' is removed, use 'Literal' instead` at class-definition time.

**Severity:** Hard error. Like `BaseSettings`, this cannot be deferred.

**Fix:** `kind: Literal["Unit"] = Field("Unit", ...)`. Remove `const=True` from the `Field(...)` call.

**Scope:** 216 occurrences across 54 files in `sample_analysis_api_v2` alone. Scriptable with regex.

**Key lesson:** All models in a folder that share a `base.py` importer must be migrated together. `const=True` in ANY imported model blocks the entire module chain.

---

### 3.6 `constr(regex=...)` — Hard Error

**What:** `constr(regex=r"...")` raises `TypeError: constr() got an unexpected keyword argument 'regex'` in v2 (the argument was renamed to `pattern=`).

**Severity:** Hard error at class-definition time.

**Fix:** Replace `constr(regex=r"...")` with `Annotated[str, StringConstraints(pattern=r"...")]`.

**Scope:** ~589 occurrences across all data schema model files. Scriptable, but has edge cases:
- Multi-line `constr(` calls must be handled with DOTALL regex or AST-based tools
- `Optional[constr(...)]` → `Optional[Annotated[str, StringConstraints(...)]]` (not just renaming)
- `List[constr(...)]` → `List[Annotated[str, StringConstraints(...)]]`
- `(constr(...) | None)` (Python 3.10+ pipe syntax) → `Optional[Annotated[str, StringConstraints(...)]]`

**Warning:** `StringConstraints(...)` is a constraint object, NOT a type. Using it bare (without `Annotated[str, ...]`) as a field annotation causes `AttributeError: 'StringConstraints' object has no attribute '__mro__'`. All occurrences must be wrapped.

---

### 3.7 Field-Name-Shadows-Class-Name — `PydanticSchemaGenerationError`

**What:** When a field name matches a class name used in its own type annotation — e.g., `Conditions: Optional[Conditions] = Field(None, ...)` — pydantic v2 fails with `PydanticSchemaGenerationError: Unable to generate pydantic-core schema for FieldInfo(annotation=NoneType, ...)`.

**Root cause:** Pydantic v2 resolves annotation names using the model's own namespace during schema generation. The field name `Conditions` shadows the class `Conditions`, leaving pydantic v2 with `NoneType` as the resolved type.

**This bug affects ALL generated models** from `datamodel-codegen` because the generated code uses PascalCase field names that match the nested model class names (e.g., `Conditions`, `Meta`, `GrainVolume`, `PoreVolume`, `Permeability`, `Compressibility`, etc.).

**Fix:** Add a module-level type alias before the class that uses the shadowed field:
```python
_ConditionsModel = Conditions  # alias to avoid field-name-shadows-class-name in pydantic v2

class PermeabilityItem(RafsBaseModel):
    Conditions: Optional[_ConditionsModel] = Field(None, ...)
```

**Scope:** Every generated model file that has a field sharing a name with a nested model class. Found in: ~52 files across `sample_analysis_api_v2`, `reservoir_simulation_rock_physics_v2`, domain models.

**Key lesson:** This is a systematic issue with ALL `datamodel-codegen`-generated pydantic models. The code generator would need to be updated to emit v2-compatible output, OR a post-generation script must apply the alias fix. This is the most pervasive structural issue of the migration.

---

### 3.8 `from __future__ import annotations` Interaction

**What:** Generated models with `from __future__ import annotations` compound the field-name-shadowing issue: annotations are stored as strings and evaluated lazily. When pydantic evaluates `"Optional[Conditions]"` with the model's namespace, field names in that namespace take precedence over module-level class names.

**Fix:** Remove `from __future__ import annotations` from generated model files. Without it, annotations are evaluated eagerly at class-body time where class names are unambiguous. This was applied to 102 generated model files.

**Side effect:** Some files used `Optional[...]` in annotations without importing `Optional` from `typing` (relying on string-form annotations to not fail). After removing `from __future__`, those imports must be added explicitly. Affected ~45 files.

---

### 3.9 `conlist(item_type=..., min_items=...)` — Hard Error

**What:** `conlist(item_type=str, min_items=1)` in `app/models/schemas/pandas_dataframe.py` (the `OrientSplit` model) raises `TypeError: conlist() got an unexpected keyword argument`.

**Fix:**
```python
# Before:
columns: conlist(item_type=str, min_items=1)

# After:
columns: Annotated[List[str], Field(min_length=1)]
```

This is the critical `OrientSplit` model used by all bulk data ingestion routes.

---

### 3.10 Deprecation Warnings (Non-Breaking but Noisy)

The following patterns still work in pydantic v2 but emit `PydanticDeprecatedSince20` warnings. They do NOT break the application but will be removed in v3:

| Pattern | Warning | Proper v2 Form |
|---|---|---|
| `class Config: extra = Extra.forbid` | `Support for class-based config is deprecated` | `model_config = ConfigDict(extra="forbid")` |
| `Extra.forbid` | `pydantic.config.Extra is deprecated` | `"forbid"` string literal |
| `.dict()` | `dict() is deprecated` | `.model_dump()` |
| `.construct()` | `construct() is deprecated` | `.model_construct()` |
| `.schema()` | (v1 compat shim) | `.model_json_schema()` |
| `__fields__` | `__fields__ is deprecated` | `.model_fields` |

These are in `app/models/schemas/osdu_storage.py` (`Acl`, `Legal` classes) and in the app API layer (`app/api/errors/`, `app/api/routes/`). They are NOT part of the pilot but must be fixed in the full migration to eliminate the 5000+ deprecation warnings currently emitted per test run.

---

## 5. Test Results

| | Before migration | After pilot |
|---|---|---|
| Tests collected | 0 (28 collection errors) | 1710 |
| Passed | — | **1345 (79%)** |
| Failed | — | 347 (21%) |
| Skipped | — | 18 |
| Collection errors | 28 | 0 |

> **Note on "28 collection errors":** These occurred at the start of the spike after pydantic v2 was installed but before any code was updated. Import-time hard errors (`BaseSettings`, `Field(const=True)`, `constr(regex=...)`) in the model layer prevented pytest from even loading test modules. Zero collection errors after the pilot means the import chain is fully clean.

The 347 failures break down as:

| Test file | Failures | Root cause |
|---|---|---|
| `test_api/test_routes/data/data_v2_test.py` | 303 | `FieldInfo.type_` / `FieldInfo.required` (Category L) |
| `test_api/test_routes/osdu/storage_records_test.py` | 36 | `osdu_storage.py` `Acl`/`Legal` still use `class Config: extra = Extra.forbid` (Category C) |
| `test_validation/test_osdu_storage_models.py` | 5 | v2 error message changed: `"extra fields not permitted"` → `"Extra inputs are not permitted"` (Category N) |
| `test_validation/test_data_schema.py` | 1 | `FieldInfo.type_` (Category L) |
| `test_validation/test_bulk_nullable_fields.py` | 1 | `FieldInfo.required` (Category L) |
| `test_validation/test_json_orient_formats.py` | 1 | `FieldInfo` attribute (Category L) |

All 347 failures have **three root causes**:

1. **`FieldInfo.type_` and `FieldInfo.required` (Category L)** — `app/api/routes/data/api.py` and `app/bulk_data_validation/data_validation.py` access `__fields__`, `field.type_`, and `field_info.required` which are removed in v2. Fix: `model.model_fields`, `field_info.annotation` (with `get_args()` to unwrap `Optional`), `field_info.is_required()`.

2. **`osdu_storage.py` still uses v1 config patterns (Category C)** — `Acl`, `Legal`, `OsduStorageRecord` in `app/models/schemas/osdu_storage.py` still use `class Config: extra = Extra.forbid` (deprecated shim still works, but the shim behavior for `extra_forbidden` error messages changed in v2).

3. **Error message casing (Category N)** — Tests assert `"extra fields not permitted"` (v1) but v2 emits `"Extra inputs are not permitted"`.

---

## 6. Identified Risks Before Full-Scale Migration

| Risk | Severity | Mitigation |
|---|---|---|
| Scripted `constr` → `StringConstraints` transformation has edge cases (parentheses in regex patterns, multiline forms, pipe syntax) | High | Use AST-based tool (`libcst`) instead of regex; validate output file by file |
| `datamodel-codegen` generates v1-incompatible code | High | Must update code generator config to emit v2 patterns, OR apply post-gen script; regenerating schemas after migration must also produce v2 code |
| `field.type_` unwrapping of `Optional[T]` — float cast in `_cast_float_columns` | High | `Optional[float]` annotation in v2 returns `Union[float, None]` via `get_args()`; the check `field.type_ is float` will silently skip all optional float columns |
| `__fields__` / `field_info.required` removal affects bulk data required-field validation | High | `is_required()` replacement is a one-line fix but must be tested against the full bulk validation suite |
| JSON Schema output format changed (`$defs` vs `definitions`, `Optional[T]` encoded as `anyOf`) | High | `build_normalized_schema_from_model` in `model_to_schema.py` and the filter system must be tested with v2 schema output; `jsonref` handles `$defs` correctly |
| Generated model files require systematic post-processing for field-name-class-name aliases | Medium | Script is required; any new schema generation must also apply the alias fix |
| 5000+ deprecation warnings per test run in current state | Low | Not breaking, but will degrade log readability in CI until full cleanup is done |

---

## 7. Constraints and Limitations

1. **Cannot migrate one model in isolation.** All models in a shared `base.py` importer (e.g., all 54 files in `sample_analysis_api_v2/`) must be migrated together. Any v1 pattern in any imported file blocks the entire chain.

2. **`datamodel-codegen` must be re-evaluated.** The current generator produces v1-only code (`constr`, `Field(const=True)`, `__root__`, `class Config`). Any future schema regeneration after migration will produce broken code unless the generator is updated or a post-gen script is applied.

3. **Type alias requirement is pervasive.** All field names that match nested model class names (PascalCase names like `Conditions`, `Meta`, `Permeability`, `Compressibility`, etc.) need module-level type aliases. This is a systematic property of OSDU RAFS generated models and cannot be avoided without renaming API fields.

4. **`from __future__ import annotations` must be removed from all generated models.** Without this removal, the field-name-shadowing issue recurs even with type aliases in place.

---

## 8. Things to Watch Carefully in Full Migration

1. **`Optional[T]` unwrapping** — In v2, `Optional[float]` is `Union[float, None]`, not bare `float`. Any code that checks `annotation is float` (like the float-column cast in `api.py`) must use `get_args(annotation)[0]` or `get_origin(annotation)`.

2. **`conlist` `min_items` → `min_length`** — `min_items` is silently ignored in v2; must be renamed to `min_length`.

3. **`Field(min_items=N)` → `Field(min_length=N)`** — Same rename for list length constraints.

4. **`__root__` → `RootModel[T]`** — 5 domain models use `__root__`. The `RootModel` serialization is compatible but the JSON Schema output differs.

5. **Error message casing** — `"field required"` (v1) → `"Field required"` (v2). Any test or code that compares against the exact string must use case-insensitive comparison.

6. **Validation error `url` field** — v2 adds a `url` field to each validation error dict. Tests that assert the exact error structure must account for this.

7. **`.schema()` vs `.model_json_schema()`** — The JSON Schema format changed: v2 uses `$defs` instead of `definitions`, and `Optional[T]` is encoded as `anyOf: [{"type": "null"}, <T>]`. The `build_normalized_schema_from_model` function and the filter system must be validated against v2 schema output.

8. **`pydantic[dotenv]` extra removed** — `requirements.in` must replace `pydantic[dotenv]==...` with `pydantic>=2.9,<3` + `pydantic-settings>=2.7,<3`.

---

## 9. Estimated Full Migration Effort

| Category | Files / Occurrences | Approach | Est. Effort |
|---|---|---|---|
| `requirements.in` | 1 | Manual | Trivial |
| `BaseSettings` migration | 7 app + 1 test | Manual | 0.5h |
| Settings subclass `class Config` cleanup | 3 files | Manual | 0.5h |
| `str = None` → `Optional[str] = None` | ~18 | Scripted | 1h |
| `RafsBaseModel` + `Extra.forbid` → `ConfigDict` | ~307 occurrences | Scripted | 1h |
| `constr(regex=)` → `Annotated[str, StringConstraints(pattern=)]` | ~589 occurrences | Scripted (careful) | 2h |
| `Field(const=True)` → `Literal[...]` | ~233 occurrences | Scripted | 1h |
| `Field(min_items=)` → `Field(min_length=)` | 33 | Scripted | 0.5h |
| `conlist` → `Annotated[List, Field]` | 3 | Manual | 0.5h |
| `conint` → `Annotated[int, Field]` | 1 | Manual | Trivial |
| `__root__` → `RootModel[T]` | 5 | Manual | 1h |
| `.dict()` → `.model_dump()` | ~12 app | Scripted | 0.5h |
| `.construct()` → `.model_construct()` | ~12 | Scripted | 0.5h |
| `.schema()` → `.model_json_schema()` + schema normalizer validation | ~8 app + 12 tests | Manual + testing | 3h |
| `parse_obj()` → `model_validate()` | 1 | Trivial | |
| `__fields__` / `field.type_` / `field_info.required` | 3 files | Manual | 2h |
| Error message casing | 2 app + 2 tests | Manual | 1h |
| `pydantic.main` imports | 3 | Scripted | 0.5h |
| `validate_all` → `validate_default` | 2 | Trivial | |
| Remove `from __future__ import annotations` from 102 models + add missing imports | 102 files | Scripted | 1h |
| Type alias fixes for field-name-class-name shadowing | ~52 files | Scripted | 2h |
| Update code generator for future regenerations | 1 | Research + config | 2h |
| Update test assertions (error message format) | ~5 test files | Manual | 1h |
| Validate JSON Schema normalizer / filter system with v2 output | 2 files | Manual + testing | 4h |
| Full test suite pass + CI green | — | Testing + fixes | 4h |
| **Total** | | | **~27–30h** |

---

## 10. Recommendation

**Proceed with the migration.** The pilot demonstrated:

- Migration is technically feasible with no fundamental blockers.
- 79% of tests pass after migrating the infrastructure and data schema layer.
- All remaining failures (21%) map to three well-scoped categories, none of which involve unknown behavior.
- Pydantic v2 is backward-compatible for most deprecated patterns (they emit warnings, not errors), which means the migration can be staged: fix hard errors first, then clean up deprecation warnings.

**Conditions before proceeding to full migration:**

1. Resolve the `datamodel-codegen` question — determine whether the generator can be configured to emit v2-compatible code, or document the post-generation script as a permanent step in the schema lifecycle.
2. Address the `.model_json_schema()` / filter system risk as a high-priority early step (Category J) — this is the one area where the behavior change is subtle and test coverage may be insufficient.

**Acceptance criteria (migration is "done" when ALL of these pass):**

- 1710 / 1710 tests passing (zero failures, zero collection errors)
- Zero `PydanticDeprecatedSince20` warnings in the test run output
- `python scripts/check_openapi_sync.py` passes (OpenAPI spec unchanged)
- CI pipeline green on `ci/integration` (code quality + unit test jobs)

**Estimated timeline:**

The 27–30h total effort fits into roughly two sprints if one developer is assigned:

- **Phase 1 (~8h):** Hard blockers only — requirements, `BaseSettings`, `Field(const=True)`, `constr`, `FieldInfo.type_` / `field_info.required`. Target: 100% tests collecting, hard errors eliminated.
- **Phase 2 (~20h):** Cleanup — deprecation warnings, JSON Schema normalizer validation, test assertion updates, OpenAPI sync verification, CI green.

---

## 11. Step-by-Step Guide for Full Migration

See [`agents/workspace/plans/pydantic-v2-migration-plan.md`](../../agents/workspace/plans/pydantic-v2-migration-plan.md) (in this branch, `feature/pydantic-v2-migration`) — "Full Migration Reference" section — for the complete ordered change list with before/after code snippets and test commands.

**Key additions from this spike (not in the original plan):**

1. **Step 0a (prerequisite):** Remove `from __future__ import annotations` from all generated model files (`app/models/data_schemas/*/`, `app/models/domain/`). Add missing `typing` imports as needed.

2. **Step 0b (prerequisite):** Add type aliases for ALL class-name-as-field-name patterns. Can be scripted: for each module, find classes whose names are also used as field annotation types in the same module, and insert `_NameModel = Name` aliases before the first class that uses them.

3. **Bundling requirement:** Steps 1 (requirements), 2 (BaseSettings), and 3 (RafsBaseModel + `str = None`) must be in the same commit. Any commit with pydantic v2 installed but v1 `BaseSettings` imports will be broken.

4. **Code generator — resolved:** `datamodel-codegen 0.53.0` (already installed in `.venv`) supports pydantic v2 output natively via `--output-model-type pydantic_v2.BaseModel`. See Section 12 for the exact changes to `scripts/model_generator.py`. No post-processing script is needed for future regenerations.

---

## 12. Code Generator Fix (datamodel-codegen)

### Answer

`datamodel-codegen` can be configured to emit v2-compatible code. **No permanent post-processing script is required.**

### Version

`0.53.0` (installed in `.venv`). Has had `pydantic_v2` model backend since ≥0.25.0.

### Changes to `scripts/model_generator.py`

**Add three flags to the `command` list:**

```python
"--output-model-type", "pydantic_v2.BaseModel",  # emit v2 model config, Literal, etc.
"--use-annotated",                                # emit Annotated[str, Field(pattern=)] instead of constr()
"--disable-future-imports",                       # do NOT emit "from __future__ import annotations"
```

**Update `_build_model_for_rafs`** — remove the `from __future__ import annotations` injection, keep only the `RafsBaseModel` substitution:

```python
# Before:
rafs_base_model_import = "from app.models.config import RafsBaseModel"
annotations_import = "from __future__ import annotations"
model = model.replace(annotations_import, f"{annotations_import}\n\n{rafs_base_model_import}")

# After:
rafs_import = "from app.models.config import RafsBaseModel"
model = model.replace("from pydantic import", f"{rafs_import}\n\nfrom pydantic import", 1)
```

This change was already applied in commit `22c3a066`.

### What the new generator emits (verified on RCA schema)

| Pattern | Old (v1) | New (v2) |
|---|---|---|
| `from __future__ import annotations` | ✅ emitted | ❌ not emitted |
| `class Config: extra = Extra.forbid` | emitted | `model_config = ConfigDict(extra="forbid")` |
| `constr(regex=r"...")` | emitted | `Annotated[str, Field(pattern=r"...")]` |
| `Field(const=True, default="Unit")` | emitted | `Literal["Unit"]` |
| `(constr(...) \| None)` | emitted | `Annotated[str \| None, Field(pattern=...)]` |
| `from pydantic import BaseModel` | included | excluded (replaced with `RafsBaseModel`) |

### Why `--disable-future-imports` eliminates the field-name-shadowing problem

Without `from __future__ import annotations`, Python evaluates type annotations **eagerly** at class-body time. When it processes `Conditions: Annotated[Conditions | None, Field(...)]`, the name `Conditions` is looked up in the module's global scope (where the class is already defined, since it appeared before the current class). There is no lazy evaluation and no namespace ambiguity — the type alias workaround is not needed for freshly generated models.

The type aliases (`_ConditionsModel = Conditions`, etc.) added during the migration are only needed for the **existing generated files** that still carry `from __future__ import annotations`. They can be cleaned up if those files are regenerated with the updated generator.
