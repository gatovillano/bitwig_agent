import pytest
from pathlib import Path
from bitwig_agent.session import SessionManager, Session

def test_session_lifecycle(tmp_path):
    sm = SessionManager(directory=tmp_path)
    
    # Create session
    sess = sm.create_session(
        title="Neo-Soul Session in Dm",
        provider="antigravity",
        model="antigravity/gemini-3-flash",
        messages=[
            {"role": "user", "content": "Crea una progresión en Dm9"},
            {"role": "assistant", "content": "He creado la progresión Dm9 - G13 - Cmaj9"}
        ]
    )
    assert sess.id is not None
    assert sess.title == "Neo-Soul Session in Dm"
    assert sess.message_count == 2

    # List sessions
    sessions = sm.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["id"] == sess.id

    # Retrieve session
    retrieved = sm.get_session(sess.id)
    assert retrieved is not None
    assert retrieved.title == "Neo-Soul Session in Dm"
    assert len(retrieved.messages) == 2

    # Search session
    found = sm.find_sessions("neo-soul")
    assert len(found) == 1

    # Delete session
    deleted = sm.delete_session(sess.id)
    assert deleted is True
    assert len(sm.list_sessions()) == 0

def test_auto_title():
    sm = SessionManager()
    title = sm.auto_title_from_prompt("Crea una progresión armónica neo-soul en D menor a 85 bpm")
    assert len(title) <= 45
    assert "neo-soul" in title.lower()
