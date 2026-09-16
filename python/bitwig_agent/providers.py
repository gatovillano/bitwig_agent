from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

import os
from typing import List, Tuple, Dict, Any, Optional
import httpx

from bitwig_agent.antigravity import AntigravityClient

PROVIDERS: List[Tuple[str, str, str]] = [
    ("google", "🤖 Google AI (Gemini 2.5 Pro / Flash)", "gemini/gemini-2.5-flash"),
    ("antigravity", "🛸 Google Antigravity (Dynamic Session OAuth2)", "antigravity/gemini-pro-agent"),
    ("kilocode", "⚡ KiloCode Gateway (Smart Routing / Auto)", "kilocode/kilo/auto"),
    ("anthropic", "🎭 Anthropic (Claude 3.7 Sonnet / Opus)", "claude-3-7-sonnet-20250219"),
    ("openai", "🧠 OpenAI (GPT-4o, o3-mini)", "gpt-4o"),
    ("openrouter", "🌐 OpenRouter (Catálogo multi-modelo)", "openrouter/anthropic/claude-3.7-sonnet"),
    ("groq", "⚡ Groq (Ultra-baja latencia / Llama 3.3)", "groq/llama-3.3-70b-versatile"),
    ("ollama", "🦙 Ollama Local (Ejecución local privada)", "ollama/llama3"),
]

PROVIDER_DEFAULT_MODELS: Dict[str, str] = {
    "google": "gemini/gemini-2.5-flash",
    "antigravity": "antigravity/gemini-pro-agent",
    "kilocode": "kilocode/kilo/auto",
    "anthropic": "claude-3-7-sonnet-20250219",
    "openai": "gpt-4o",
    "openrouter": "openrouter/anthropic/claude-3.7-sonnet",
    "groq": "groq/llama-3.3-70b-versatile",
    "ollama": "ollama/llama3",
}

