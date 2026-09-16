import os
import pytest
from bitwig_agent.config import (
    load_config,
    save_config,
    get_active_provider,
    set_active_provider,
    get_active_model,
    set_active_model,
    mask_secret,
    save_env_var,
    remove_env_var,
)
from bitwig_agent.providers import (
    PROVIDERS,
    fetch_models_for_provider,
    FALLBACK_MODELS,
    get_provider_key,
)

def test_mask_secret():
    assert mask_secret("") == ""
    assert mask_secret("short") == "****"
    assert mask_secret("AIzaSy123456789xyz") == "AIza...9xyz"

def test_config_provider_model(tmp_path, monkeypatch):
    test_cfg = tmp_path / "config.json"
    monkeypatch.setattr("bitwig_agent.config.CONFIG_FILE", test_cfg)
    monkeypatch.setattr("bitwig_agent.config.CONFIG_DIR", tmp_path)

    set_active_provider("anthropic")
    assert get_active_provider() == "anthropic"

    set_active_model("claude-3-7-sonnet-20250219")
    assert get_active_model() == "claude-3-7-sonnet-20250219"

def test_fetch_models_fallback():
    models = fetch_models_for_provider("anthropic")
    assert len(models) > 0
    assert any("claude-3-7-sonnet" in m[0] for m in models)

    google_models = fetch_models_for_provider("google")
    assert len(google_models) > 0
    assert any("gemini-2.5-flash" in m[0] for m in google_models)
