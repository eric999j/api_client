# Skill: Add HTTP Feature

Guided workflow for adding a new HTTP-related feature to the API Client Enterprise Edition.
This skill ensures all architectural layers are updated consistently and the graceful degradation pattern is preserved.

## When to Use

- Adding a new HTTP method, request option, or response handling capability
- Extending `HttpRequest` / `HttpResponse` dataclasses
- Adding new config options that affect HTTP behavior (SSL, proxy, auth, etc.)
- Adding new exception types for HTTP error scenarios

## Pre-Flight

1. Read [AGENTS.md](../../../AGENTS.md) for architecture overview and critical patterns.
2. Identify which layers the feature touches — most HTTP features span **all four layers**:

| Layer | File | What to change |
|-------|------|----------------|
| Core data | `core/http_client.py` | `HttpRequest` / `HttpResponse` dataclass fields, `HttpClient` logic |
| Exceptions | `core/exceptions.py` | New exception subclass if the feature introduces a new failure mode |
| Config | `config/settings.py` | `AppConfig` field + `Environment` field (if per-env) |
| Orchestrator | `logic.py` | Wire config → request in both `send_request_new()` AND `send_request()` |
| GUI | `main.py` | UI control + pass value through to orchestrator |
| Utils | `utils.py` | Validation or formatting helpers (only if needed) |

## Step-by-Step Workflow

### Step 1 — Define the data model change

Add fields to the appropriate dataclass in `core/http_client.py`:

```python
@dataclass
class HttpRequest:
    # ... existing fields ...
    new_option: bool = False          # always provide a safe default
```

- Use `Optional[T] = None` for nullable fields, concrete defaults for required ones.
- If the field needs validation, add checks inside `HttpRequest.validate()`.

### Step 2 — Add exception type (if needed)

If the feature introduces a new failure mode, add a subclass in `core/exceptions.py`:

```python
class NewFeatureError(ApiClientError):
    def __init__(self, message: str, detail_field: str = None, **kwargs):
        super().__init__(message, error_code="NEW_FEATURE_ERROR", **kwargs)
        self.detail_field = detail_field
```

Rules:
- Inherit from `ApiClientError` (or a more specific parent like `RequestError`).
- Always set a unique `error_code` string.
- Add contextual attributes (similar to `TimeoutError.timeout_seconds`, `SSLError.cert_info`).
- Import the new exception in `core/http_client.py` and catch the corresponding `requests` exception in `HttpClient._execute_request()`.

### Step 3 — Add config support

In `config/settings.py`:

```python
@dataclass
class AppConfig:
    # ... existing fields ...
    new_option: bool = False           # safe default matching HttpRequest default
```

If the setting should be overridable per environment, also update `Environment` and the serialization in `ConfigManager._save_config()` / `_load_config()`.

Add env-var override in `ConfigManager.__init__()` following the pattern:
```python
env_value = os.environ.get('API_CLIENT_NEW_OPTION')
if env_value is not None:
    self.app_config.new_option = env_value.lower() in ('true', '1', 'yes')
```

Config precedence: **env var > config file > dataclass default**.

### Step 4 — Wire through the orchestrator

In `logic.py`, update **both** request paths:

**`send_request_new()` (new architecture):**
```python
request = HttpRequest(
    # ... existing args ...
    new_option=config.new_option,     # read from config
)
```

**`send_request()` (legacy fallback):**
```python
# Only use new feature if enterprise mode available
if NEW_ARCHITECTURE_AVAILABLE:
    new_option_value = config_manager.app_config.new_option
```

**Critical**: Both paths must remain functional. The legacy `send_request()` must work even when `core/` modules are unavailable — guard with `if NEW_ARCHITECTURE_AVAILABLE`.

### Step 5 — Add GUI controls

In `main.py`, add the UI element inside `create_widgets()`:

```python
self.new_option_var = tk.BooleanVar(value=False)
# ... create checkbox/entry/dropdown ...
```

Pass the value when calling the orchestrator in `run_request()`:

```python
# Read from UI
new_option = self.new_option_var.get()
```

UI rules:
- **Thread safety**: `run_request()` runs on a daemon thread. Extract all Tkinter variable values **before** starting the thread, or inside `on_send()` on the main thread. Never call `.get()` on a `tk.*Var` from a background thread.
- **Theme support**: Any new widget must be styled in `apply_theme()` for both light and dark modes.
- **Widget order**: `apply_theme()` is called after `create_widgets()` — add new widgets before that call.

### Step 6 — Add logging

Log the new feature's usage in `HttpClient.send()` or `_execute_request()`:

```python
logger.info(
    f"Feature enabled [{request_id}]: new_option={request.new_option}",
    extra={
        'request_id': request_id,
        'new_option': request.new_option,
    }
)
```

Use structured `extra` fields for JSON log output.

## Checklist

Before considering the feature complete, verify:

- [ ] **Safe defaults**: New fields have defaults that preserve existing behavior
- [ ] **Validation**: Invalid values caught in `HttpRequest.validate()` with `ValidationError`
- [ ] **Graceful degradation**: Feature guarded by `NEW_ARCHITECTURE_AVAILABLE` / `ENTERPRISE_MODE` flags in `logic.py` and `main.py`
- [ ] **Both paths updated**: `send_request_new()` AND `send_request()` in `logic.py` handle the feature
- [ ] **Config persistence**: New `AppConfig` fields serialize/deserialize correctly in `~/.api_client/config.json`
- [ ] **Env var override**: `API_CLIENT_<OPTION>` env var respected if applicable
- [ ] **Thread safety**: No Tkinter `.get()` / widget modification from background threads
- [ ] **Theme applied**: New widgets styled in `apply_theme()` for both modes
- [ ] **Logging**: Feature usage logged with structured fields
- [ ] **Exception hierarchy**: New failure modes have a dedicated exception with `error_code` and `to_dict()`

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Forgot to update legacy `send_request()` | Always grep for both `send_request_new` and `send_request` in `logic.py` |
| Tkinter crash on background thread | Extract all UI values in `on_send()` before `threading.Thread(...)` |
| Config not loading on restart | Ensure field is in both `_save_config()` dict and `_load_config()` parsing |
| New widget unstyled in dark mode | Add widget to the correct section of `apply_theme()` |
| Import breaks when `core/` missing | Test by temporarily renaming `core/` folder — app should still launch in basic mode |
