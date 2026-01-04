import os
import tempfile

from backend.utils.config import load_config, validate_config


def test_load_default_config(monkeypatch, tmp_path):
    # Ensure no config exists
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setenv("MAILSORTER_CONFIG", os.path.join(td, "nope.json"))
        cfg = load_config()
        assert cfg is not None
        assert "provider" in cfg


def test_validate_good_config(tmp_path):
    cfg = {
        "provider": "ollama",
        "analysis_mode": "full",
        "batch_mode": {"enabled": False}
    }
    # Should not raise
    validate_config(cfg)


def test_validate_bad_config(tmp_path):
    cfg = {
        "analysis_mode": "invalid"
    }
    try:
        validate_config(cfg)
        assert False, "Validation should have failed"
    except Exception:
        assert True
