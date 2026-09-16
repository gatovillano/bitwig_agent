from __future__ import annotations
import json
import math
from typing import List, Dict, Any, Optional
from bitwig_agent.client import BitwigClient, NoteEvent
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
            "description": "Controls Bitwig transport: play, stop, restart, or change tempo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["play", "stop", "restart", "set_tempo"],
                        "description": "Transport action to perform."
                    },
                    "tempo": {
                        "type": "number",
                        "description": "New tempo in BPM (required if action is 'set_tempo')."
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
    }
]

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
            return self.client.inspect_track(track_idx)

        elif tool_name == "inspect_clip":
            track_ident = arguments.get("track", "0")
            slot_idx = int(arguments.get("slot", 0))
            track_idx = self._resolve_track_index(track_ident)
            clip_res = self.client.inspect_clip(track=track_idx, slot=slot_idx)
            if isinstance(clip_res, dict):
                clip_res["piano_roll"] = render_ascii_piano_roll(clip_res)
            return clip_res

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

        return {"error": f"Unknown tool: {tool_name}"}

