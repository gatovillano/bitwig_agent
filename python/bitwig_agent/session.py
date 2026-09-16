from __future__ import annotations
import os
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

from bitwig_agent.config import CONFIG_DIR

SESSIONS_DIR = CONFIG_DIR / "sessions"

@dataclass
class Session:
    id: str
    title: str
    created_at: str
    updated_at: str
    provider: str
    model: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def message_count(self) -> int:
        return len([m for m in self.messages if m.get("role") in ("user", "assistant")])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "provider": self.provider,
            "model": self.model,
            "messages": self.messages,
            "metadata": self.metadata,
            "message_count": self.message_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Session:
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            title=data.get("title", "Sesión sin título"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            provider=data.get("provider", "google"),
            model=data.get("model", ""),
            messages=data.get("messages", []),
            metadata=data.get("metadata", {}),
        )

class SessionManager:
    """
    Manages persistent conversation sessions in ~/.config/bitwig_agent/sessions/
    """
    def __init__(self, directory: Optional[Path] = None):
        self.directory = directory or SESSIONS_DIR
        self.ensure_dir()

    def ensure_dir(self) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        return self.directory

    def _generate_id(self, title: Optional[str] = None) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if title:
            # Clean slug from title
            slug = re.sub(r"[^\w\s-]", "", title).strip().lower()
            slug = re.sub(r"[-\s]+", "_", slug)[:24]
            if slug:
                return f"{slug}_{timestamp}"
        short_uuid = uuid.uuid4().hex[:6]
        return f"session_{timestamp}_{short_uuid}"

    def auto_title_from_prompt(self, prompt: str) -> str:
        clean = prompt.strip().replace("\n", " ")
        if len(clean) > 45:
            return clean[:42] + "..."
        return clean or "Sesión Musical"

    def create_session(
        self,
        title: Optional[str] = None,
        provider: str = "google",
        model: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None
    ) -> Session:
        now = datetime.now().isoformat()
        sid = session_id or self._generate_id(title)
        stitle = title or "Nueva Sesión"
        sess = Session(
            id=sid,
            title=stitle,
            created_at=now,
            updated_at=now,
            provider=provider,
            model=model,
            messages=messages or []
        )
        self.save_session(sess)
        return sess

    def save_session(self, session: Session) -> bool:
        self.ensure_dir()
        session.updated_at = datetime.now().isoformat()
        filepath = self.directory / f"{session.id}.json"
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def get_session(self, session_id: str) -> Optional[Session]:
        filepath = self.directory / f"{session_id}.json"
        if not filepath.exists():
            # Try searching by exact name or matching prefix
            matches = list(self.directory.glob(f"*{session_id}*.json"))
            if matches:
                filepath = matches[0]
            else:
                return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Session.from_dict(data)
        except Exception:
            return None

    def list_sessions(self) -> List[Dict[str, Any]]:
        self.ensure_dir()
        results = []
        for file in self.directory.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    results.append({
                        "id": data.get("id", file.stem),
                        "title": data.get("title", "Sin título"),
                        "created_at": data.get("created_at", ""),
                        "updated_at": data.get("updated_at", ""),
                        "provider": data.get("provider", "desconocido"),
                        "model": data.get("model", ""),
                        "message_count": data.get("message_count", len(data.get("messages", []))),
                    })
            except Exception:
                continue

        # Sort by updated_at descending
        results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return results

    def find_sessions(self, query: str) -> List[Dict[str, Any]]:
        all_sessions = self.list_sessions()
        q = query.lower().strip()
        matches = []
        for s in all_sessions:
            if q in s["id"].lower() or q in s["title"].lower():
                matches.append(s)
        return matches

    def delete_session(self, session_id: str) -> bool:
        filepath = self.directory / f"{session_id}.json"
        if filepath.exists():
            try:
                filepath.unlink()
                return True
            except Exception:
                return False
        # Try matching glob
        matches = list(self.directory.glob(f"*{session_id}*.json"))
        if matches:
            try:
                matches[0].unlink()
                return True
            except Exception:
                return False
        return False
