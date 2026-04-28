# AGENTS.md — API Client Enterprise Edition

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

**Python 3.9+** required. Only external dependency is `requests>=2.28.0`. GUI uses `tkinter` (bundled with Python).

## Architecture

Layered architecture — **GUI → Orchestrator → Core → Config**:

| Layer | File | Key Class | Responsibility |
|-------|------|-----------|----------------|
| GUI | `main.py` | `ApiClientApp` | Tkinter UI, event handling, history |
| Logic | `logic.py` | `ApiClientOrchestrator` | Coordinates HTTP requests, applies auth/config |
| HTTP | `core/http_client.py` | `HttpClient`, `HttpRequest`, `HttpResponse` | Request execution, retry, SSL, proxy |
| Logging | `core/logger.py` | `JsonFormatter`, `ConsoleFormatter` | Structured JSON + colored console logging |
| Errors | `core/exceptions.py` | `ApiClientError` hierarchy | Typed exceptions with `.to_dict()` |
| Config | `config/settings.py` | `ConfigManager` (Singleton) | App + environment config, persisted to `~/.api_client/` |
| Utils | `utils.py` | — | JSON formatting, URL/header validation |

See [README.md](README.md) for feature details and usage instructions.

## Critical Patterns

### Graceful Degradation via Conditional Imports

Enterprise modules (`core/`, `config/`) are conditionally imported. If unavailable, the app falls back to basic `requests` usage:

```python
try:
    from core.http_client import HttpClient
    NEW_ARCHITECTURE_AVAILABLE = True
except ImportError:
    NEW_ARCHITECTURE_AVAILABLE = False
```

**Always check the feature flag** (e.g., `NEW_ARCHITECTURE_AVAILABLE`, `ENTERPRISE_MODE`) before using enterprise components.

### Thread-Safe UI Updates

Background HTTP requests run on daemon threads. **Never modify Tkinter widgets from a non-main thread** — always use `self.root.after(0, callback, ...)`.

### Config Precedence

Environment variables > config file (`~/.api_client/config.json`) > dataclass defaults.  
Env var override pattern: `API_CLIENT_TIMEOUT`, `API_CLIENT_LOG_LEVEL`, etc.

### URL Resolution Order

1. Variable substitution (`{{variable_name}}` → value)
2. Base URL prepended if path is relative

### Auth Header Priority

Environment default headers are applied first (without overwriting existing), then auth headers are applied with `dict.update()` — **auth always wins**.

## Conventions

- **Classes**: PascalCase — `ApiClientApp`, `HttpRequest`
- **Functions/methods**: snake_case — `on_send()`, `format_json()`
- **Constants**: UPPER_SNAKE_CASE — `MAX_SYNTAX_HIGHLIGHT_CHARS`
- **Dataclasses** for data containers (`HttpRequest`, `HttpResponse`, `AppConfig`, `Environment`)
- **Singleton** for `ConfigManager` (module-level `config_manager` instance)
- **Custom exception hierarchy** rooted at `ApiClientError` — each has `error_code` and `details`
- **Logging**: JSON to file (rotating, 10MB×5), colored text to console

## Known Constraints

- Syntax highlighting disabled for responses > 120KB (`MAX_SYNTAX_HIGHLIGHT_CHARS`)
- History deduplication uses exact 4-tuple match: `(method, url, headers, body)`
- `apply_theme()` must be called **after** all widgets are created
- No async HTTP support yet (sync `requests` only)
- No test suite exists — be careful with refactoring