PROVIDER_KEYS: Dict[str, List[str]] = {
    "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "antigravity": ["ANTIGRAVITY_TOKEN"],
    "kilocode": ["KILOCODE_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "ollama": ["OLLAMA_API_BASE"],
}

ALL_COMMON_KEYS: List[str] = [
    "GEMINI_API_KEY",
    "KILOCODE_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "OLLAMA_API_BASE",
]

FALLBACK_MODELS: Dict[str, List[Tuple[str, str]]] = {
    "google": [
        ("gemini/gemini-2.5-flash", "Gemini 2.5 Flash (Recomendado, rápido y capaz)"),
        ("gemini/gemini-2.5-pro", "Gemini 2.5 Pro (Máximo razonamiento musical)"),
        ("gemini/gemini-2.0-flash", "Gemini 2.0 Flash"),
        ("gemini/gemini-1.5-pro", "Gemini 1.5 Pro"),
        ("gemini/gemini-1.5-flash", "Gemini 1.5 Flash"),
    ],
    "antigravity": [
        ("antigravity/gemini-pro-agent", "Gemini 3.1 Pro (High) (Antigravity Agent)"),
        ("antigravity/gemini-3-flash", "Gemini 3 Flash (Antigravity)"),
        ("antigravity/gemini-3-pro", "Gemini 3 Pro (Antigravity)"),
        ("antigravity/gemini-2.5-flash", "Gemini 2.5 Flash (Antigravity)"),
        ("antigravity/gemini-2.5-pro", "Gemini 2.5 Pro (Antigravity)"),
    ],
    "kilocode": [
        ("kilocode/kilo/auto", "Kilo Auto (Smart Routing)"),
        ("kilocode/anthropic/claude-3-7-sonnet", "Claude 3.7 Sonnet via Kilo"),
        ("kilocode/openai/gpt-4o", "GPT-4o via Kilo"),
        ("kilocode/google/gemini-2.5-pro", "Gemini 2.5 Pro via Kilo"),
        ("kilocode/deepseek/deepseek-r1", "DeepSeek R1 via Kilo"),
    ],
    "anthropic": [
        ("claude-3-7-sonnet-20250219", "Claude 3.7 Sonnet (Híbrido pensamiento/código)"),
        ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet v2"),
        ("claude-3-5-haiku-20241022", "Claude 3.5 Haiku (Rápido y ligero)"),
        ("claude-3-opus-20240229", "Claude 3 Opus"),
    ],
    "openai": [
        ("gpt-4o", "GPT-4o (Omni multimodal de alta inteligencia)"),
        ("gpt-4o-mini", "GPT-4o Mini (Económico y veloz)"),
        ("o3-mini", "o3-mini (Razonamiento lógico avanzado)"),
        ("o1", "o1 (Razonamiento profundo)"),
        ("gpt-4-turbo", "GPT-4 Turbo"),
    ],
    "openrouter": [
        ("openrouter/anthropic/claude-3.7-sonnet", "Claude 3.7 Sonnet via OpenRouter"),
        ("openrouter/google/gemini-2.5-flash", "Gemini 2.5 Flash via OpenRouter"),
        ("openrouter/openai/gpt-4o", "GPT-4o via OpenRouter"),
        ("openrouter/meta-llama/llama-3.3-70b-instruct", "Llama 3.3 70B Instruct"),
        ("openrouter/deepseek/deepseek-chat", "DeepSeek V3"),
        ("openrouter/deepseek/deepseek-r1", "DeepSeek R1 (Razonamiento)"),
    ],
    "groq": [
        ("groq/llama-3.3-70b-versatile", "Llama 3.3 70B Versatile (128k ctx)"),
        ("groq/llama-3.1-8b-instant", "Llama 3.1 8B Instant (Ultra-rápido)"),
        ("groq/mixtral-8x7b-32768", "Mixtral 8x7B (32k ctx)"),
        ("groq/gemma2-9b-it", "Gemma 2 9B Instruct"),
    ],
    "ollama": [
        ("ollama/llama3", "Llama 3 (Local)"),
        ("ollama/llama3.2", "Llama 3.2 (Local ligero)"),
        ("ollama/mistral", "Mistral 7B (Local)"),
        ("ollama/qwen2.5-coder", "Qwen 2.5 Coder (Local)"),
        ("ollama/deepseek-r1", "DeepSeek R1 (Local)"),
    ],
}

def get_provider_key(provider: str) -> Optional[str]:
    if provider == "antigravity":
        return "OAuth-Session" if AntigravityClient.is_logged_in() else None
    keys = PROVIDER_KEYS.get(provider, [])
    for k in keys:
        v = os.getenv(k)
        if v:
            return v
    return None

def fetch_google_models(api_key: Optional[str] = None) -> List[Tuple[str, str]]:
    key = api_key or get_provider_key("google")
    if not key:
        return FALLBACK_MODELS["google"]
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("models", []):
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        m_id = m["name"].replace("models/", "gemini/")
                        name = m.get("displayName", m["name"].split("/")[-1])
                        models.append((m_id, f"{name} ({m_id})"))
                if models:
                    models.sort(key=lambda x: x[0], reverse=True)
                    return models
    except Exception:
        pass
    return FALLBACK_MODELS["google"]

def fetch_antigravity_models() -> List[Tuple[str, str]]:
    return AntigravityClient.fetch_available_models()

def fetch_kilocode_models(api_key: Optional[str] = None) -> List[Tuple[str, str]]:
    key = api_key or get_provider_key("kilocode")
    if not key:
        return FALLBACK_MODELS["kilocode"]
    try:
        headers = {"Authorization": f"Bearer {key}"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get("https://api.kilo.ai/api/gateway/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                model_list = data if isinstance(data, list) else data.get("models", data.get("data", []))
                models = []
                for m in model_list:
                    m_id = m.get("id", m.get("model", ""))
                    if not m_id:
                        continue
                    if not m_id.startswith("kilocode/"):
                        m_id = f"kilocode/{m_id}"
                    name = m.get("name", m_id)
                    pricing = m.get("pricing", {})
                    p_str = ""
                    if pricing and pricing.get("prompt"):
                        try:
                            prompt_cost = float(pricing.get("prompt", 0)) * 1_000_000
                            p_str = f" [${prompt_cost:.2f}/M in]"
                        except Exception:
                            pass
                    ctx = m.get("context_length", m.get("context", 0))
                    ctx_str = f" ({int(ctx/1024)}k ctx)" if ctx else ""
                    models.append((m_id, f"{name}{ctx_str}{p_str}"))
                if models:
                    models.sort(key=lambda x: x[1])
                    return models
    except Exception:
        pass
    return FALLBACK_MODELS["kilocode"]

def fetch_openrouter_models() -> List[Tuple[str, str]]:
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get("https://openrouter.ai/api/v1/models")
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("data", []):
                    m_id = f"openrouter/{m['id']}"
                    name = m.get("name", m["id"])
                    ctx = m.get("context_length", 0)
                    ctx_str = f" ({int(ctx/1024)}k ctx)" if ctx else ""
                    pricing = m.get("pricing", {})
                    p_str = ""
                    if pricing and pricing.get("prompt"):
                        try:
                            prompt_cost = float(pricing.get("prompt", 0)) * 1_000_000
                            p_str = f" [${prompt_cost:.2f}/M in]"
                        except Exception:
                            pass
                    label = f"{name}{ctx_str}{p_str}"
                    models.append((m_id, label))
                if models:
                    models.sort(key=lambda x: x[1])
                    return models
    except Exception:
        pass
    return FALLBACK_MODELS["openrouter"]

def fetch_openai_models(api_key: Optional[str] = None) -> List[Tuple[str, str]]:
    key = api_key or get_provider_key("openai")
    if not key:
        return FALLBACK_MODELS["openai"]
    try:
        headers = {"Authorization": f"Bearer {key}"}
        with httpx.Client(timeout=8.0) as client:
            resp = client.get("https://api.openai.com/v1/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("data", []):
                    m_id = m.get("id", "")
                    if any(k in m_id for k in ("gpt-", "o1", "o3", "chatgpt")):
                        models.append((m_id, f"{m_id}"))
                if models:
                    models.sort(key=lambda x: x[0], reverse=True)
                    return models
    except Exception:
        pass
    return FALLBACK_MODELS["openai"]

def fetch_anthropic_models(api_key: Optional[str] = None) -> List[Tuple[str, str]]:
    key = api_key or get_provider_key("anthropic")
    if not key:
        return FALLBACK_MODELS["anthropic"]
    try:
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01"
        }
        with httpx.Client(timeout=8.0) as client:
            resp = client.get("https://api.anthropic.com/v1/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("data", []):
                    m_id = m.get("id", "")
                    name = m.get("display_name", m_id)
                    models.append((m_id, f"{name} ({m_id})"))
                if models:
                    models.sort(key=lambda x: x[0], reverse=True)
                    return models
    except Exception:
        pass
    return FALLBACK_MODELS["anthropic"]

def fetch_groq_models(api_key: Optional[str] = None) -> List[Tuple[str, str]]:
    key = api_key or get_provider_key("groq")
    if not key:
        return FALLBACK_MODELS["groq"]
    try:
        headers = {"Authorization": f"Bearer {key}"}
        with httpx.Client(timeout=8.0) as client:
            resp = client.get("https://api.groq.com/openai/v1/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("data", []):
                    m_id = f"groq/{m.get('id', '')}"
                    models.append((m_id, m.get("id", "")))
                if models:
                    models.sort(key=lambda x: x[1])
                    return models
    except Exception:
        pass
    return FALLBACK_MODELS["groq"]

def fetch_ollama_models(api_base: Optional[str] = None) -> List[Tuple[str, str]]:
    base = api_base or os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    base = base.rstrip("/").replace("/v1", "")
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{base}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("models", []):
                    name = m.get("name", "")
                    if name:
                        size = m.get("size", 0)
                        size_str = f" ({size / (1024**3):.1f} GB)" if size else ""
                        models.append((f"ollama/{name}", f"{name}{size_str}"))
                if models:
                    models.sort(key=lambda x: x[1])
                    return models
    except Exception:
        pass
    return FALLBACK_MODELS["ollama"]

def fetch_models_for_provider(provider: str) -> List[Tuple[str, str]]:
    if provider == "google":
        return fetch_google_models()
    elif provider == "antigravity":
        return fetch_antigravity_models()
    elif provider == "kilocode":
        return fetch_kilocode_models()
    elif provider == "openrouter":
        return fetch_openrouter_models()
    elif provider == "openai":
        return fetch_openai_models()
    elif provider == "anthropic":
        return fetch_anthropic_models()
    elif provider == "groq":
        return fetch_groq_models()
    elif provider == "ollama":
        return fetch_ollama_models()
    return []
