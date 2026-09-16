from unittest.mock import MagicMock
from prompt_toolkit.document import Document
from prompt_toolkit.completion import CompleteEvent
from bitwig_agent.completer import BitwigCliCompleter

def test_non_slash_input_returns_no_completions():
    completer = BitwigCliCompleter()
    doc = Document("Crea una progresión en D menor", cursor_position=len("Crea una progresión en D menor"))
    completions = list(completer.get_completions(doc, CompleteEvent()))
    assert len(completions) == 0

def test_slash_triggers_root_commands():
    completer = BitwigCliCompleter()
    doc = Document("/", cursor_position=1)
    completions = list(completer.get_completions(doc, CompleteEvent()))
    texts = [c.text for c in completions]
    assert "/session" in texts
    assert "/provider" in texts
    assert "/model" in texts
    assert "/status" in texts
    assert "/help" in texts
    assert "/exit" in texts

def test_partial_root_command_filter():
    completer = BitwigCliCompleter()
    doc = Document("/se", cursor_position=3)
    completions = list(completer.get_completions(doc, CompleteEvent()))
    texts = [c.text for c in completions]
    assert texts == ["/session"]
    assert completions[0].start_position == -3

def test_session_subcommands():
    completer = BitwigCliCompleter()
    doc = Document("/session ", cursor_position=len("/session "))
    completions = list(completer.get_completions(doc, CompleteEvent()))
    texts = [c.text for c in completions]
    assert "list" in texts
    assert "save" in texts
    assert "load" in texts
    assert "new" in texts
    assert "delete" in texts

def test_session_partial_subcommand():
    completer = BitwigCliCompleter()
    doc = Document("/session lo", cursor_position=len("/session lo"))
    completions = list(completer.get_completions(doc, CompleteEvent()))
    texts = [c.text for c in completions]
    assert texts == ["load"]
    assert completions[0].start_position == -2

def test_dynamic_session_load_completion():
    mock_sm = MagicMock()
    mock_sm.list_sessions.return_value = [
        {"id": "session-123", "title": "Boceto Lofi", "message_count": 4, "updated_at": "2026-09-15T12:00:00"},
        {"id": "session-456", "title": "Techno Beat", "message_count": 8, "updated_at": "2026-09-15T13:00:00"},
    ]
    completer = BitwigCliCompleter(session_manager=mock_sm)
    doc = Document("/session load ", cursor_position=len("/session load "))
    completions = list(completer.get_completions(doc, CompleteEvent()))
    texts = [c.text for c in completions]
    assert "session-123" in texts
    assert "session-456" in texts

def test_dynamic_provider_completion():
    completer = BitwigCliCompleter()
    doc = Document("/provider ", cursor_position=len("/provider "))
    completions = list(completer.get_completions(doc, CompleteEvent()))
    texts = [c.text for c in completions]
    assert "google" in texts
    assert "anthropic" in texts
    assert "openai" in texts
