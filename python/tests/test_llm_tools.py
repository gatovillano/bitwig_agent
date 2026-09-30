import pytest
from bitwig_agent.client import BitwigClient
from bitwig_agent.llm.tools import ToolExecutor, BITWIG_TOOLS

def test_tools_schema():
    assert len(BITWIG_TOOLS) >= 10
    names = [t["function"]["name"] for t in BITWIG_TOOLS]
    assert "create_chord_progression" in names
    assert "create_bassline" in names
    assert "control_transport" in names
    assert "get_project_context" in names
    assert "add_instrument_track" in names
    assert "inspect_track" in names
    assert "inspect_clip" in names
    assert "inspect_arranger" in names
    assert "write_notes" in names
    assert "launch_scene" in names
    assert "record_to_arranger" in names
    assert "add_audio_effect" in names
    assert "control_device" in names
    assert "list_audio_effects" in names

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
 
def test_executor_inspect_arranger_call(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    called = {"count": 0}

    def mock_inspect_arranger():
        called["count"] += 1
        return {
            "timeline": {
                "position_beats": 32.0,
                "tempo": 128.0,
                "is_playing": True,
                "is_recording": False,
                "is_overdub": False,
                "loop_enabled": True,
                "loop_start_beat": 0.0,
                "loop_duration_beats": 32.0
            },
            "cue_markers": [
                {"index": 0, "name": "Verse 1", "position_beat": 0.0, "bar": 1},
                {"index": 1, "name": "Chorus", "position_beat": 16.0, "bar": 5}
            ],
            "cue_markers_count": 2,
            "selected_clip": {
                "has_content": True,
                "track": 0,
                "track_name": "Lead Synth",
                "play_start": 0.0,
                "play_stop": 16.0,
                "loop_length": 16.0,
                "notes": [
                    {"step": 0, "beat": 0.0, "pitch": 72, "name": "C5", "velocity": 100, "duration": 2.0}
                ],
                "notes_count": 1
            }
        }

    monkeypatch.setattr(client, "inspect_arranger", mock_inspect_arranger)
    executor = ToolExecutor(client)
    res = executor.execute("inspect_arranger", {})
    assert called["count"] == 1
    assert res["timeline"]["tempo"] == 128.0
    assert len(res["cue_markers"]) == 2
    assert "piano_roll" in res["selected_clip"]
    assert "C5" in res["selected_clip"]["piano_roll"]

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

def test_executor_launch_scene(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    called = {}
    monkeypatch.setattr(client, "launch_scene", lambda scene: (called.update({"scene": scene}) or {"status": "launched", "scene": scene}))
    executor = ToolExecutor(client)
    res = executor.execute("launch_scene", {"scene": 2})
    assert res["status"] == "success"
    assert res["scene"] == 2
    assert called["scene"] == 2

def test_executor_control_transport_recording(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    called = []
    monkeypatch.setattr(client, "start_record", lambda: (called.append("start_record") or {"status": "ok"}))
    monkeypatch.setattr(client, "stop_record", lambda: (called.append("stop_record") or {"status": "ok"}))
    monkeypatch.setattr(client, "return_to_arrangement", lambda: (called.append("return_to_arrangement") or {"status": "ok"}))
    monkeypatch.setattr(client, "set_position", lambda pos: (called.append(f"set_pos:{pos}") or {"status": "ok"}))

    executor = ToolExecutor(client)
    executor.execute("control_transport", {"action": "record"})
    assert "start_record" in called

    executor.execute("control_transport", {"action": "stop_record"})
    assert "stop_record" in called

    executor.execute("control_transport", {"action": "return_to_arrangement"})
    assert "return_to_arrangement" in called

    executor.execute("control_transport", {"action": "set_position", "position": 16.0})
    assert "set_pos:16.0" in called

def test_executor_record_to_arranger_manual(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    called = []
    monkeypatch.setattr(client, "set_position", lambda pos: called.append(f"pos:{pos}"))
    monkeypatch.setattr(client, "start_record", lambda: (called.append("start_record") or {"status": "ok"}))
    monkeypatch.setattr(client, "stop_record", lambda: called.append("stop_record"))
    monkeypatch.setattr(client, "stop", lambda: called.append("stop"))
    monkeypatch.setattr(client, "return_to_arrangement", lambda: called.append("return_to_arr"))
    monkeypatch.setattr(client, "launch_scene", lambda s: called.append(f"scene:{s}"))

    executor = ToolExecutor(client)
    res_start = executor.execute("record_to_arranger", {"action": "start", "start_beat": 8.0, "scene": 1})
    assert res_start["status"] == "recording_started"
    assert "pos:8.0" in called
    assert "start_record" in called
    assert "scene:1" in called

    res_stop = executor.execute("record_to_arranger", {"action": "stop"})
    assert res_stop["status"] == "recording_stopped"
    assert "stop_record" in called
    assert "stop" in called
    assert "return_to_arr" in called

def test_executor_record_to_arranger_sequence(monkeypatch):
    import time
    from bitwig_agent.client import ProjectState
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    called = []
    slept = []

    monkeypatch.setattr(client, "get_project", lambda: ProjectState(tempo=120.0, isPlaying=False, tracks=[]))
    monkeypatch.setattr(client, "set_position", lambda pos: called.append(f"pos:{pos}"))
    monkeypatch.setattr(client, "start_record", lambda: called.append("record"))
    monkeypatch.setattr(client, "stop_record", lambda: called.append("stop_record"))
    monkeypatch.setattr(client, "stop", lambda: called.append("stop"))
    monkeypatch.setattr(client, "return_to_arrangement", lambda: called.append("return_to_arr"))
    monkeypatch.setattr(client, "launch_scene", lambda s: called.append(f"scene:{s}"))
    monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))

    executor = ToolExecutor(client)
    res = executor.execute("record_to_arranger", {
        "sequence": [
            {"scene": 0, "bars": 2},  # 8 beats = 4.0 seconds at 120 bpm
            {"scene": 1, "bars": 4}   # 16 beats = 8.0 seconds at 120 bpm
        ],
        "start_beat": 0.0
    })

    assert res["status"] == "completed"
    assert res["total_beats"] == 24.0
    assert res["total_bars"] == 6.0
    assert len(res["sections"]) == 2
    assert "record" in called
    assert "scene:0" in called
    assert "scene:1" in called
    assert "stop_record" in called
    assert "return_to_arr" in called
    assert len(slept) == 2
    assert slept[0] == pytest.approx(4.0)
    assert slept[1] == pytest.approx(8.0)

def test_executor_add_audio_effect(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    called = {}

    def mock_add_effect(track, effect, position, create_effect_track):
        called["track"] = track
        called["effect"] = effect
        called["position"] = position
        called["create_effect_track"] = create_effect_track
        return {"status": "effect_added", "effect": effect}

    monkeypatch.setattr(client, "add_effect", mock_add_effect)
    executor = ToolExecutor(client)

    res = executor.execute("add_audio_effect", {
        "track": 0,
        "effect": "delay+",
        "position": "end"
    })
    assert res["status"] == "effect_added"
    assert called["track"] == 0
    assert called["effect"] == "delay+"
    assert called["position"] == "end"
    assert called["create_effect_track"] is False

    res_fx = executor.execute("add_audio_effect", {
        "effect": "reverb",
        "create_effect_track": True
    })
    assert called["create_effect_track"] is True
    assert called["track"] is None

def test_executor_control_device(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    called = {}

    def mock_control(track, device, action, enabled):
        called["track"] = track
        called["device"] = device
        called["action"] = action
        called["enabled"] = enabled
        return {"status": "ok", "action": action}

    monkeypatch.setattr(client, "control_device", mock_control)
    executor = ToolExecutor(client)

    res = executor.execute("control_device", {
        "track": 0,
        "device": "Reverb",
        "action": "set_enabled",
        "enabled": False
    })
    assert res["status"] == "ok"
    assert called["track"] == 0
    assert called["device"] == "Reverb"
    assert called["action"] == "set_enabled"
    assert called["enabled"] is False

def test_executor_list_audio_effects():
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    executor = ToolExecutor(client)

    res = executor.execute("list_audio_effects", {})
    assert "categories" in res
    assert "Reverb" in res["categories"]
    assert "Delay" in res["categories"]
    assert "Dynamics" in res["categories"]
    assert "EQ & Filter" in res["categories"]

    res_filtered = executor.execute("list_audio_effects", {"category": "delay"})
    assert "categories" in res_filtered
    assert "Delay" in res_filtered["categories"]

def test_executor_control_track(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    called = {}

    def mock_control_track(track, volume, pan, mute, solo, arm, name):
        called["track"] = track
        called["volume"] = volume
        called["pan"] = pan
        called["mute"] = mute
        called["solo"] = solo
        called["arm"] = arm
        called["name"] = name
        return {"status": "success", "track_index": track}

    monkeypatch.setattr(client, "control_track", mock_control_track)
    executor = ToolExecutor(client)

    res = executor.execute("control_track", {
        "track": 0,
        "volume": 0.75,
        "pan": -0.2,
        "mute": False,
        "solo": True,
        "name": "Lead Synth"
    })
    assert res["status"] == "success"
    assert called["track"] == 0
    assert called["volume"] == 0.75
    assert called["pan"] == -0.2
    assert called["mute"] is False
    assert called["solo"] is True
    assert called["name"] == "Lead Synth"

def test_executor_recommend_devices():
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    executor = ToolExecutor(client)

    res = executor.execute("recommend_devices", {
        "description": "warm analog synth for lush synthwave pads",
        "num_results": 3
    })
    assert "recommendations" in res
    assert res["count"] > 0
    assert any(r["device"] in ["Polymer", "Polysynth"] for r in res["recommendations"])

def test_executor_search_device_browser():
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    executor = ToolExecutor(client)

    res = executor.execute("search_device_browser", {"query": "delay"})
    assert "results" in res
    assert res["count"] > 0
    names = [r["name"] for r in res["results"]]
    assert any("Delay" in n for n in names)

def test_executor_get_device_info():
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    executor = ToolExecutor(client)

    res = executor.execute("get_device_info", {"device_name": "Polymer"})
    assert res["status"] == "success"
    assert res["device"]["name"] == "Polymer"

    err = executor.execute("get_device_info", {"device_name": "NonExistentThing"})
    assert "error" in err

def test_executor_get_device_categories():
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    executor = ToolExecutor(client)

    res = executor.execute("get_device_categories", {})
    assert "categories" in res
    assert "Synth" in res["categories"]

