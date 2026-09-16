from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import find_dotenv, set_key, unset_key

CONFIG_DIR = Path.home() / ".config" / "bitwig_agent"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "provider": "google",
    "model": "gemini/gemini-2.5-flash",
    "custom_models": []
}

def ensure_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR

def load_config() -> Dict[str, Any]:
    ensure_config_dir()
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**DEFAULT_CONFIG, **data}
    except Exception:
        return dict(DEFAULT_CONFIG)

def save_config(cfg: Dict[str, Any]) -> None:
    ensure_config_dir()
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def get_active_provider() -> str:
    cfg = load_config()
    return cfg.get("provider", "google")

def set_active_provider(provider: str) -> None:
    cfg = load_config()
    cfg["provider"] = provider
    save_config(cfg)

def get_active_model() -> str:
    env_model = os.getenv("BITWIG_LLM_MODEL")
    if env_model:
        return env_model
    cfg = load_config()
    return cfg.get("model", "gemini/gemini-2.5-flash")

def set_active_model(model: str) -> None:
    cfg = load_config()
    cfg["model"] = model
    save_config(cfg)
    os.environ["BITWIG_LLM_MODEL"] = model
    save_env_var("BITWIG_LLM_MODEL", model)

def get_env_file_path() -> str:
    dotenv_path = find_dotenv(usecwd=True)
    if not dotenv_path:
        dotenv_path = os.path.join(os.getcwd(), ".env")
        if not os.path.exists(dotenv_path):
            try:
                with open(dotenv_path, "w", encoding="utf-8") as f:
                    f.write("# Bitwig Agent Environment Variables\n")
            except Exception:
                pass
    return dotenv_path

def save_env_var(key: str, value: str) -> bool:
    os.environ[key] = value
    env_path = get_env_file_path()
    try:
        set_key(env_path, key, value)
        return True
    except Exception:
        return False

def remove_env_var(key: str) -> bool:
    if key in os.environ:
        del os.environ[key]
    env_path = get_env_file_path()
    try:
        unset_key(env_path, key)
        return True
    except Exception:
        return False

def mask_secret(val: Optional[str]) -> str:
    if not val:
        return ""
    val = val.strip()
    if len(val) <= 8:
        return "****"
    return f"{val[:4]}...{val[-4:]}"
