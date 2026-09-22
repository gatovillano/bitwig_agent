from __future__ import annotations
import json
import logging
import math
from typing import List, Dict, Any, Optional
from bitwig_agent.client import BitwigClient, NoteEvent

logger = logging.getLogger("bitwig_agent.tools")
from bitwig_agent.theory import (
    build_chord_progression,
    build_bassline,
    render_ascii_piano_roll,
    note_name_to_pitch,
    pitch_to_note_name,
    humanize_events
)

BITWIG_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_project_context",
            "description": "Inspects current Bitwig project state: tempo, playing status, and all available tracks with their clip slots.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_chord_progression",
            "description": "Generates a musically voiced, humanized chord progression and writes it directly to a clip on the specified track in Bitwig.",
            "parameters": {
                "type": "object",
                "properties": {
                    "track": {
                        "type": "string",
                        "description": "Track index (e.g. '0', '1') or track name (e.g. 'Keys', 'Rhodes', 'Piano')."
                    },
                    "slot": {
                        "type": "integer",
                        "description": "Clip launcher slot index (0-based, default: 0).",
                        "default": 0
                    },
                    "chords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of chord symbols, e.g. ['Dm9', 'G13', 'Cmaj9', 'A7alt']."
                    },
                    "beats_per_chord": {
                        "type": "number",
                        "description": "Duration in beats for each chord (default: 4.0 = 1 measure in 4/4).",
                        "default": 4.0
                    },
                    "voicing_style": {
                        "type": "string",
                        "enum": ["keyboard", "rootless", "drop2"],
                        "description": "Keyboard voicing algorithm to apply (default: 'keyboard').",
                        "default": "keyboard"
                    },
                    "rhythm_pattern": {
                        "type": "string",
                        "enum": ["sustained", "lofi", "syncopated", "quarter_stabs", "arpeggio"],
                        "description": "Rhythmic groove pattern for the chords (default: 'sustained').",
                        "default": "sustained"
                    },
                    "include_bass": {
                        "type": "boolean",
                        "description": "Whether to include a lower bass root note in the chord clip (default: true).",
                        "default": True
                    },
                    "humanize": {
                        "type": "boolean",
                        "description": "Whether to apply dynamic velocity contours and micro-timing (default: true).",
                        "default": True
                    },
                    "launch": {
                        "type": "boolean",
                        "description": "Whether to launch the clip immediately after writing (default: false).",
                        "default": False
                    }
                },
                "required": ["track", "chords"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_bassline",
            "description": "Generates a dedicated bassline track matching a chord progression and writes it to a clip in Bitwig.",
            "parameters": {
                "type": "object",
                "properties": {
                    "track": {
                        "type": "string",
                        "description": "Track index or name for the bass track (e.g. 'Bass', 'Sub')."
                    },
                    "slot": {
                        "type": "integer",
                        "description": "Clip launcher slot index (0-based, default: 0).",
                        "default": 0
                    },
                    "chords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of chord symbols to follow, e.g. ['Dm7', 'G7', 'Cmaj7']."
                    },
                    "beats_per_chord": {
                        "type": "number",
                        "description": "Duration in beats for each chord (default: 4.0).",
                        "default": 4.0
                    },
                    "style": {
                        "type": "string",
                        "enum": ["root", "syncopated", "walking"],
                        "description": "Bassline style (default: 'syncopated').",
                        "default": "syncopated"
                    },
                    "launch": {
                        "type": "boolean",
                        "description": "Whether to launch the clip immediately (default: false).",
                        "default": False
                    }
                },
                "required": ["track", "chords"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_transport",
            "description": "Controls Bitwig transport: play, stop, restart, set_tempo, record, return_to_arrangement, or set_position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["play", "stop", "restart", "set_tempo", "record", "stop_record", "toggle_record", "return_to_arrangement", "set_position"],
                        "description": "Transport action to perform."
                    },
                    "tempo": {
                        "type": "number",
                        "description": "New tempo in BPM (required if action is 'set_tempo')."
                    },
                    "position": {
                        "type": "number",
                        "description": "Playback position in beats (required if action is 'set_position')."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clear_clip",
            "description": "Clears notes or deletes a clip slot in Bitwig.",
            "parameters": {
                "type": "object",
                "properties": {
                    "track": {
                        "type": "string",
                        "description": "Track index or name."
                    },
                    "slot": {
                        "type": "integer",
                        "description": "Slot index (default: 0).",
                        "default": 0
                    },
                    "action": {
                        "type": "string",
                        "enum": ["notes", "delete"],
                        "description": "'notes' to clear notes inside the clip, 'delete' to remove the clip object entirely.",
                        "default": "notes"
                    }
                },
                "required": ["track"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_instrument_track",
            "description": "Creates a new instrument track or loads a native synth/drum machine/preset into Bitwig Studio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the track (e.g. 'Lead', 'Bass', 'Drums', 'Chords')."
                    },
                    "instrument": {
                        "type": "string",
                        "enum": [
                            "polymer",
                            "polysynth",
                            "fm-4",
                            "phase-4",
                            "sampler",
                            "drum_machine",
                            "organ",
                            "poly_grid",
                            "instrument_layer"
                        ],
                        "description": "Instrument to load (default: 'polymer'). Can also be a preset path (.bwpreset) or Bitwig device UUID.",
                        "default": "polymer"
                    },
                    "position": {
                        "type": "integer",
                        "description": "Track index position to insert at (-1 to insert at the end).",
                        "default": -1
                    },
                    "track": {
                        "type": "string",
                        "description": "Optional existing track index or name to add the instrument to without creating a new track."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_track",
            "description": "Inspects a specific track in Bitwig Studio to see its detailed composition: channel properties (volume, pan, mute, solo, arm, type), device chain (instruments, synths, VST/CLAP plugins, effects, active presets), and occupied clips.",
            "parameters": {
                "type": "object",
                "properties": {
                    "track": {
                        "type": "string",
                        "description": "Track index (e.g. '0', '1') or track name (e.g. 'Polymer Pad', 'Keys', 'Bass')."
                    }
                },
                "required": ["track"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_clip",
            "description": "Inspects and visualizes an individual clip in Bitwig Studio: clip slot status (playing, selected, recording), loop/timeline bounds, note details (pitch, step, velocity, duration), musical pattern analysis, and an ASCII piano roll visualization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "track": {
                        "type": "string",
                        "description": "Track index (e.g. '0', '1') or track name (e.g. 'Voices', 'Fossora Pad', 'Bass')."
                    },
                    "slot": {
                        "type": "integer",
                        "description": "Clip launcher slot index (0-based, default: 0).",
                        "default": 0
                    }
                },
                "required": ["track"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_arranger",
            "description": "Inspects the Bitwig Studio Arranger timeline: playhead position (beats & bars), arranger loop boundaries, recording status, cue markers (song sections/structure like Intro, Verse, Chorus), and note details + ASCII piano roll of any currently selected Arranger clip.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_notes",
            "description": "Writes custom note sequences note-by-note into a clip slot in Bitwig Studio with precise control over pitch, timing, duration, velocity, and channel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "track": {
                        "type": "string",
                        "description": "Track index (e.g. '0', '1') or track name (e.g. 'Lead', 'Piano', 'Bass', 'Drums')."
                    },
                    "slot": {
                        "type": "integer",
                        "description": "Clip launcher slot index (0-based, default: 0).",
                        "default": 0
                    },
                    "notes": {
                        "type": "array",
                        "description": "List of note events to write to the clip.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "pitch": {
                                    "description": "MIDI pitch number (0-127, e.g. 60) or note name with octave (e.g. 'C4', 'F#3', 'Bb2', 'Db5')."
                                },
                                "step": {
                                    "type": "integer",
                                    "description": "16th-note step index (0 = beat 1, 4 = beat 2, etc.). Optional if beat is provided."
                                },
                                "beat": {
                                    "type": "number",
                                    "description": "Start position in beats (e.g. 0.0, 0.5, 1.25, 2.0). Optional if step is provided."
                                },
                                "duration": {
                                    "type": "number",
                                    "description": "Duration in beats (default: 1.0 = quarter note, 0.25 = 16th note, 0.5 = 8th note).",
                                    "default": 1.0
                                },
                                "velocity": {
                                    "type": "integer",
                                    "description": "MIDI velocity (1-127, default: 100).",
                                    "default": 100
                                },
                                "channel": {
                                    "type": "integer",
                                    "description": "MIDI channel (0-15, default: 0).",
                                    "default": 0
                                }
                            },
                            "required": ["pitch"]
                        }
                    },
                    "beats": {
                        "type": "number",
                        "description": "Total clip length in beats (default: 16 = 4 bars in 4/4). Will auto-extend if notes exceed this length.",
                        "default": 16
                    },
                    "clear": {
                        "type": "boolean",
                        "description": "Whether to clear existing notes in the clip slot before writing (default: true).",
                        "default": True
                    },
                    "launch": {
                        "type": "boolean",
                        "description": "Whether to launch the clip immediately after writing (default: false).",
                        "default": False
                    },
                    "humanize": {
                        "type": "boolean",
                        "description": "Whether to apply subtle humanization to velocities and micro-timing (default: false).",
                        "default": False
                    }
                },
                "required": ["track", "notes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "launch_scene",
            "description": "Launches an entire scene in the Clip Launcher (triggers playback across all tracks for that scene row).",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene": {
                        "type": "integer",
                        "description": "Scene index to launch (0-based, default: 0).",
                        "default": 0
                    }
                },
                "required": ["scene"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_to_arranger",
            "description": "Records scenes or clips into the Bitwig Arranger timeline in real-time. Supports executing an automated multi-scene arrangement sequence (timed accurately to project BPM) or manual recording control (start, stop, toggle, return_to_arrangement).",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {
                        "type": "array",
                        "description": "List of song sections to record sequentially into the Arranger. Each item defines 'scene' (int) and either 'bars' (float, e.g. 4.0) or 'beats' (float, e.g. 16.0).",
                        "items": {
                            "type": "object",
                            "properties": {
                                "scene": {"type": "integer", "description": "Scene index (0-based)."},
                                "bars": {"type": "number", "description": "Length of this section in bars/measures (4 beats per bar)."},
                                "beats": {"type": "number", "description": "Length of this section in beats."}
                            },
                            "required": ["scene"]
                        }
                    },
                    "start_beat": {
                        "type": "number",
                        "description": "Arranger timeline beat position to start recording from (default: 0.0 = bar 1).",
                        "default": 0.0
                    },
                    "action": {
                        "type": "string",
                        "enum": ["record_sequence", "start", "stop", "toggle", "return_to_arrangement"],
                        "description": "Action to perform. Default is 'record_sequence' if sequence is provided, otherwise 'start'.",
                        "default": "record_sequence"
                    },
                    "scene": {
                        "type": "integer",
                        "description": "Scene index to launch immediately if action is 'start'."
                    },
                    "stop_on_finish": {
                        "type": "boolean",
                        "description": "Whether to stop playback when sequence recording finishes (default: true).",
                        "default": True
                    },
                    "return_to_arrangement": {
                        "type": "boolean",
                        "description": "Whether to restore track playback to the Arranger timeline when recording finishes (default: true).",
                        "default": True
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_audio_effect",
            "description": "Inserts a native Bitwig audio effect, preset (.bwpreset), or VST/CLAP plugin onto a track's device chain, or creates a new Effect/Return track.",
            "parameters": {
                "type": "object",
                "properties": {
                    "effect": {
                        "type": "string",
                        "description": "Name of the audio effect (e.g. 'reverb', 'delay+', 'delay-1', 'compressor+', 'eq+', 'eq-5', 'saturator', 'distortion', 'chorus+', 'flanger+', 'phaser+', 'filter+', 'tool', 'peak_limiter') or path to a .bwpreset file.",
                        "default": "reverb"
                    },
                    "track": {
                        "type": "string",
                        "description": "Track index (e.g. '0', '1') or track name (e.g. 'Keys', 'Bass', 'Master'). Not required if create_effect_track is true."
                    },
                    "position": {
                        "type": "string",
                        "description": "Position in the device chain: 'end' (default), 'start', or a 0-based device index to insert after.",
                        "default": "end"
                    },
                    "create_effect_track": {
                        "type": "boolean",
                        "description": "Whether to create a new Effect/Return track in Bitwig and load the effect there (default: false).",
                        "default": False
                    }
                },
                "required": ["effect"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_device",
            "description": "Controls a device or audio effect on a track: enable/disable (bypass), toggle bypass, remove/delete, or navigate presets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "track": {
                        "type": "string",
                        "description": "Track index or track name (e.g. '0', 'Keys', 'Bass')."
                    },
                    "device": {
                        "type": "string",
                        "description": "Device index in the track chain (e.g. '0', '1') or device name (e.g. 'Reverb', 'Polymer', 'EQ+')."
                    },
                    "action": {
                        "type": "string",
                        "enum": ["set_enabled", "toggle", "delete", "next_preset", "previous_preset"],
                        "description": "Action to perform on the device."
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Target enabled state if action is 'set_enabled' (true = active, false = bypassed)."
                    }
                },
                "required": ["track", "device", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_device_parameter",
            "description": "Sets an exact parameter value on a Bitwig device or audio effect (e.g., EQ frequency, gain, Q, filter cutoff, reverb decay). Use this for precise EQ and device tweaking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "track": {
                        "type": "string",
                        "description": "Track index or name (e.g. '0', 'Keys', 'Bass')."
                    },
                    "device": {
                        "type": "string",
                        "description": "Device index (e.g. '0', '1') or device name (e.g. 'EQ+', 'Reverb', 'Filter+')."
                    },
                    "parameter": {
                        "type": "string",
                        "description": "Parameter name (e.g. 'Low Freq', 'Gain', 'Q', 'Cutoff', 'Resonance', 'Decay') or remote control index ('0'-'7'). Flexible matching supported."
                    },
                    "value": {
                        "type": "number",
                        "description": "Value to set. Use Hz for frequency, dB for gain, float for Q, or 0.0-1.0 if normalized."
                    },
                    "page": {
                        "type": "string",
                        "description": "Optional remote control page name to switch to before setting parameter."
                    },
                    "normalized": {
                        "type": "boolean",
                        "description": "If true, treats value as normalized (0.0 to 1.0)."
                    }
                },
                "required": ["track", "device", "parameter", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_audio_effects",
                "description": "Lists all available native Bitwig audio effects organized by category (Reverb, Delay, Dynamics, EQ & Filters, Distortion, Modulation, Utility, Spectral).",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (e.g. 'reverb', 'delay', 'dynamics', 'eq', 'filter', 'distortion', 'modulation', 'utility')."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_track",
            "description": "Moves one or more tracks before or after a target track, or to the start/end of the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of track names or indices to move. Can also be a single track name or index."
                    },
                    "target": {
                        "type": "string",
                        "description": "Target track name or index to position relative to (not needed if position is 'start' or 'end')."
                    },
                    "position": {
                        "type": "string",
                        "enum": ["before", "after", "start", "end"],
                        "description": "Where to place the tracks: 'before', 'after' (default), 'start', or 'end'.",
                        "default": "after"
                    }
                },
                "required": ["tracks"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "group_tracks",
            "description": "Creates a Group Track containing the specified tracks, or moves tracks into an existing group, with an optional custom name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of track names or indices to place in the group."
                    },
                    "name": {
                        "type": "string",
                        "description": "Name for the new group track (e.g. 'Drums', 'Bass', 'Synths', 'Vocals')."
                    },
                    "group": {
                        "type": "string",
                        "description": "Optional name or index of an existing group track to move tracks into."
                    }
                },
                "required": ["tracks"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ungroup_track",
            "description": "Ungroups a Group Track in Bitwig Studio, bringing its child tracks back to the root level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "track": {
                        "type": "string",
                        "description": "Name or index of the group track to ungroup."
                    }
                },
                "required": ["track"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "organize_tracks",
            "description": "Intelligently organizes, groups, and reorders project tracks. Can execute custom grouping plans, reorder tracks in bulk, or automatically group and arrange tracks by instrument family (Drums, Bass, Synths, FX).",
            "parameters": {
                "type": "object",
                "properties": {
                    "order": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ordered list of track/group names to place in top-to-bottom sequence (e.g. ['Drums', 'Bass', 'Keys', 'Leads', 'FX', 'Master'])."
                    },
                    "groups": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Name of the group (e.g. 'Drums')"},
                                "tracks": {"type": "array", "items": {"type": "string"}, "description": "Track names/indices to include"}
                            },
                            "required": ["name", "tracks"]
                        },
                        "description": "List of groups to create, each with its name and constituent tracks."
                    },
                    "auto_group": {
                        "type": "boolean",
                        "description": "If true, automatically detects and groups tracks by musical role (Drums, Bass, Synths/Keys, FX) based on device types and track names.",
                        "default": False
                    }
                },
                "required": []
            }
        }
    }
]

