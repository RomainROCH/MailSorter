import os
import json
from typing import Any, Dict, Optional

from .logger import logger

"""
Simple configuration loader for MailSorter (Plan V5).

Behavior:
- Looks for config path in env var `MAILSORTER_CONFIG`.
- Falls back to `backend/config.json` next to the package.
- If not found, attempts to load `backend/config.json.example` and uses conservative defaults.

TODO: Add JSON Schema validation (jsonschema) and stricter secret handling.
TODO: Consider merging with platform-specific config (XDG paths).
"""

_DEFAULT_CONFIG = {
    "provider": "ollama",
    "providers": {"ollama": {"base_url": "http://localhost:11434", "model": "llama3"}},
    "analysis_mode": "full",
    "thresholds": {},
    "log_level": "INFO",
    "batch_mode": {"enabled": False},
}

_config_cache: Dict[str, Any] = {}


def _default_config_path() -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_dir, "config.json")


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from JSON with sensible fallbacks.

    Returns a dictionary with configuration values. Raises FileNotFoundError only
    if no config nor example exists and defaults are explicitly disabled by user.
    """
    global _config_cache
    if _config_cache:
        return _config_cache

    env_path = os.environ.get("MAILSORTER_CONFIG")
    candidates = []
    if path:
        candidates.append(path)
    if env_path:
        candidates.append(env_path)
    candidates.append(_default_config_path())
    candidates.append(
        os.path.join(os.path.dirname(__file__), "..", "config.json.example")
    )

    for p in candidates:
        try:
            p_abs = os.path.abspath(p)
            if not os.path.exists(p_abs):
                continue
            with open(p_abs, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            validate_config(cfg)
            _config_cache = cfg
            logger.info(f"Configuration loaded from {p_abs}")
            return cfg
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file {p}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Failed to load config {p}: {e}")
            continue

    # No valid config found; return defaults but log warning
    logger.warning(
        "No config found; using default conservative configuration. Create 'backend/config.json' to customize."
    )
    _config_cache = _DEFAULT_CONFIG.copy()
    return _config_cache


def validate_config(cfg: Dict[str, Any]) -> None:
    """Validate configuration using a JSON Schema.

    This uses the schema defined in `backend/json_schema/config.schema.json`.
    Raises jsonschema.ValidationError on invalid configs.

    TODO: Cache schema loading for performance.
    """
    from jsonschema import ValidationError, validate

    if not isinstance(cfg, dict):
        raise ValueError("Configuration must be a JSON object/dict")

    # Load schema from package data
    schema_data = None
    schema_path = os.path.join(
        os.path.dirname(__file__), "..", "json_schema", "config.schema.json"
    )
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_data = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load config schema for validation: {e}")
        # Fallback to minimal checks
        if "provider" not in cfg:
            raise ValueError("Configuration missing required key: 'provider'")
        return

    try:
        validate(instance=cfg, schema=schema_data)
    except ValidationError:
        # Re-raise with clearer message
        raise


if __name__ == "__main__":
    # Simple CLI for debugging
    cfg = load_config()
    print(json.dumps(cfg, indent=2))
import os
import json
from typing import Any, Dict, Optional

from .logger import logger

"""
Simple configuration loader for MailSorter (Plan V5).

Behavior:
- Looks for config path in env var `MAILSORTER_CONFIG`.
- Falls back to `backend/config.json` next to the package.
- If not found, attempts to load `backend/config.json.example` and uses conservative defaults.

TODO: Add JSON Schema validation (jsonschema) and stricter secret handling.
TODO: Consider merging with platform-specific config (XDG paths).
"""

_DEFAULT_CONFIG = {
    "provider": "ollama",
    "providers": {"ollama": {"base_url": "http://localhost:11434", "model": "llama3"}},
    "analysis_mode": "full",
    "thresholds": {},
    "log_level": "INFO",
    "batch_mode": {"enabled": False},
}

_config_cache: Dict[str, Any] = {}


def _default_config_path() -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_dir, "config.json")


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from JSON with sensible fallbacks.

    Returns a dictionary with configuration values. Raises FileNotFoundError only
    if no config nor example exists and defaults are explicitly disabled by user.
    """
    global _config_cache
    if _config_cache:
        return _config_cache

    env_path = os.environ.get("MAILSORTER_CONFIG")
    candidates = []
    if path:
        candidates.append(path)
    if env_path:
        candidates.append(env_path)
    candidates.append(_default_config_path())
    candidates.append(
        os.path.join(os.path.dirname(__file__), "..", "config.json.example")
    )

    for p in candidates:
        try:
            p_abs = os.path.abspath(p)
            if not os.path.exists(p_abs):
                continue
            with open(p_abs, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            validate_config(cfg)
            _config_cache = cfg
            logger.info(f"Configuration loaded from {p_abs}")
            return cfg
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file {p}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Failed to load config {p}: {e}")
            continue

    # No valid config found; return defaults but log warning
    logger.warning(
        "No config found; using default conservative configuration. Create 'backend/config.json' to customize."
    )
    _config_cache = _DEFAULT_CONFIG.copy()
    return _config_cache


def validate_config(cfg: Dict[str, Any]) -> None:
    """Validate configuration using a JSON Schema.

    This uses the schema defined in `backend/json_schema/config.schema.json`.
    Raises jsonschema.ValidationError on invalid configs.

    TODO: Cache schema loading for performance.
    """
    from jsonschema import ValidationError, validate

    if not isinstance(cfg, dict):
        raise ValueError("Configuration must be a JSON object/dict")

    # Load schema from package data
    schema_data = None
    schema_path = os.path.join(
        os.path.dirname(__file__), "..", "json_schema", "config.schema.json"
    )
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_data = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load config schema for validation: {e}")
        # Fallback to minimal checks
        if "provider" not in cfg:
            raise ValueError("Configuration missing required key: 'provider'")
        return

    try:
        validate(instance=cfg, schema=schema_data)
    except ValidationError:
        # Re-raise with clearer message
        raise


if __name__ == "__main__":
    # Simple CLI for debugging
    cfg = load_config()
    print(json.dumps(cfg, indent=2))
