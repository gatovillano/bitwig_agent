from __future__ import annotations
from typing import List
from bitwig_agent.client import NoteEvent
from bitwig_agent.theory.chords import parse_chord, ParsedChord
from bitwig_agent.theory.voicings import voice_progression, VoicedChord
from bitwig_agent.theory.rhythm import generate_chord_events, generate_bassline_events
from bitwig_agent.theory.humanize import humanize_events

def build_chord_progression(
    chords: List[str],
    beats_per_chord: float = 4.0,
    voicing_style: str = "keyboard",
    rhythm_pattern: str = "sustained",
    include_bass: bool = True,
    humanize: bool = True,
    base_velocity: int = 80
) -> List[NoteEvent]:
    """
    High-level facade: converts a list of chord names (e.g. ['Dm9', 'G13', 'Cmaj9', 'A7alt'])
    into a fully voiced, smoothly connected, humanized list of NoteEvents ready for Bitwig.
    """
    voiced = voice_progression(chords, style=voicing_style)
    events = generate_chord_events(
        voiced,
        beats_per_chord=beats_per_chord,
        rhythm_pattern=rhythm_pattern,
        include_bass=include_bass,
        base_velocity=base_velocity
    )
    if humanize:
        events = humanize_events(events)
    return events

def build_bassline(
    chords: List[str],
    beats_per_chord: float = 4.0,
    style: str = "root"
) -> List[NoteEvent]:
    """
    Generates a matching bassline for a chord progression.
    """
    voiced = voice_progression(chords, style="keyboard")
    return generate_bassline_events(voiced, beats_per_chord=beats_per_chord, style=style)

from bitwig_agent.theory.visualization import render_ascii_piano_roll, pitch_to_note_name, note_name_to_pitch

__all__ = [
    "parse_chord",
    "ParsedChord",
    "voice_progression",
    "VoicedChord",
    "generate_chord_events",
    "generate_bassline_events",
    "humanize_events",
    "build_chord_progression",
    "build_bassline",
    "render_ascii_piano_roll",
    "pitch_to_note_name",
    "note_name_to_pitch"
]
