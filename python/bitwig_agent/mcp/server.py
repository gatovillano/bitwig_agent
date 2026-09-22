import os
import sys
import logging
from typing import List, Optional, Dict, Any, Union
from mcp.server.mcpserver import MCPServer
from bitwig_agent.client import BitwigClient
from bitwig_agent.llm.tools import ToolExecutor

# Setup logging to stderr and log file so standard MCP JSON-RPC on stdout is not polluted
LOG_DIR = os.path.expanduser("~/.gemini/antigravity-cli/logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "bitwig_mcp.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(LOG_FILE, encoding="utf-8")
    ]
)
logger = logging.getLogger("bitwig_agent.mcp")

mcp_server = MCPServer("bitwig-agent")
client = BitwigClient()
executor = ToolExecutor(client)

@mcp_server.tool()
def get_project_context() -> str:
    """Inspects the current Bitwig project: tempo, playing status, and all tracks with their occupied slots."""
    res = executor.execute("get_project_context", {})
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def create_chord_progression(
    track: Union[str, int],
    chords: List[str],
    slot: int = 0,
    beats_per_chord: float = 4.0,
    voicing_style: str = "keyboard",
    rhythm_pattern: str = "sustained",
    include_bass: bool = True,
    humanize: bool = True,
    launch: bool = False
) -> str:
    """
    Generates a smoothly voiced, humanized chord progression and writes it directly
    to a clip on the specified track in Bitwig Studio.

    Args:
        track: Track index (e.g. '0') or track name (e.g. 'Keys', 'Rhodes').
        chords: Chord names, e.g. ['Dm9', 'G13', 'Cmaj9', 'A7alt'].
        slot: Clip launcher slot index (default: 0).
        beats_per_chord: Length in beats per chord (default: 4.0 = 1 bar in 4/4).
        voicing_style: 'keyboard', 'rootless', or 'drop2'.
        rhythm_pattern: 'sustained', 'lofi', 'syncopated', 'quarter_stabs', or 'arpeggio'.
        include_bass: Whether to include bass root notes.
        humanize: Whether to apply micro-timing and velocity humanization.
        launch: Whether to trigger clip playback immediately.
    """
    res = executor.execute("create_chord_progression", {
        "track": track,
        "slot": slot,
        "chords": chords,
        "beats_per_chord": beats_per_chord,
        "voicing_style": voicing_style,
        "rhythm_pattern": rhythm_pattern,
        "include_bass": include_bass,
        "humanize": humanize,
        "launch": launch
    })
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def create_bassline(
    track: Union[str, int],
    chords: List[str],
    slot: int = 0,
    beats_per_chord: float = 4.0,
    style: str = "syncopated",
    launch: bool = False
) -> str:
    """
    Generates a matching bassline for a chord progression on the specified bass track.

    Args:
        track: Track index or name (e.g. 'Bass', 'Sub').
        chords: Chord progression symbols, e.g. ['Dm7', 'G7', 'Cmaj7'].
        slot: Clip slot index (default: 0).
        beats_per_chord: Beats per chord (default: 4.0).
        style: 'root', 'syncopated', or 'walking'.
        launch: Whether to launch playback immediately.
    """
    res = executor.execute("create_bassline", {
        "track": track,
        "slot": slot,
        "chords": chords,
        "beats_per_chord": beats_per_chord,
        "style": style,
        "launch": launch
    })
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def control_transport(action: str, tempo: float = 120.0, position: float = 0.0) -> str:
    """
    Controls Bitwig transport: play, stop, restart, set_tempo, record, stop_record, toggle_record, return_to_arrangement, or set_position.
    """
    res = executor.execute("control_transport", {"action": action, "tempo": tempo, "position": position})
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def clear_clip(track: Union[str, int], slot: int = 0, action: str = "notes") -> str:
    """
    Clears notes from a clip or deletes a clip in Bitwig.
    """
    res = executor.execute("clear_clip", {"track": track, "slot": slot, "action": action})
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def add_instrument_track(
    name: str,
    instrument: str = "polymer",
    position: int = -1,
    track: Optional[Union[str, int]] = None
) -> str:
    """
    Creates a new instrument track or loads a native synth/drum machine/preset into Bitwig Studio.

    Args:
        name: Name for the track (e.g. 'Lead', 'Bass Synth', 'Drums').
        instrument: Instrument type ('polymer', 'polysynth', 'fm-4', 'phase-4', 'sampler', 'drum_machine', 'organ', 'poly_grid', 'instrument_layer') or a preset path.
        position: Position index to insert at (-1 to insert at the end).
        track: Optional existing track index or name to add the instrument to without creating a new track.
    """
    payload = {"name": name, "instrument": instrument, "position": position}
    if track is not None:
        payload["track"] = track
    res = executor.execute("add_instrument_track", payload)
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def inspect_track(track: Union[str, int]) -> str:
    """
    Inspects a specific track in Bitwig Studio to see its detailed composition:
    track type, mix parameters (volume, pan, mute, solo, arm), device chain
    (instruments, synths, VST/CLAP plugins, effects, active presets), and occupied clips.

    Args:
        track: Track index (e.g. '0', '1') or track name (e.g. 'Polymer Pad', 'Keys', 'Bass').
    """
    res = executor.execute("inspect_track", {"track": track})
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def inspect_clip(track: Union[str, int], slot: int = 0) -> str:
    """
    Inspects and visualizes an individual clip in Bitwig Studio:
    playback status, loop length, notes details, and a graphical ASCII piano roll representation.

    Args:
        track: Track index (e.g. '0', '1') or track name (e.g. 'Voices', 'Fossora Pad', 'Bass').
        slot: Clip slot index (0-based, default: 0).
    """
    res = executor.execute("inspect_clip", {"track": track, "slot": slot})
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def inspect_arranger() -> str:
    """
    Inspects the Bitwig Studio Arranger timeline:
    - Playhead position (beats & bars) and project tempo
    - Arranger recording and overdubbing status
    - Arranger loop status (enabled, start beat, duration)
    - Cue markers list (arrangement sections/structure like Intro, Verse, Chorus, Drop, Outro)
    - Currently selected Arranger clip (if any), including playback/loop bounds, notes details, and an ASCII piano roll.
    """
    res = executor.execute("inspect_arranger", {})
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def write_notes(
    track: Union[str, int],
    notes: List[Dict[str, Any]],
    slot: int = 0,
    beats: float = 16.0,
    clear: bool = True,
    launch: bool = False,
    humanize: bool = False
) -> str:
    """
    Writes custom note sequences note-by-note into a clip slot in Bitwig Studio with precise control
    over pitch, timing, duration, velocity, and channel.

    Args:
        track: Track index (e.g. '0', '1') or track name (e.g. 'Lead', 'Piano', 'Bass', 'Drums').
        notes: List of note dicts. Each note can specify 'pitch' (MIDI number 0-127 or name like 'C4', 'F#3'),
               'step' (16th-note step index: 0, 4, 8, etc.) or 'beat' (float: 0.0, 1.0, 1.5),
               'duration' (in beats, default: 1.0), 'velocity' (1-127, default: 100), 'channel' (0-15, default: 0).
        slot: Clip slot index (0-based, default: 0).
        beats: Total clip length in beats (default: 16.0 = 4 bars in 4/4). Will auto-extend if notes exceed this length.
        clear: Whether to clear existing notes in the clip before writing (default: True).
        launch: Whether to trigger clip playback immediately (default: False).
        humanize: Whether to apply subtle humanization to velocities and micro-timing (default: False).
    """
    res = executor.execute("write_notes", {
        "track": track,
        "notes": notes,
        "slot": slot,
        "beats": beats,
        "clear": clear,
        "launch": launch,
        "humanize": humanize
    })
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def launch_scene(scene: int = 0) -> str:
    """
    Launches an entire scene in the Bitwig Clip Launcher (triggers playback across all tracks for that scene row).

    Args:
        scene: Scene index (0-based, default: 0).
    """
    res = executor.execute("launch_scene", {"scene": scene})
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def record_to_arranger(
    sequence: Optional[List[Dict[str, Any]]] = None,
    start_beat: float = 0.0,
    action: str = "record_sequence",
    scene: Optional[int] = None,
    stop_on_finish: bool = True,
    return_to_arrangement: bool = True
) -> str:
    """
    Records scenes or clips into the Bitwig Arranger timeline in real-time.
    Supports executing an automated multi-scene arrangement sequence (timed accurately to project BPM)
    or manual recording control (start, stop, toggle, return_to_arrangement).

    Args:
        sequence: Optional list of sections to record sequentially into the Arranger.
                  Each item must specify 'scene' (int) and optionally 'bars' (e.g. 4.0) or 'beats' (e.g. 16.0).
                  Example: [{"scene": 0, "bars": 4}, {"scene": 1, "bars": 8}, {"scene": 2, "bars": 4}].
        start_beat: Arranger timeline beat position to start recording from (default: 0.0 = bar 1).
        action: 'record_sequence' (default if sequence given), 'start', 'stop', 'toggle', or 'return_to_arrangement'.
        scene: Optional scene index to trigger immediately when action is 'start'.
        stop_on_finish: Whether to stop playback when sequence recording completes (default: True).
        return_to_arrangement: Whether to restore tracks to arrangement playback when recording finishes (default: True).
    """
    payload: Dict[str, Any] = {
        "start_beat": start_beat,
        "action": action,
        "stop_on_finish": stop_on_finish,
        "return_to_arrangement": return_to_arrangement
    }
    if sequence is not None:
        payload["sequence"] = sequence
    if scene is not None:
        payload["scene"] = scene

    res = executor.execute("record_to_arranger", payload)
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def add_audio_effect(
    effect: str = "reverb",
    track: Optional[Union[str, int]] = None,
    position: Union[str, int] = "end",
    create_effect_track: bool = False
) -> str:
    """
    Inserts a native Bitwig audio effect, preset (.bwpreset), or VST/CLAP plugin onto a track's device chain,
    or creates a new Effect/Return track in Bitwig Studio.

    Args:
        effect: Name of the effect (e.g. 'reverb', 'delay+', 'delay-1', 'compressor+', 'eq+', 'eq-5', 'saturator', 'distortion', 'chorus+', 'flanger+', 'phaser+', 'filter+', 'tool', 'peak_limiter') or path to a .bwpreset file.
        track: Track index (e.g. '0', '1') or track name (e.g. 'Keys', 'Bass', 'Master'). Not required if create_effect_track is True.
        position: Position in chain: 'end' (default), 'start', or a 0-based integer index to insert after.
        create_effect_track: If True, creates a dedicated Effect/Return track and loads the effect there.
    """
    payload: Dict[str, Any] = {
        "effect": effect,
        "position": position,
        "create_effect_track": create_effect_track
    }
    if track is not None:
        payload["track"] = track

    res = executor.execute("add_audio_effect", payload)
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def control_device(
    track: Union[str, int],
    device: Union[str, int],
    action: str,
    enabled: Optional[bool] = None
) -> str:
    """
    Controls a device or audio effect in a track's device chain: bypass/enable, toggle bypass, remove, or switch presets.

    Args:
        track: Track index (e.g. '0', '1') or track name (e.g. 'Keys', 'Bass').
        device: Device index (e.g. 0, 1) or device name (e.g. 'Reverb', 'Polymer', 'EQ+').
        action: 'set_enabled', 'toggle', 'delete', 'next_preset', or 'previous_preset'.
        enabled: Target state if action is 'set_enabled' (True = active, False = bypassed).
    """
    payload: Dict[str, Any] = {
        "track": track,
        "device": device,
        "action": action
    }
    if enabled is not None:
        payload["enabled"] = enabled

    res = executor.execute("control_device", payload)
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def set_device_parameter(
    track: Union[str, int],
    device: Union[str, int],
    parameter: Union[str, int],
    value: float,
    page: Optional[str] = None,
    normalized: Optional[bool] = None
) -> str:
    """
    Sets an exact parameter value on a Bitwig device or audio effect (e.g., EQ frequency, gain, Q, filter cutoff, reverb decay).
    Supports matching by parameter name ('Low Freq', 'Gain', 'Frequency', 'Cutoff'), normalized alias ('lowfreq'), substring, or remote control index (0 to 7).

    Args:
        track: Track index (e.g. 0, 4) or track name (e.g. 'Keys', 'Bass', 'Strings').
        device: Device index (e.g. 0, 1) or device name (e.g. 'EQ+', 'Compressor+', 'Reverb').
        parameter: Parameter name ('Low Freq', 'Gain', 'Q', 'Cutoff', 'Resonance', 'Decay') or remote control index ('0'-'7').
        value: Value to set. Hz for frequency/cutoff (e.g. 220.0), dB for gain (e.g. -3.0), float for Q (e.g. 1.5), or 0.0-1.0 for normalized.
        page: Optional remote control page name to switch to before tweaking (e.g. 'Main', 'Band 1', 'EQ').
        normalized: Optional boolean. If True, treats value as normalized between 0.0 and 1.0.
    """
    payload: Dict[str, Any] = {
        "track": track,
        "device": device,
        "parameter": parameter,
        "value": value
    }
    if page:
        payload["page"] = page
    if normalized is not None:
        payload["normalized"] = normalized

    logger.info(f"Executing set_device_parameter: track={track}, device={device}, parameter={parameter}, value={value}, page={page}, normalized={normalized}")
    res = executor.execute("set_device_parameter", payload)
    if "error" in res:
        logger.error(f"set_device_parameter failed: {res}")
    else:
        logger.info(f"set_device_parameter succeeded: {res}")
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def list_audio_effects(category: Optional[str] = None) -> str:
    """
    Lists all available native Bitwig audio effects organized by category (Reverb, Delay, Dynamics, EQ & Filters, Distortion, Modulation, Utility, Spectral).

    Args:
        category: Optional category filter (e.g. 'reverb', 'delay', 'dynamics', 'eq', 'filter', 'distortion', 'modulation', 'utility').
    """
    payload: Dict[str, Any] = {}
    if category is not None:
        payload["category"] = category

    res = executor.execute("list_audio_effects", payload)
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def move_track(
    tracks: Union[List[Union[str, int]], str, int],
    target: Optional[Union[str, int]] = None,
    position: str = "after"
) -> str:
    """
    Moves one or more tracks before or after a target track, or to the start/end of the project.

    Args:
        tracks: Track name/index or list of track names/indices to move.
        target: Target track name or index to place tracks relative to (optional if position is 'start' or 'end').
        position: 'before', 'after' (default), 'start', or 'end'.
    """
    payload = {
        "tracks": tracks if isinstance(tracks, list) else [tracks],
        "position": position
    }
    if target is not None:
        payload["target"] = target
    res = executor.execute("move_track", payload)
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def group_tracks(
    tracks: List[Union[str, int]],
    name: Optional[str] = None,
    group: Optional[Union[str, int]] = None
) -> str:
    """
    Creates a Group Track containing the specified tracks, or moves tracks into an existing group track.

    Args:
        tracks: List of track names or indices to place inside the group.
        name: Name for the new group track (e.g. 'Drums', 'Bass', 'Synths', 'Vocals').
        group: Optional name or index of an existing group track to add tracks into.
    """
    payload: Dict[str, Any] = {"tracks": tracks}
    if name is not None:
        payload["name"] = name
    if group is not None:
        payload["group"] = group
    res = executor.execute("group_tracks", payload)
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def ungroup_track(track: Union[str, int]) -> str:
    """
    Ungroups a Group Track in Bitwig Studio, returning its child tracks to the root level.

    Args:
        track: Name or index of the group track to ungroup.
    """
    res = executor.execute("ungroup_track", {"track": track})
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def organize_tracks(
    order: Optional[List[str]] = None,
    groups: Optional[List[Dict[str, Any]]] = None,
    auto_group: bool = False
) -> str:
    """
    Intelligently organizes, groups, and reorders project tracks.
    Can execute custom grouping plans, reorder tracks in bulk, or automatically group and arrange tracks by instrument family (Drums, Bass, Synths, FX).

    Args:
        order: Ordered list of track/group names to place in top-to-bottom sequence (e.g. ['Drums', 'Bass', 'Keys', 'Leads', 'FX', 'Master']).
        groups: List of group objects to create, e.g. [{"name": "Drums", "tracks": ["Kick", "Snare", "HiHats"]}].
        auto_group: If true, automatically detects and groups tracks by musical role based on device types and track names.
    """
    payload: Dict[str, Any] = {"auto_group": auto_group}
    if order is not None:
        payload["order"] = order
    if groups is not None:
        payload["groups"] = groups
    res = executor.execute("organize_tracks", payload)
    import json
    return json.dumps(res, indent=2)

def main():
    mcp_server.run(transport="stdio")

if __name__ == "__main__":
    main()
