import pytest
import httpx
from bitwig_agent.client import BitwigClient, NoteEvent, ProjectState

def test_client_models():
    note = NoteEvent(step=0, pitch=60, velocity=90, duration=1.0)
    assert note.pitch == 60
    assert note.velocity == 90
    assert note.duration == 1.0

    state = ProjectState(
        tempo=120.0,
        isPlaying=False,
        tracks=[
            {
                "index": 0,
                "name": "Keys",
                "isGroup": False,
                "arm": False,
                "mute": False,
                "solo": False,
                "slots": [
                    {"index": 0, "hasContent": True, "isPlaying": False, "isSelected": True}
                ]
            }
        ]
    )
    assert state.tempo == 120.0
    assert state.tracks[0].name == "Keys"

def test_client_urls():
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    assert client.base_url == "http://127.0.0.1:8989"

def test_add_instrument_payload(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    recorded = {}

    class MockResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"status": "created", "name": "Synth", "instrument": "polymer"}

    def mock_post(url, json=None):
        recorded["url"] = url
        recorded["json"] = json
        return MockResponse()

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, json=None: mock_post(url, json=json))
    res = client.add_instrument(name="Synth", instrument="polymer", position=-1)
    assert res["status"] == "created"
    assert recorded["url"] == "http://127.0.0.1:8989/api/instrument/add"
    assert recorded["json"] == {"name": "Synth", "instrument": "polymer", "position": -1}

def test_inspect_track_payload(monkeypatch):
    from bitwig_agent.client import TrackDetail, DeviceInfo
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    recorded = {}

    class MockResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {
                "index": 2,
                "name": "Polymer Pad",
                "type": "Instrument",
                "volume": "0.00 dB",
                "pan": "C",
                "isGroup": False,
                "arm": True,
                "mute": False,
                "solo": False,
                "devices": [
                    {
                        "index": 0,
                        "name": "Polymer",
                        "type": "instrument",
                        "preset": "Default",
                        "category": "Synth",
                        "isEnabled": True,
                        "isPlugin": False
                    }
                ],
                "occupied_clips": [
                    {"slot": 0, "name": "Chords", "isPlaying": True, "isSelected": False}
                ]
            }

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, json=None: (recorded.update({"url": url, "json": json}) or MockResponse()))
    res = client.inspect_track(2)
    detail = TrackDetail.model_validate(res)
    assert detail.name == "Polymer Pad"
    assert len(detail.devices) == 1
    assert detail.devices[0].name == "Polymer"
    assert detail.occupied_clips[0].name == "Chords"
    assert recorded["url"] == "http://127.0.0.1:8989/api/track/inspect"
    assert recorded["json"] == {"track": 2}

def test_inspect_clip_payload(monkeypatch):
    from bitwig_agent.client import ClipDetail
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    recorded = {}

    class MockResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {
                "track": 1,
                "track_name": "Voices",
                "slot": 2,
                "name": "Chorus Vibe",
                "has_content": True,
                "is_playing": True,
                "loop_length": 16.0,
                "notes": [
                    {
                        "step": 0,
                        "beat": 0.0,
                        "pitch": 60,
                        "name": "C4",
                        "velocity": 100,
                        "duration": 4.0,
                        "channel": 0
                    }
                ],
                "notes_count": 1
            }

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, json=None: (recorded.update({"url": url, "json": json}) or MockResponse()))
    res = client.inspect_clip(track=1, slot=2)
    detail = ClipDetail.model_validate(res)
    assert detail.track_name == "Voices"
    assert detail.slot == 2
    assert detail.has_content is True
    assert len(detail.notes) == 1
    assert detail.notes[0].pitch == 60
    assert recorded["url"] == "http://127.0.0.1:8989/api/clip/inspect"
    assert recorded["json"] == {"track": 1, "slot": 2}

def test_record_and_scene_payload(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    recorded = {}

    class MockResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"status": "ok", "action": recorded.get("json", {}).get("action")}

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, json=None: (recorded.update({"url": url, "json": json}) or MockResponse()))

    res = client.start_record()
    assert recorded["url"] == "http://127.0.0.1:8989/api/transport"
    assert recorded["json"] == {"action": "record"}

    res = client.stop_record()
    assert recorded["json"] == {"action": "stop_record"}

    res = client.toggle_record()
    assert recorded["json"] == {"action": "toggle_record"}

    res = client.return_to_arrangement()
    assert recorded["json"] == {"action": "return_to_arrangement"}

    class MockSceneResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"status": "launched", "scene": recorded.get("json", {}).get("scene")}

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, json=None: (recorded.update({"url": url, "json": json}) or MockSceneResponse()))
    res = client.launch_scene(scene=3)
    assert res["status"] == "launched"
    assert recorded["url"] == "http://127.0.0.1:8989/api/scene/launch"
    assert recorded["json"] == {"scene": 3}

def test_add_effect_and_control_device_payload(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    recorded = {}

    class MockResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"status": "ok", "recorded": recorded.get("json")}

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, json=None: (recorded.update({"url": url, "json": json}) or MockResponse()))

    res = client.add_effect(track=1, effect="delay+", position="end", create_effect_track=False)
    assert recorded["url"] == "http://127.0.0.1:8989/api/effect/add"
    assert recorded["json"] == {
        "track": 1,
        "effect": "delay+",
        "position": "end",
        "create_effect_track": False
    }

    res_fx = client.add_effect(effect="reverb", create_effect_track=True)
    assert recorded["json"] == {
        "effect": "reverb",
        "position": "end",
        "create_effect_track": True
    }

    res_ctrl = client.control_device(track=0, device="Reverb", action="set_enabled", enabled=False)
    assert recorded["url"] == "http://127.0.0.1:8989/api/device/control"
    assert recorded["json"] == {
        "track": 0,
        "device": "Reverb",
        "action": "set_enabled",
        "enabled": False
    }

def test_inspect_arranger_payload(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    recorded = {}

    class MockResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {
                "timeline": {
                    "position_beats": 16.0,
                    "tempo": 124.0,
                    "is_playing": True,
                    "is_recording": False,
                    "loop_enabled": True,
                    "loop_start_beat": 0.0,
                    "loop_duration_beats": 32.0
                },
                "cue_markers": [
                    {"index": 0, "name": "Intro", "position_beat": 0.0, "bar": 1},
                    {"index": 1, "name": "Drop", "position_beat": 32.0, "bar": 9}
                ],
                "cue_markers_count": 2,
                "selected_clip": None
            }

    monkeypatch.setattr(httpx.Client, "get", lambda self, url: (recorded.update({"url": url}) or MockResponse()))
    res = client.inspect_arranger()
    assert recorded["url"] == "http://127.0.0.1:8989/api/arranger/inspect"
    assert res["timeline"]["tempo"] == 124.0
    assert len(res["cue_markers"]) == 2
    assert res["cue_markers"][1]["name"] == "Drop"

