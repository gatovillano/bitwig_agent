from __future__ import annotations
from typing import List, Dict, Any, Union, Optional

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def pitch_to_note_name(pitch: int) -> str:
    """Converts a MIDI pitch number (0-127) to a standard note name with octave, e.g. 60 -> C4."""
    if pitch < 0 or pitch > 127:
        return f"?{pitch}"
    octave = (pitch // 12) - 1
    name = NOTE_NAMES[pitch % 12]
    return f"{name}{octave}"

def note_name_to_pitch(name: str) -> Optional[int]:
    """Converts a note name (e.g. 'C4', 'F#3', 'Bb2') to MIDI pitch number."""
    if not name:
        return None
    name = name.strip()
    # Normalize flats to sharps
    flats_map = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
    for flat, sharp in flats_map.items():
        if name.startswith(flat):
            name = sharp + name[len(flat):]
            break
    
    # Extract pitch name and octave
    if len(name) >= 2 and name[1] == "#":
        pitch_part = name[:2]
        octave_part = name[2:]
    else:
        pitch_part = name[:1]
        octave_part = name[1:]
    
    if pitch_part not in NOTE_NAMES:
        return None
    try:
        octave = int(octave_part)
    except ValueError:
        return None
    
    pitch = (octave + 1) * 12 + NOTE_NAMES.index(pitch_part)
    return pitch if 0 <= pitch <= 127 else None

def render_ascii_piano_roll(
    clip_data: Union[Dict[str, Any], Any],
    max_steps: Optional[int] = None
) -> str:
    """
    Renders an ASCII piano roll and musical analysis of a clip.
    Supports both dict and Pydantic ClipDetail instances.
    """
    if hasattr(clip_data, "model_dump"):
        data = clip_data.model_dump()
    elif isinstance(clip_data, dict):
        data = clip_data
    else:
        data = dict(clip_data)

    track_name = data.get("track_name", f"Track {data.get('track', '?')}")
    track_idx = data.get("track", 0)
    slot_idx = data.get("slot", 0)
    clip_name = data.get("name") or f"Slot {slot_idx}"
    has_content = data.get("has_content", True)
    is_playing = data.get("is_playing", False)
    loop_length = float(data.get("loop_length", 16.0))
    loop_enabled = data.get("loop_enabled", True)
    notes_raw = data.get("notes", [])

    lines: List[str] = []

    if not has_content:
        lines.append(f"┌─ Clip Slot [{slot_idx}] on Track {track_idx} ({track_name}) ─┐")
        lines.append(f"│ Status: EMPTY (No clip in slot)                         │")
        lines.append(f"└────────────────────────────────────────────────────────┘")
        return "\n".join(lines)

    if not notes_raw:
        lines.append(f"┌─ Clip: '{clip_name}' (Track {track_idx}: {track_name}, Slot {slot_idx}) ─┐")
        lines.append(f"│ Loop: {loop_length:.1f} beats | Playing: {'Yes' if is_playing else 'No'}                 │")
        lines.append(f"│ Notes: 0 (Empty clip - no note events found)            │")
        lines.append(f"└─────────────────────────────────────────────────────────┘")
        return "\n".join(lines)

    # Parse and normalize notes
    notes = []
    for n in notes_raw:
        if isinstance(n, dict):
            step = int(n.get("step", 0))
            pitch = int(n.get("pitch", 60))
            vel = int(n.get("velocity", 100))
            dur = float(n.get("duration", 1.0))
            name = n.get("name") or pitch_to_note_name(pitch)
            channel = int(n.get("channel", 0))
        else:
            step = int(getattr(n, "step", 0))
            pitch = int(getattr(n, "pitch", 60))
            vel = int(getattr(n, "velocity", 100))
            dur = float(getattr(n, "duration", 1.0))
            name = getattr(n, "name", pitch_to_note_name(pitch))
            channel = int(getattr(n, "channel", 0))
        notes.append({
            "step": step,
            "pitch": pitch,
            "velocity": vel,
            "duration": dur,
            "name": name,
            "channel": channel
        })

    pitches = sorted(list(set(n["pitch"] for n in notes)))
    min_pitch = pitches[0]
    max_pitch = pitches[-1]
    pitch_classes = sorted(list(set(NOTE_NAMES[p % 12] for p in pitches)))
    bars = max(1, int(round(loop_length / 4.0)))

    # 1 beat = 4 steps (16th notes)
    configured_steps = int(round(loop_length * 4)) if loop_length > 0 else 64
    max_note_step = max(n["step"] + int(round(n["duration"] * 4)) for n in notes) if notes else 16
    needed_steps = max(configured_steps, ((max_note_step + 15) // 16) * 16)
    effective_max = max_steps if max_steps is not None else max(64, needed_steps)
    total_steps = min(effective_max, needed_steps)
    total_steps = max(16, total_steps)

    # Header Card
    lines.append(f"╔═ Clip: \"{clip_name}\" ══════════════════════════════════════════")
    lines.append(f"║ Track: {track_idx} ({track_name}) | Slot: {slot_idx}")
    lines.append(f"║ Loop: {loop_length:.1f} beats ({bars} bars) | Loop Enabled: {'Yes' if loop_enabled else 'No'} | Playing: {'Yes ▶' if is_playing else 'No ⏹'}")
    lines.append(f"║ Notes Total: {len(notes)} | Pitch Range: {pitch_to_note_name(min_pitch)} ({min_pitch}) - {pitch_to_note_name(max_pitch)} ({max_pitch})")
    lines.append(f"║ Pitch Classes: {', '.join(pitch_classes)}")
    lines.append(f"╚══════════════════════════════════════════════════════════════════")

    # Time Axis Headers
    bar_line = "           "
    num_bars = (total_steps + 15) // 16
    for b in range(num_bars):
        bar_text = f" Bar {b+1} "
        fill_len = max(0, 16 - len(bar_text))
        left_fill = fill_len // 2
        right_fill = fill_len - left_fill
        bar_line += "|" + ("─" * left_fill) + bar_text + ("─" * right_fill)
    bar_line += "|"
    lines.append(bar_line)

    beat_line = "           "
    for s in range(0, total_steps):
        if s % 16 == 0:
            beat_line += "|"
        elif s % 4 == 0:
            beat_line += ":"
        beat_line += str((s // 4) % 4 + 1) if s % 4 == 0 else "·"
    beat_line += "|"
    lines.append(beat_line)

    divider = "───────────+" + ("─" * (total_steps + (total_steps // 16)))
    lines.append(divider)

    # Build pitch rows (from highest note down to lowest note)
    for p in reversed(pitches):
        note_name = pitch_to_note_name(p)
        label = f"{note_name:>4} ({p:>3}) │"
        
        row_cells = [" "] * total_steps
        
        pitch_notes = [n for n in notes if n["pitch"] == p]
        for pn in pitch_notes:
            start_s = pn["step"]
            dur_steps = max(1, int(round(pn["duration"] * 4.0)))
            for offset in range(dur_steps):
                step_idx = start_s + offset
                if 0 <= step_idx < total_steps:
                    if offset == 0:
                        row_cells[step_idx] = "■"
                    else:
                        row_cells[step_idx] = "═"

        formatted_row = label
        for s in range(total_steps):
            if s > 0 and s % 16 == 0:
                formatted_row += "|"
            elif s > 0 and s % 4 == 0:
                formatted_row += " "
            formatted_row += row_cells[s]
        formatted_row += "│"
        lines.append(formatted_row)

    lines.append(divider)

    # Note Event Summary Table (first 16 notes)
    lines.append("\nNotes Timeline (First 16 events):")
    lines.append(" Step │ Beat │ Note │ Pitch │ Velocity │ Duration")
    lines.append("──────┼──────┼──────┼───────┼──────────┼─────────")
    for n in notes[:16]:
        beat_val = n["step"] * 0.25
        lines.append(f" {n['step']:>4} │ {beat_val:>4.2f} │ {n['name']:>4} │ {n['pitch']:>5} │ {n['velocity']:>8} │ {n['duration']:>4.2f} beats")
    if len(notes) > 16:
        lines.append(f" ... and {len(notes) - 16} more notes.")

    return "\n".join(lines)