AUDIO_EFFECTS_CATALOG: Dict[str, List[str]] = {
    "Reverb": ["Reverb"],
    "Delay": ["Delay+", "Delay-1", "Delay-2", "Delay-4"],
    "Dynamics": ["Compressor", "Compressor+", "Dynamics", "Gate", "Peak Limiter", "De-Esser", "Transient Control"],
    "EQ & Filter": ["EQ+", "EQ-5", "EQ-2", "EQ-DJ", "Filter", "Filter+", "Ladder", "Sweep", "Comb", "Resonator Bank", "Tilt", "Focus", "Sculpt"],
    "Distortion & Color": ["Saturator", "Distortion", "Amp", "Bit-8", "Over"],
    "Modulation": ["Chorus", "Chorus+", "Flanger", "Flanger+", "Phaser", "Phaser+", "Tremolo", "Rotary"],
    "Utility & Spatial": ["Tool", "Dual Pan", "Time Shift", "Pitch Shifter", "Freq Shifter", "Freq Shifter+", "Ring-Mod", "Blur", "Treemonster", "Vocoder", "Spectrum", "Oscilloscope"]
}

class ToolExecutor:
    """
    Executes tool calls against the BitwigClient and Music Theory Engine.
    """
    def __init__(self, client: BitwigClient):
        self.client = client

    def _resolve_track_index(self, track_ident: str | int) -> int:
        if isinstance(track_ident, int):
            return track_ident
        if track_ident.isdigit():
            return int(track_ident)

        # Search by name in project
        try:
            proj = self.client.get_project()
            ident_lower = track_ident.lower().strip()
            for t in proj.tracks:
                if t.name.lower().strip() == ident_lower:
                    return t.index
                if ident_lower in t.name.lower():
                    return t.index
        except Exception:
            pass
        return 0

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "get_project_context":
            if not self.client.is_connected():
                return {
                    "error": "Bitwig Agent Bridge is not connected.",
                    "hint": "Make sure Bitwig Studio is running and the 'Bitwig Agent Bridge' controller extension is added under Settings -> Controllers."
                }
            proj = self.client.get_project()
            return {
                "tempo": proj.tempo,
                "isPlaying": proj.isPlaying,
                "tracks": [
                    {
                        "index": t.index,
                        "name": t.name,
                        "arm": t.arm,
                        "mute": t.mute,
                        "solo": t.solo,
                        "occupied_slots": [s.index for s in t.slots if s.hasContent]
                    }
                    for t in proj.tracks
                ]
            }

        elif tool_name == "create_chord_progression":
            track_idx = self._resolve_track_index(arguments.get("track", 0))
            slot_idx = int(arguments.get("slot", 0))
            chords = arguments.get("chords", [])
            beats_per_chord = float(arguments.get("beats_per_chord", 4.0))
            voicing_style = arguments.get("voicing_style", "keyboard")
            rhythm_pattern = arguments.get("rhythm_pattern", "sustained")
            include_bass = bool(arguments.get("include_bass", True))
            humanize = bool(arguments.get("humanize", True))
            launch = bool(arguments.get("launch", False))

            events = build_chord_progression(
                chords=chords,
                beats_per_chord=beats_per_chord,
                voicing_style=voicing_style,
                rhythm_pattern=rhythm_pattern,
                include_bass=include_bass,
                humanize=humanize
            )

            total_beats = int(len(chords) * beats_per_chord)
            res = self.client.write_notes(
                track=track_idx,
                slot=slot_idx,
                notes=events,
                clear=True,
                beats=max(4, total_beats)
            )

            if launch:
                self.client.launch_clip(track=track_idx, slot=slot_idx)

            return {
                "status": "success",
                "track": track_idx,
                "slot": slot_idx,
                "chords": chords,
                "total_notes": len(events),
                "total_beats": total_beats,
                "bitwig_response": res
            }

        elif tool_name == "create_bassline":
            track_idx = self._resolve_track_index(arguments.get("track", 0))
            slot_idx = int(arguments.get("slot", 0))
            chords = arguments.get("chords", [])
            beats_per_chord = float(arguments.get("beats_per_chord", 4.0))
            style = arguments.get("style", "syncopated")
            launch = bool(arguments.get("launch", False))

            events = build_bassline(
                chords=chords,
                beats_per_chord=beats_per_chord,
                style=style
            )

            total_beats = int(len(chords) * beats_per_chord)
            res = self.client.write_notes(
                track=track_idx,
                slot=slot_idx,
                notes=events,
                clear=True,
                beats=max(4, total_beats)
            )

            if launch:
                self.client.launch_clip(track=track_idx, slot=slot_idx)

            return {
                "status": "success",
                "track": track_idx,
                "slot": slot_idx,
                "style": style,
                "total_notes": len(events),
                "bitwig_response": res
            }

        elif tool_name == "control_transport":
            action = arguments.get("action")
            if action == "play":
                return self.client.play()
            elif action == "stop":
                return self.client.stop()
            elif action == "restart":
                return self.client.restart()
            elif action == "set_tempo":
                tempo = float(arguments.get("tempo", 120.0))
                return self.client.set_tempo(tempo)
            elif action in ("record", "start_record"):
                return self.client.start_record()
            elif action == "stop_record":
                return self.client.stop_record()
            elif action == "toggle_record":
                return self.client.toggle_record()
            elif action == "return_to_arrangement":
                return self.client.return_to_arrangement()
            elif action == "set_position":
                pos = float(arguments.get("position", 0.0))
                return self.client.set_position(pos)
            return {"error": f"Unknown transport action: {action}"}

        elif tool_name == "clear_clip":
            track_idx = self._resolve_track_index(arguments.get("track", 0))
            slot_idx = int(arguments.get("slot", 0))
            action = arguments.get("action", "notes")
            return self.client.clear_clip(track=track_idx, slot=slot_idx, action=action)

        elif tool_name == "add_instrument_track":
            name = arguments.get("name")
            instrument = arguments.get("instrument", "polymer")
            position = int(arguments.get("position", -1))
            track_ident = arguments.get("track")
            track_idx = self._resolve_track_index(track_ident) if track_ident is not None else None
            return self.client.add_instrument(
                name=name,
                instrument=instrument,
                position=position,
                track=track_idx
            )

        elif tool_name == "inspect_track":
            track_ident = arguments.get("track", "0")
            track_idx = self._resolve_track_index(track_ident)
            try:
                return self.client.inspect_track(track_idx)
            except Exception as e:
                return {
                    "error": f"Failed to inspect track '{track_ident}': {str(e)}",
                    "hint": "Check if Bitwig is running and the track exists."
                }

        elif tool_name == "inspect_clip":
            track_ident = arguments.get("track", "0")
            slot_idx = int(arguments.get("slot", 0))
            track_idx = self._resolve_track_index(track_ident)
            try:
                clip_res = self.client.inspect_clip(track=track_idx, slot=slot_idx)
                if isinstance(clip_res, dict):
                    clip_res["piano_roll"] = render_ascii_piano_roll(clip_res)
                return clip_res
            except Exception as e:
                return {
                    "error": f"Failed to inspect clip on track '{track_ident}' slot {slot_idx}: {str(e)}",
                    "hint": "Check if Bitwig is running and the clip exists."
                }

        elif tool_name == "inspect_arranger":
            try:
                arr_res = self.client.inspect_arranger()
                if isinstance(arr_res, dict):
                    sel_clip = arr_res.get("selected_clip")
                    if isinstance(sel_clip, dict):
                        sel_clip["piano_roll"] = render_ascii_piano_roll(sel_clip)
                return arr_res
            except Exception as e:
                return {
                    "error": f"Failed to inspect arranger: {str(e)}",
                    "hint": "Check if Bitwig is running and the Bitwig Agent extension is active."
                }

        elif tool_name == "write_notes":
            track_ident = arguments.get("track", 0)
            track_idx = self._resolve_track_index(track_ident)
            slot_idx = int(arguments.get("slot", 0))
            raw_notes = arguments.get("notes", [])
            beats_arg = arguments.get("beats", 16)
            beats = int(beats_arg) if beats_arg else 16
            clear = bool(arguments.get("clear", True))
            launch = bool(arguments.get("launch", False))
            humanize = bool(arguments.get("humanize", False))

            note_events: List[NoteEvent] = []
            max_end_beat = 0.0

            for n in raw_notes:
                raw_pitch = n.get("pitch")
                if raw_pitch is None:
                    continue
                if isinstance(raw_pitch, str):
                    p_num = note_name_to_pitch(raw_pitch)
                    if p_num is None:
                        if raw_pitch.isdigit():
                            p_num = int(raw_pitch)
                        else:
                            return {"error": f"Invalid pitch note name or number: '{raw_pitch}'"}
                else:
                    p_num = int(raw_pitch)

                pitch = max(0, min(127, p_num))

                if "step" in n and n["step"] is not None:
                    step = int(n["step"])
                elif "beat" in n and n["beat"] is not None:
                    step = int(round(float(n["beat"]) * 4.0))
                elif "start_beat" in n and n["start_beat"] is not None:
                    step = int(round(float(n["start_beat"]) * 4.0))
                else:
                    step = 0
                step = max(0, step)

                if "duration" in n and n["duration"] is not None:
                    dur = float(n["duration"])
                elif "duration_steps" in n and n["duration_steps"] is not None:
                    dur = float(n["duration_steps"]) / 4.0
                else:
                    dur = 1.0
                dur = max(0.05, dur)

                vel = int(n.get("velocity", 100))
                vel = max(1, min(127, vel))

                chan = int(n.get("channel", 0))
                chan = max(0, min(15, chan))

                note_events.append(NoteEvent(
                    step=step,
                    pitch=pitch,
                    velocity=vel,
                    duration=dur,
                    channel=chan
                ))

                note_end_beat = (step / 4.0) + dur
                if note_end_beat > max_end_beat:
                    max_end_beat = note_end_beat

            if humanize and note_events:
                note_events = humanize_events(note_events)

            if max_end_beat > beats:
                beats = max(beats, int(math.ceil(max_end_beat / 4.0) * 4))

            res = self.client.write_notes(
                track=track_idx,
                slot=slot_idx,
                notes=note_events,
                clear=clear,
                beats=beats
            )

            if launch:
                self.client.launch_clip(track=track_idx, slot=slot_idx)

            piano_roll = render_ascii_piano_roll({
                "track": track_idx,
                "slot": slot_idx,
                "loop_length": float(beats),
                "notes": [
                    {
                        "step": ev.step,
                        "pitch": ev.pitch,
                        "velocity": ev.velocity,
                        "duration": ev.duration,
                        "channel": ev.channel,
                        "name": pitch_to_note_name(ev.pitch)
                    }
                    for ev in note_events
                ]
            })

            return {
                "status": "success",
                "track": track_idx,
                "slot": slot_idx,
                "total_notes": len(note_events),
                "beats": beats,
                "piano_roll": piano_roll,
                "bitwig_response": res
            }

        elif tool_name == "launch_scene":
            scene_idx = int(arguments.get("scene", 0))
            res = self.client.launch_scene(scene_idx)
            return {
                "status": "success",
                "scene": scene_idx,
                "bitwig_response": res
            }

        elif tool_name == "record_to_arranger":
            action = arguments.get("action")
            sequence = arguments.get("sequence")
            if not action:
                action = "record_sequence" if sequence else "start"

            if action == "start":
                start_beat = float(arguments.get("start_beat", 0.0))
                self.client.set_position(start_beat)
                record_res = self.client.start_record()
                scene_to_launch = arguments.get("scene")
                if scene_to_launch is not None:
                    self.client.launch_scene(int(scene_to_launch))
                return {
                    "status": "recording_started",
                    "start_beat": start_beat,
                    "scene_launched": scene_to_launch,
                    "bitwig_response": record_res
                }

            elif action == "stop":
                self.client.stop_record()
                if arguments.get("stop_on_finish", True):
                    self.client.stop()
                if arguments.get("return_to_arrangement", True):
                    self.client.return_to_arrangement()
                return {
                    "status": "recording_stopped",
                    "returned_to_arrangement": bool(arguments.get("return_to_arrangement", True))
                }

            elif action == "toggle":
                return self.client.toggle_record()

            elif action == "return_to_arrangement":
                return self.client.return_to_arrangement()

            elif action == "record_sequence":
                if not sequence:
                    return {"error": "A 'sequence' list of scenes with durations must be provided for 'record_sequence'."}

                import time

                try:
                    proj = self.client.get_project()
                    bpm = proj.tempo if proj.tempo > 0 else 120.0
                except Exception:
                    bpm = 120.0
                seconds_per_beat = 60.0 / bpm

                start_beat = float(arguments.get("start_beat", 0.0))
                self.client.set_position(start_beat)
                self.client.start_record()

                recorded_sections = []
                current_beat = start_beat

                for idx, item in enumerate(sequence):
                    scene_num = int(item.get("scene", 0))
                    if "bars" in item and item["bars"] is not None:
                        section_beats = float(item["bars"]) * 4.0
                    elif "beats" in item and item["beats"] is not None:
                        section_beats = float(item["beats"])
                    else:
                        section_beats = 16.0

                    section_seconds = section_beats * seconds_per_beat
                    self.client.launch_scene(scene_num)

                    recorded_sections.append({
                        "order": idx + 1,
                        "scene": scene_num,
                        "start_beat": current_beat,
                        "end_beat": current_beat + section_beats,
                        "beats": section_beats,
                        "bars": section_beats / 4.0,
                        "duration_seconds": round(section_seconds, 2)
                    })

                    current_beat += section_beats
                    time.sleep(section_seconds)

                self.client.stop_record()

                if arguments.get("stop_on_finish", True):
                    self.client.stop()

                if arguments.get("return_to_arrangement", True):
                    self.client.return_to_arrangement()

                total_beats = current_beat - start_beat
                return {
                    "status": "completed",
                    "bpm": bpm,
                    "start_beat": start_beat,
                    "end_beat": current_beat,
                    "total_beats": total_beats,
                    "total_bars": total_beats / 4.0,
                    "sections": recorded_sections,
                    "returned_to_arrangement": bool(arguments.get("return_to_arrangement", True))
                }

            return {"error": f"Unknown record action: {action}"}

        elif tool_name == "add_audio_effect":
            effect = arguments.get("effect", "reverb")
            pos_arg = arguments.get("position", "end")
            create_effect_track = bool(arguments.get("create_effect_track", False))
            track_ident = arguments.get("track")
            track_idx = None
            if not create_effect_track:
                track_idx = self._resolve_track_index(track_ident if track_ident is not None else 0)

            position = pos_arg
            if isinstance(pos_arg, str) and pos_arg.isdigit():
                position = int(pos_arg)

            return self.client.add_effect(
                track=track_idx,
                effect=effect,
                position=position,
                create_effect_track=create_effect_track
            )

        elif tool_name == "control_device":
            track_ident = arguments.get("track", 0)
            track_idx = self._resolve_track_index(track_ident)
            device_ident = arguments.get("device", 0)
            action = arguments.get("action", "toggle")
            enabled = arguments.get("enabled")

            return self.client.control_device(
                track=track_idx,
                device=device_ident,
                action=action,
                enabled=enabled
            )

        elif tool_name == "set_device_parameter":
            track_ident = arguments.get("track", 0)
            track_idx = self._resolve_track_index(track_ident)
            device_ident = arguments.get("device", 0)
            parameter = arguments.get("parameter")
            value = float(arguments.get("value", 0.0))

            if not parameter:
                return {"error": "Missing 'parameter' name."}

            page = arguments.get("page")
            normalized = arguments.get("normalized")

            return self.client.set_device_parameter(
                track=track_idx,
                device=device_ident,
                parameter=parameter,
                value=value,
                page=page,
                normalized=normalized
            )

        elif tool_name == "list_audio_effects":
            cat_filter = arguments.get("category")
            if cat_filter:
                q = cat_filter.strip().lower()
                filtered = {
                    cat: effects for cat, effects in AUDIO_EFFECTS_CATALOG.items()
                    if q in cat.lower() or any(q in e.lower() for e in effects)
                }
                return {"categories": filtered if filtered else AUDIO_EFFECTS_CATALOG}
            return {"categories": AUDIO_EFFECTS_CATALOG}

        elif tool_name == "move_track":
            tracks_arg = arguments.get("tracks")
            if tracks_arg is None:
                tracks_arg = arguments.get("track")
            if tracks_arg is None:
                return {"error": "Missing 'tracks' parameter."}
            target = arguments.get("target")
            position = arguments.get("position", "after")
            res = self.client.move_track(tracks=tracks_arg, target=target, position=position)
            return {
                "status": "success",
                "message": f"Moved track(s) {res.get('moved_tracks', tracks_arg)} {position} {res.get('target_track', target)}",
                "bitwig_response": res
            }

        elif tool_name == "group_tracks":
            tracks_arg = arguments.get("tracks")
            if tracks_arg is None:
                tracks_arg = arguments.get("track")
            if not tracks_arg:
                return {"error": "Missing 'tracks' parameter for group_tracks."}
            if not isinstance(tracks_arg, list):
                tracks_arg = [tracks_arg]
            name = arguments.get("name")
            group = arguments.get("group")
            res = self.client.group_tracks(tracks=tracks_arg, name=name, group=group)
            return {
                "status": "success",
                "message": f"Grouped tracks {res.get('grouped_tracks', tracks_arg)} into '{res.get('group_name', name)}'",
                "bitwig_response": res
            }

        elif tool_name == "ungroup_track":
            track_ident = arguments.get("track")
            if track_ident is None:
                return {"error": "Missing 'track' parameter for ungroup_track."}
            res = self.client.ungroup_track(track=track_ident)
            return {
                "status": "success",
                "message": f"Ungrouped track '{res.get('track', track_ident)}'",
                "bitwig_response": res
            }

        elif tool_name == "organize_tracks":
            import time
            results = []

            # 1. Handle auto_group
            if arguments.get("auto_group", False):
                try:
                    proj = self.client.get_project()
                    categories = {
                        "Drums": [],
                        "Bass": [],
                        "Synths": [],
                        "FX": []
                    }
                    for t in proj.tracks:
                        if t.type == "Master" or t.isGroup:
                            continue
                        name_low = t.name.lower()
                        dev_names = [d.name.lower() for d in t.devices]
                        if any(k in name_low for k in ["drum", "beat", "kick", "snare", "hat", "perc", "clap"]) or any("drum" in d for d in dev_names):
                            categories["Drums"].append(t.name)
                        elif any(k in name_low for k in ["bass", "sub", "808"]):
                            categories["Bass"].append(t.name)
                        elif t.type == "Effect" or any(k in name_low for k in ["fx", "reverb", "delay"]):
                            categories["FX"].append(t.name)
                        elif t.type == "Instrument" or any(k in name_low for k in ["synth", "keys", "piano", "organ", "lead", "pad"]):
                            categories["Synths"].append(t.name)

                    for cat_name, cat_tracks in categories.items():
                        if len(cat_tracks) >= 2:
                            try:
                                g_res = self.client.group_tracks(tracks=cat_tracks, name=cat_name)
                                results.append({"action": "auto_group", "group": cat_name, "tracks": cat_tracks, "result": g_res})
                                time.sleep(0.1)
                            except Exception as e:
                                results.append({"action": "auto_group_error", "group": cat_name, "error": str(e)})
                except Exception as e:
                    results.append({"action": "auto_group_failed", "error": str(e)})

            # 2. Handle explicit groups
            groups_arg = arguments.get("groups")
            if groups_arg:
                for g in groups_arg:
                    g_name = g.get("name")
                    g_tracks = g.get("tracks", [])
                    if g_tracks:
                        try:
                            g_res = self.client.group_tracks(tracks=g_tracks, name=g_name)
                            results.append({"action": "group", "group": g_name, "tracks": g_tracks, "result": g_res})
                            time.sleep(0.1)
                        except Exception as e:
                            results.append({"action": "group_error", "group": g_name, "error": str(e)})

            # 3. Handle explicit track reordering
            order_arg = arguments.get("order")
            if order_arg and len(order_arg) >= 2:
                try:
                    first_track = order_arg[0]
                    self.client.move_track(tracks=first_track, position="start")
                    time.sleep(0.05)
                    prev = first_track
                    for item in order_arg[1:]:
                        self.client.move_track(tracks=item, target=prev, position="after")
                        prev = item
                        time.sleep(0.05)
                    results.append({"action": "reorder", "order": order_arg, "status": "completed"})
                except Exception as e:
                    results.append({"action": "reorder_error", "order": order_arg, "error": str(e)})

            # Get final state
            final_tracks = []
            try:
                proj = self.client.get_project()
                final_tracks = [{"index": t.index, "name": t.name, "type": t.type, "isGroup": t.isGroup} for t in proj.tracks]
            except Exception:
                pass

            return {
                "status": "success",
                "operations_performed": len(results),
                "details": results,
                "project_tracks": final_tracks
            }

        return {"error": f"Unknown tool: {tool_name}"}

