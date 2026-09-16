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



