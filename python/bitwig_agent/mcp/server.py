from __future__ import annotations
from typing import List, Optional, Dict, Any
from mcp.server.mcpserver import MCPServer
from bitwig_agent.client import BitwigClient
from bitwig_agent.llm.tools import ToolExecutor

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
    track: str,
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
    track: str,
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
def control_transport(action: str, tempo: float = 120.0) -> str:
    """
    Controls Bitwig transport: play, stop, restart, or set_tempo.
    """
    res = executor.execute("control_transport", {"action": action, "tempo": tempo})
    import json
    return json.dumps(res, indent=2)

@mcp_server.tool()
def clear_clip(track: str, slot: int = 0, action: str = "notes") -> str:
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
    track: Optional[str] = None
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
def inspect_track(track: str) -> str:
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
def inspect_clip(track: str, slot: int = 0) -> str:
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
def write_notes(
    track: str,
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

def main():
    mcp_server.run(transport="stdio")

if __name__ == "__main__":
    main()
