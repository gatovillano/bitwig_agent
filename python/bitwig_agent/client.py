from __future__ import annotations
from typing import List, Optional, Dict, Any
import httpx
from pydantic import BaseModel, Field

class NoteEvent(BaseModel):
    step: int = Field(..., ge=0, description="Step index (usually in 16th notes: 0 = beat 1, 4 = beat 2, etc.)")
    pitch: int = Field(..., ge=0, le=127, description="MIDI note pitch (0-127, e.g. 60 = Middle C / C4)")
    velocity: int = Field(default=100, ge=1, le=127, description="MIDI velocity (1-127)")
    duration: float = Field(default=1.0, gt=0, description="Note duration in beats (1.0 = quarter note, 4.0 = whole note)")
    channel: int = Field(default=0, ge=0, le=15, description="MIDI channel (0-15)")

class SlotInfo(BaseModel):
    index: int
    hasContent: bool
    isPlaying: bool
    isSelected: bool

class DeviceInfo(BaseModel):
    index: int
    name: str
    type: Optional[str] = None
    preset: Optional[str] = None
    category: Optional[str] = None
    isEnabled: bool = True
    isPlugin: bool = False

class OccupiedClipInfo(BaseModel):
    slot: int
    name: Optional[str] = None
    isPlaying: bool = False
    isSelected: bool = False

class ClipNote(BaseModel):
    step: int
    beat: float
    pitch: int
    name: str
    velocity: int = 100
    duration: float = 1.0
    channel: int = 0

class ClipDetail(BaseModel):
    track: int
    track_name: str
    track_type: Optional[str] = None
    slot: int
    name: Optional[str] = None
    has_content: bool = True
    is_playing: bool = False
    is_selected: bool = False
    is_recording: bool = False
    message: Optional[str] = None
    play_start: float = 0.0
    play_stop: float = 16.0
    loop_enabled: bool = True
    loop_start: float = 0.0
    loop_length: float = 16.0
    shuffle: bool = False
    accent: float = 0.0
    playing_step: int = -1
    notes: List[ClipNote] = Field(default_factory=list)
    notes_count: int = 0

class TrackDetail(BaseModel):
    index: int
    name: str
    type: Optional[str] = None
    volume: Optional[str] = None
    pan: Optional[str] = None
    isGroup: bool = False
    arm: bool = False
    mute: bool = False
    solo: bool = False
    devices: List[DeviceInfo] = Field(default_factory=list)
    occupied_clips: List[OccupiedClipInfo] = Field(default_factory=list)

class TrackInfo(BaseModel):
    index: int
    name: str
    type: Optional[str] = None
    volume: Optional[str] = None
    pan: Optional[str] = None
    isGroup: bool
    arm: bool
    mute: bool
    solo: bool
    devices: List[DeviceInfo] = Field(default_factory=list)
    slots: List[SlotInfo] = Field(default_factory=list)

class ProjectState(BaseModel):
    tempo: float
    isPlaying: bool
    tracks: List[TrackInfo] = Field(default_factory=list)

class BitwigClient:
    """
    Client interface for communicating with Bitwig Studio via the BitwigAgentBridge extension.
    """
    def __init__(self, base_url: str = "http://127.0.0.1:8989", timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def is_connected(self) -> bool:
        try:
            with httpx.Client(timeout=1.0) as client:
                res = client.get(f"{self.base_url}/api/status")
                return res.status_code == 200
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/status")
            res.raise_for_status()
            return res.json()

    def get_project(self) -> ProjectState:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/project")
            res.raise_for_status()
            return ProjectState.model_validate(res.json())

    def play(self) -> Dict[str, Any]:
        return self._post_transport({"action": "play"})

    def stop(self) -> Dict[str, Any]:
        return self._post_transport({"action": "stop"})

    def restart(self) -> Dict[str, Any]:
        return self._post_transport({"action": "restart"})

    def set_tempo(self, bpm: float) -> Dict[str, Any]:
        return self._post_transport({"action": "set_tempo", "tempo": float(bpm)})

    def set_position(self, beats: float) -> Dict[str, Any]:
        return self._post_transport({"action": "set_position", "position": float(beats)})

    def select_track(self, track: int) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/track/select", json={"track": track})
            res.raise_for_status()
            return res.json()

    def create_clip(self, track: int, slot: int = 0, beats: int = 16) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(
                f"{self.base_url}/api/clip/create",
                json={"track": track, "slot": slot, "beats": beats}
            )
            res.raise_for_status()
            return res.json()

    def write_notes(
        self,
        track: int,
        slot: int,
        notes: List[NoteEvent],
        clear: bool = True,
        beats: int = 16
    ) -> Dict[str, Any]:
        payload = {
            "track": track,
            "slot": slot,
            "clear": clear,
            "beats": beats,
            "notes": [n.model_dump() for n in notes]
        }
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/clip/notes", json=payload)
            res.raise_for_status()
            return res.json()

    def clear_clip(self, track: int, slot: int = 0, action: str = "notes") -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(
                f"{self.base_url}/api/clip/clear",
                json={"track": track, "slot": slot, "action": action}
            )
            res.raise_for_status()
            return res.json()

    def launch_clip(self, track: int, slot: int = 0) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(
                f"{self.base_url}/api/clip/launch",
                json={"track": track, "slot": slot}
            )
            res.raise_for_status()
            return res.json()

    def add_instrument(
        self,
        name: Optional[str] = None,
        instrument: str = "polymer",
        position: int = -1,
        track: Optional[int] = None
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "name": name,
            "instrument": instrument,
            "position": position,
        }
        if track is not None:
            payload["track"] = track
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/instrument/add", json=payload)
            res.raise_for_status()
            return res.json()

    def inspect_track(self, track: int | str) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/track/inspect", json={"track": track})
            res.raise_for_status()
            return res.json()

    def inspect_clip(self, track: int | str, slot: int = 0) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(
                f"{self.base_url}/api/clip/inspect",
                json={"track": track, "slot": slot}
            )
            res.raise_for_status()
            return res.json()

    def _post_transport(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/transport", json=payload)
            res.raise_for_status()
            return res.json()
