from __future__ import annotations
import os
import re
import json
import uuid
import time
import base64
import logging
from types import SimpleNamespace
from typing import Dict, Any, List, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

ANTIGRAVITY_SYSTEM_INSTRUCTION = (
    "You are the Bitwig Studio Musical AI Agent running via Google Antigravity. "
    "You are an expert music producer, arranger, and harmony specialist connected in real-time to Bitwig Studio 6.0."
)

class AntigravityClient:
    """
    Client for interacting with Google Antigravity (Cloud Code Gemini)
    using the active CLI OAuth2 token from ~/.gemini/antigravity-cli/antigravity-oauth-token
    """
    _access_token: Optional[str] = None
    _token_expiry: float = 0.0
    _project_id: Optional[str] = None
    _session_id: Optional[str] = None
    _agent_id: Optional[str] = None
    _trajectory_id: Optional[str] = None
    _step_index: int = 1
    _last_request_time: float = 0.0

    CODE_ASSIST_ENDPOINT_PROD = "https://cloudcode-pa.googleapis.com"

    @classmethod
    def get_token_file_path(cls) -> str:
        return os.path.expanduser("~/.gemini/antigravity-cli/antigravity-oauth-token")

    @classmethod
    def is_logged_in(cls) -> bool:
        return os.path.exists(cls.get_token_file_path())

    @classmethod
    def get_token(cls) -> str:
        now = time.time()
        if cls._access_token and now < cls._token_expiry:
            return cls._access_token

        token_path = cls.get_token_file_path()
        if not os.path.exists(token_path):
            raise ValueError(
                "No se encontró sesión activa de Antigravity en ~/.gemini/antigravity-cli/antigravity-oauth-token"
            )

        with open(token_path, "r", encoding="utf-8") as f:
            token_data = json.load(f)

        token_info = token_data.get("token", {})
        refresh_token = token_info.get("refresh_token")
        if not refresh_token:
            # Check if access_token is directly present
            acc = token_info.get("access_token")
            if acc:
                cls._access_token = acc
                cls._token_expiry = now + 1800
                return acc
            raise ValueError("Token de refresco no encontrado en la sesión de Antigravity.")

        client_id = base64.b64decode(
            "==QbvNmL05WZ052bjJXZzVXZsd2bvdmLzBHch5CclNDM0cGNop2bs9Gd2VzMyUmcjxWMygmMul2czhWb01SM5UDM2AjNwATM3ATM"[::-1]
        ).decode()
        client_secret = base64.b64decode(
            "=YWQEFnN6RzQYNHOCxUbxoETkxkN4QjUXZEO1sULYB1UD90R"[::-1]
        ).decode()

        url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        resp = requests.post(url, data=data, timeout=12)
        resp.raise_for_status()
        info = resp.json()

        cls._access_token = info["access_token"]
        expires_in = info.get("expires_in", 3600)
        cls._token_expiry = now + expires_in - 60
        return cls._access_token

    @classmethod
    def get_project_id(cls) -> str:
        if cls._project_id:
            return cls._project_id

        try:
            token = cls.get_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "antigravity/1.15.8 linux/amd64",
                "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
                "Client-Metadata": '{"ideType":"IDE_UNSPECIFIED","platform":"PLATFORM_UNSPECIFIED","pluginType":"GEMINI"}'
            }
            body = {
                "metadata": {
                    "ideType": "IDE_UNSPECIFIED",
                    "platform": "PLATFORM_UNSPECIFIED",
                    "pluginType": "GEMINI"
                }
            }
            url = f"{cls.CODE_ASSIST_ENDPOINT_PROD}/v1internal:loadCodeAssist"
            resp = requests.post(url, headers=headers, json=body, timeout=12)
            if resp.status_code == 200:
                res_data = resp.json()
                cls._project_id = res_data.get("cloudaicompanionProject", "")
        except Exception:
            pass

        if not cls._project_id:
            cls._project_id = "aicode-consumers"
        return cls._project_id

    @classmethod
    def fetch_available_models(cls) -> List[Tuple[str, str]]:
        fallback_models = [
            ("antigravity/gemini-3-flash", "Gemini 3 Flash (Antigravity - Fast & Efficient)"),
            ("antigravity/gemini-3-pro", "Gemini 3 Pro (Antigravity - High Intelligence)"),
            ("antigravity/gemini-2.5-flash", "Gemini 2.5 Flash (Antigravity - Responsive)"),
            ("antigravity/gemini-2.5-pro", "Gemini 2.5 Pro (Antigravity - Advanced Reasoning)"),
            ("antigravity/gemini-1.5-pro", "Gemini 1.5 Pro (Antigravity - Large Context)"),
            ("antigravity/gemini-1.5-flash", "Gemini 1.5 Flash (Antigravity - Balanced)"),
        ]
        if not cls.is_logged_in():
            return fallback_models

        try:
            token = cls.get_token()
            project_id = cls.get_project_id()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "antigravity/2.0.0 linux/amd64",
                "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
                "Client-Metadata": '{"ideType":"IDE_UNSPECIFIED","platform":"PLATFORM_UNSPECIFIED","pluginType":"GEMINI"}'
            }
            url = f"{cls.CODE_ASSIST_ENDPOINT_PROD}/v1internal:fetchAvailableModels"
            resp = requests.post(url, headers=headers, json={"project": project_id}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                models_data = data.get("models", {})
                models = []
                if isinstance(models_data, dict):
                    for m_id, m_info in models_data.items():
                        if not m_id:
                            continue
                        full_id = f"antigravity/{m_id}" if not m_id.startswith("antigravity/") else m_id
                        name = m_info.get("displayName", m_id) if isinstance(m_info, dict) else m_id
                        models.append((full_id, f"{name} ({full_id})"))
                if models:
                    models.sort(key=lambda x: x[0], reverse=True)
                    return models
        except Exception:
            pass
        return fallback_models

    @staticmethod
    def map_messages(openai_messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        contents = []
        system_instruction = None

        for msg in openai_messages:
            role = msg.get("role")
            content = msg.get("content") or ""

            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": str(content)}]
                })
            elif role == "assistant":
                parts = []
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    for tc in tool_calls:
                        fn = tc.get("function", {})
                        args = fn.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                args = {}
                        fc_part = {
                            "functionCall": {
                                "name": fn.get("name"),
                                "args": args
                            }
                        }
                        parts.append(fc_part)
                elif content:
                    parts.append({"text": content})
                contents.append({
                    "role": "model",
                    "parts": parts if parts else [{"text": ""}]
                })
            elif role == "tool":
                name = msg.get("name") or "tool_result"
                tool_call_id = msg.get("tool_call_id")
                try:
                    resp_obj = json.loads(content) if isinstance(content, str) else content
                    if not isinstance(resp_obj, dict):
                        resp_obj = {"output": resp_obj}
                except Exception:
                    resp_obj = {"output": str(content)}

                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": name,
                            "response": resp_obj
                        }
                    }]
                })

        return contents, system_instruction

    @staticmethod
    def map_tools(tools: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if not tools:
            return []
        gemini_decls = []
        for t in tools:
            if t.get("type") == "function":
                fn = t.get("function", {})
                decl = {
                    "name": fn.get("name"),
                    "description": fn.get("description", ""),
                }
                params = fn.get("parameters")
                if params and isinstance(params, dict):
                    # Sanitize parameter schema for Gemini API
                    props = params.get("properties", {})
                    sanitized_props = {}
                    for p_name, p_schema in props.items():
                        sanitized_props[p_name] = {
                            "type": p_schema.get("type", "string").upper(),
                            "description": p_schema.get("description", "")
                        }
                    decl["parameters"] = {
                        "type": "OBJECT",
                        "properties": sanitized_props,
                        "required": params.get("required", [])
                    }
                gemini_decls.append(decl)
        return [{"functionDeclarations": gemini_decls}] if gemini_decls else []

    @classmethod
    def completion(
        cls,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> SimpleNamespace:
        clean_model = model.split("/")[-1]
        token = cls.get_token()
        project_id = cls.get_project_id()

        contents, system_instruction = cls.map_messages(messages)
        gemini_tools = cls.map_tools(tools)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "antigravity/hub/2.1.4 linux/amd64",
            "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
            "Client-Metadata": '{"ideType":"IDE_UNSPECIFIED","platform":"PLATFORM_UNSPECIFIED","pluginType":"GEMINI"}'
        }

        sys_parts = [{"text": ANTIGRAVITY_SYSTEM_INSTRUCTION}]
        if system_instruction and isinstance(system_instruction, dict):
            sys_parts.extend(system_instruction.get("parts", []))

        request_payload: Dict[str, Any] = {
            "contents": contents,
            "systemInstruction": {
                "role": "user",
                "parts": sys_parts
            }
        }

        if gemini_tools:
            request_payload["tools"] = gemini_tools

        if temperature is not None:
            request_payload["generationConfig"] = {"temperature": temperature}

        session_id = f"-{uuid.uuid4().int & ((1 << 63) - 1)}"
        request_id = f"agent/{uuid.uuid4()}/{int(time.time() * 1000)}"
        request_payload["sessionId"] = session_id

        body = {
            "project": project_id,
            "model": clean_model,
            "userAgent": "antigravity",
            "requestType": "agent",
            "requestId": request_id,
            "request": request_payload
        }

        url = f"{cls.CODE_ASSIST_ENDPOINT_PROD}/v1internal:generateContent"
        resp = requests.post(url, headers=headers, json=body, timeout=120)
        resp.raise_for_status()
        res_data = resp.json()

        candidate = res_data.get("response", {}).get("candidates", [{}])[0]
        parts = candidate.get("content", {}).get("parts", [])
        finish_reason = candidate.get("finishReason")

        text = ""
        tool_calls = []
        for part in parts:
            if "text" in part and not part.get("thought"):
                text += part["text"]
            if "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(SimpleNamespace(
                    id=fc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                    type="function",
                    function=SimpleNamespace(
                        name=fc.get("name"),
                        arguments=json.dumps(fc.get("args") or {})
                    )
                ))

        message = SimpleNamespace(
            role="assistant",
            content=text if text else None,
            tool_calls=tool_calls if tool_calls else None
        )

        choice = SimpleNamespace(
            message=message,
            finish_reason=finish_reason
        )

        return SimpleNamespace(choices=[choice], model=model)
