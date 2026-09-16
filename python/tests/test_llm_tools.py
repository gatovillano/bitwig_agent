import pytest
from bitwig_agent.client import BitwigClient
from bitwig_agent.llm.tools import ToolExecutor, BITWIG_TOOLS

def test_tools_schema():
    assert len(BITWIG_TOOLS) >= 4
    names = [t["function"]["name"] for t in BITWIG_TOOLS]
    assert "create_chord_progression" in names
    assert "create_bassline" in names
    assert "control_transport" in names
    assert "get_project_context" in names
    assert "add_instrument_track" in names
    assert "inspect_track" in names
    assert "inspect_clip" in names
    assert "write_notes" in names

def test_executor_disconnected_graceful():
    client = BitwigClient(base_url="http://127.0.0.1:9999") # non-existent port
    executor = ToolExecutor(client)
    res = executor.execute("get_project_context", {})
    assert "error" in res
    assert "not connected" in res["error"]

def test_executor_add_instrument_call(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    called = {}
    def mock_add_instrument(name, instrument, position, track=None):
        called["name"] = name
        called["instrument"] = instrument
        called["position"] = position
        called["track"] = track
        return {"status": "created", "name": name, "instrument": instrument}

    monkeypatch.setattr(client, "add_instrument", mock_add_instrument)
    executor = ToolExecutor(client)
    res = executor.execute("add_instrument_track", {
        "name": "Sub Bass",
        "instrument": "polymer",
        "position": -1
    })
    assert res["status"] == "created"
    assert called["name"] == "Sub Bass"
    assert called["instrument"] == "polymer"
    assert called["position"] == -1
    assert called["track"] is None

def test_executor_inspect_track_call(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    called = {}
    def mock_inspect(track):
        called["track"] = track
        return {"name": "Keys", "index": track, "devices": []}

    monkeypatch.setattr(client, "inspect_track", mock_inspect)
    executor = ToolExecutor(client)
    res = executor.execute("inspect_track", {"track": 1})
    assert res["name"] == "Keys"
    assert called["track"] == 1

def test_executor_inspect_clip_call(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    called = {}
    def mock_inspect_clip(track, slot):
        called["track"] = track
        called["slot"] = slot
        return {
            "track": track,
            "track_name": "Rhodes",
            "slot": slot,
            "name": "Soul Chords",
            "has_content": True,
            "is_playing": True,
            "loop_length": 16.0,
            "notes": [
                {"step": 0, "beat": 0.0, "pitch": 60, "name": "C4", "velocity": 90, "duration": 4.0},
                {"step": 0, "beat": 0.0, "pitch": 64, "name": "E4", "velocity": 85, "duration": 4.0}
            ],
            "notes_count": 2
        }

    monkeypatch.setattr(client, "inspect_clip", mock_inspect_clip)
    executor = ToolExecutor(client)
    res = executor.execute("inspect_clip", {"track": 0, "slot": 1})
    assert res["track"] == 0
    assert res["slot"] == 1
    assert called["track"] == 0
    assert called["slot"] == 1
    assert "piano_roll" in res
    assert "Soul Chords" in res["piano_roll"]
    assert "C4" in res["piano_roll"]
    assert "■" in res["piano_roll"]
 
def test_executor_write_notes_call(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    called_write = {}
    called_launch = {}

    def mock_write_notes(track, slot, notes, clear, beats):
        called_write["track"] = track
        called_write["slot"] = slot
        called_write["notes"] = notes
        called_write["clear"] = clear
        called_write["beats"] = beats
        return {"status": "notes_written", "notes_count": len(notes)}

    def mock_launch_clip(track, slot):
        called_launch["track"] = track
        called_launch["slot"] = slot
        return {"status": "clip_launched"}

    monkeypatch.setattr(client, "write_notes", mock_write_notes)
    monkeypatch.setattr(client, "launch_clip", mock_launch_clip)

    executor = ToolExecutor(client)
    res = executor.execute("write_notes", {
        "track": 0,
        "slot": 1,
        "notes": [
            {"pitch": "C4", "step": 0, "duration": 1.0, "velocity": 100},
            {"pitch": 64, "beat": 1.0, "duration": 0.5, "velocity": 90},  # beat 1.0 -> step 4
            {"pitch": "G4", "step": 8, "duration": 2.0}
        ],
        "beats": 8,
        "clear": True,
        "launch": True,
        "humanize": False
    })

    assert res["status"] == "success"
    assert res["track"] == 0
    assert res["slot"] == 1
    assert res["total_notes"] == 3
    assert res["beats"] == 8
    assert "piano_roll" in res
    assert "C4" in res["piano_roll"]
    assert "E4" in res["piano_roll"]
    assert "G4" in res["piano_roll"]

    assert called_write["track"] == 0
    assert called_write["slot"] == 1
    assert called_write["clear"] is True
    assert called_write["beats"] == 8
    assert len(called_write["notes"]) == 3

    # Check note conversions
    n1, n2, n3 = called_write["notes"]
    assert n1.pitch == 60 and n1.step == 0 and n1.duration == 1.0
    assert n2.pitch == 64 and n2.step == 4 and n2.duration == 0.5
    assert n3.pitch == 67 and n3.step == 8 and n3.duration == 2.0

    assert called_launch["track"] == 0
    assert called_launch["slot"] == 1

def test_executor_write_notes_humanize(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    written = {}

    def mock_write(track, slot, notes, clear, beats):
        written["notes"] = notes
        return {"status": "ok"}

    monkeypatch.setattr(client, "write_notes", mock_write)
    executor = ToolExecutor(client)
    res = executor.execute("write_notes", {
        "track": 0,
        "notes": [
            {"pitch": "C4", "step": 0, "velocity": 100},
            {"pitch": "E4", "step": 0, "velocity": 100}
        ],
        "humanize": True
    })

    assert res["status"] == "success"
    assert len(written["notes"]) == 2

def test_executor_write_notes_invalid_pitch():
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    executor = ToolExecutor(client)
    res = executor.execute("write_notes", {
        "track": 0,
        "notes": [{"pitch": "H99", "step": 0}]
    })
    assert "error" in res
    assert "Invalid pitch" in res["error"]


