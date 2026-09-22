import pytest
import httpx
from bitwig_agent.client import BitwigClient
from bitwig_agent.llm.tools import ToolExecutor, BITWIG_TOOLS

def test_bitwig_tools_contains_track_organization():
    tool_names = [t["function"]["name"] for t in BITWIG_TOOLS]
    assert "move_track" in tool_names
    assert "group_tracks" in tool_names
    assert "ungroup_track" in tool_names
    assert "organize_tracks" in tool_names

def test_client_move_track(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    recorded = {}

    class MockResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"status": "tracks_moved", "moved_tracks": ["Perc"], "target_track": "Drums", "position": "after"}

    def mock_post(url, json=None):
        recorded["url"] = url
        recorded["json"] = json
        return MockResponse()

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, json=None: mock_post(url, json=json))
    res = client.move_track(tracks="Perc", target="Drums", position="after")
    assert res["status"] == "tracks_moved"
    assert recorded["url"] == "http://127.0.0.1:8989/api/track/move"
    assert recorded["json"] == {"tracks": ["Perc"], "position": "after", "target": "Drums"}

def test_client_group_tracks(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    recorded = {}

    class MockResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"status": "group_created", "group_name": "Drums", "grouped_tracks": ["Kick", "Snare"]}

    def mock_post(url, json=None):
        recorded["url"] = url
        recorded["json"] = json
        return MockResponse()

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, json=None: mock_post(url, json=json))
    res = client.group_tracks(tracks=["Kick", "Snare"], name="Drums")
    assert res["status"] == "group_created"
    assert recorded["url"] == "http://127.0.0.1:8989/api/track/group"
    assert recorded["json"] == {"tracks": ["Kick", "Snare"], "name": "Drums"}

def test_client_ungroup_track(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    recorded = {}

    class MockResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"status": "ungrouped", "track": "Drums"}

    def mock_post(url, json=None):
        recorded["url"] = url
        recorded["json"] = json
        return MockResponse()

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, json=None: mock_post(url, json=json))
    res = client.ungroup_track(track="Drums")
    assert res["status"] == "ungrouped"
    assert recorded["url"] == "http://127.0.0.1:8989/api/track/ungroup"
    assert recorded["json"] == {"track": "Drums"}

def test_client_rename_track(monkeypatch):
    client = BitwigClient(base_url="http://127.0.0.1:8989")
    recorded = {}

    class MockResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"status": "renamed", "track_index": 0, "name": "Lead Synth"}

    def mock_post(url, json=None):
        recorded["url"] = url
        recorded["json"] = json
        return MockResponse()

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, json=None: mock_post(url, json=json))
    res = client.rename_track(track="Lead", name="Lead Synth")
    assert res["status"] == "renamed"
    assert recorded["url"] == "http://127.0.0.1:8989/api/track/rename"
    assert recorded["json"] == {"track": "Lead", "name": "Lead Synth"}

def test_executor_move_track(monkeypatch):
    client = BitwigClient()
    executor = ToolExecutor(client)

    monkeypatch.setattr(client, "move_track", lambda tracks, target=None, position="after": {
        "status": "tracks_moved",
        "moved_tracks": tracks if isinstance(tracks, list) else [tracks],
        "target_track": target,
        "position": position
    })

    res = executor.execute("move_track", {"tracks": ["Bass"], "target": "Drums", "position": "after"})
    assert res["status"] == "success"
    assert "Moved track" in res["message"]

def test_executor_group_tracks(monkeypatch):
    client = BitwigClient()
    executor = ToolExecutor(client)

    monkeypatch.setattr(client, "group_tracks", lambda tracks, name=None, group=None: {
        "status": "group_created",
        "group_name": name or "Group",
        "grouped_tracks": tracks
    })

    res = executor.execute("group_tracks", {"tracks": ["Kick", "Snare"], "name": "Drums"})
    assert res["status"] == "success"
    assert "Grouped tracks" in res["message"]

def test_executor_ungroup_track(monkeypatch):
    client = BitwigClient()
    executor = ToolExecutor(client)

    monkeypatch.setattr(client, "ungroup_track", lambda track: {
        "status": "ungrouped",
        "track": track
    })

    res = executor.execute("ungroup_track", {"track": "Drums"})
    assert res["status"] == "success"
    assert "Ungrouped track" in res["message"]

def test_executor_organize_tracks(monkeypatch):
    client = BitwigClient()
    executor = ToolExecutor(client)

    from bitwig_agent.client import ProjectState, TrackInfo

    mock_state = ProjectState(
        tempo=120.0,
        isPlaying=False,
        tracks=[
            TrackInfo(index=0, name="Kick", isGroup=False, arm=False, mute=False, solo=False, type="Instrument"),
            TrackInfo(index=1, name="Snare", isGroup=False, arm=False, mute=False, solo=False, type="Instrument"),
            TrackInfo(index=2, name="Bass Synth", isGroup=False, arm=False, mute=False, solo=False, type="Instrument"),
            TrackInfo(index=3, name="Sub Bass", isGroup=False, arm=False, mute=False, solo=False, type="Instrument"),
        ]
    )

    monkeypatch.setattr(client, "get_project", lambda: mock_state)
    recorded_groups = []
    recorded_moves = []

    monkeypatch.setattr(client, "group_tracks", lambda tracks, name=None, group=None: recorded_groups.append((tracks, name)) or {
        "status": "group_created",
        "group_name": name,
        "grouped_tracks": tracks
    })
    monkeypatch.setattr(client, "move_track", lambda tracks, target=None, position="after": recorded_moves.append((tracks, target, position)) or {
        "status": "tracks_moved",
        "moved_tracks": [tracks],
        "target_track": target,
        "position": position
    })

    # Test auto_group
    res = executor.execute("organize_tracks", {"auto_group": True})
    assert res["status"] == "success"
    assert len(recorded_groups) == 2  # Drums (Kick, Snare) and Bass (Bass Synth, Sub Bass)

    # Test order
    res_order = executor.execute("organize_tracks", {"order": ["Drums", "Bass", "Synths"]})
    assert res_order["status"] == "success"
    assert len(recorded_moves) == 3
