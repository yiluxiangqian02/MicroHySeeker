# Dual Configuration System

AutoHySeeker uses two complementary configuration systems that serve different purposes.

## Overview

| Aspect | `src/common/config.py` | `src/configs.py` |
|---|---|---|
| Source | Environment variables / `.env` | TOML files in `configs/` |
| Format | Flat constants | Typed dataclass hierarchy |
| Access | Direct import | Lazy singleton accessors |
| Primary use | Runtime LLM client, API server | Structured app settings, file paths |

---

## System 1 — `src/common/config.py` (Environment-based)

Loads settings from the process environment (`.env` is auto-loaded via `python-dotenv`).

### Constants exported

```python
from src.common.config import (
    OPENAI_BASE_URL,        # str  — LLM proxy URL
    OPENAI_API_KEY,         # str  — secret key (empty if unset)
    DEFAULT_MODEL,          # str  — e.g. "anthropic/claude-sonnet-4-6"
    FALLBACK_MODEL,         # str  — e.g. "anthropic/claude-opus-4-6"
    DATA_ROOT,              # Path — resolved absolute path to data directory
    LOG_ROOT,               # Path — resolved absolute path to logs directory
    API_HOST,               # str  — FastAPI bind host (default "0.0.0.0")
    API_PORT,               # int  — FastAPI port (default 8100)
    OPENAI_TIMEOUT_SECONDS, # float — request timeout
)
```

### Setting values

Create a `.env` file in the project root (copy from `.env.example`):

```dotenv
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.mcxhm.cn
DEFAULT_MODEL=anthropic/claude-sonnet-4-6
FALLBACK_MODEL=anthropic/claude-opus-4-6
DATA_ROOT=../data
LOG_ROOT=./logs
API_HOST=0.0.0.0
API_PORT=8100
OPENAI_TIMEOUT_SECONDS=60
```

Relative paths (`DATA_ROOT`, `LOG_ROOT`) are resolved relative to the project root.

---

## System 2 — `src/configs.py` (TOML-based)

Loads typed configuration from TOML files in the `configs/` directory.  
Values are exposed through lazy singleton accessors that parse files once on first access.

### TOML files

| File | Dataclass | Accessor |
|---|---|---|
| `configs/settings.toml` | `Settings` | `get_settings()` |
| `configs/llm_config.toml` | `LLMConfig` | `get_llm_config()` |
| `configs/microhyseeker.toml` | `MicroHySeekerConfig` | `get_microhyseeker_config()` |

### Usage

```python
from src.configs import get_settings, get_llm_config, get_microhyseeker_config

s = get_settings()
print(s.general.project_name)   # "AutoHySeeker"
print(s.api.port)               # 8100

llm = get_llm_config()
print(llm.default.model)        # "anthropic/claude-sonnet-4-6"
print(llm.fallback.model)       # "anthropic/claude-opus-4-6"

mhs = get_microhyseeker_config()
print(mhs.engine.mode)          # "file"
print(mhs.paths.data_dir)       # resolved absolute path
```

### Path interpolation in TOML

`microhyseeker.toml` supports `${VAR:-default}` syntax for environment variable expansion:

```toml
[paths]
data_dir  = "${DATA_ROOT:-../data}"
logs_dir  = "${LOG_ROOT:-./logs}"
```

`_expand_path()` in `src/configs.py` expands env vars and resolves relative paths to the
`AutoHySeeker/` root (the parent of `configs/`).

---

## How the two systems interact

- **`llm_client.py`** reads `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `DEFAULT_MODEL`,
  `FALLBACK_MODEL`, `OPENAI_TIMEOUT_SECONDS` from **System 1** (`src/common/config.py`).
- **`src/configs.py`** is used by higher-level code that needs structured project settings
  (API host/port, LLM model details, file paths to `data/` and `logs/`).
- Both systems can coexist: System 1 is consumed at import time; System 2 singletons are
  initialised lazily on first access.

### Priority

For any setting that appears in both systems, the environment variable (System 1) takes
precedence at runtime because `src/common/config.py` reads from `os.environ` directly,
while `src/configs.py` only reads TOML files (it does not merge env vars except for path
expansion in `microhyseeker.toml`).

---

## Testing tips

- To override System 1 constants in tests, use `unittest.mock.patch`:
  ```python
  with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"):
      ...
  ```
- To override System 2 singletons, reset the module-level cache before the test:
  ```python
  import src.configs as cfg
  cfg._settings = None  # force reload on next get_settings() call
  ```
