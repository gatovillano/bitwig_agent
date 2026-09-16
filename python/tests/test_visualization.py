import pytest
from bitwig_agent.theory.visualization import (
    pitch_to_note_name,
    note_name_to_pitch,
    render_ascii_piano_roll
)
from bitwig_agent.client import ClipDetail, ClipNote

def test_pitch_conversions():
    assert pitch_to_note_name(60) == "C4"
    assert pitch_to_note_name(69) == "A4"
    assert pitch_to_note_name(48) == "C3"
    assert pitch_to_note_name(0) == "C-1"

    assert note_name_to_pitch("C4") == 60
    assert note_name_to_pitch("A4") == 69
    assert note_name_to_pitch("F#3") == 54
    assert note_name_to_pitch("Bb3") == 58
    assert note_name_to_pitch("invalid") is None

def test_render_empty_slot():
    data = {
        "track": 1,
        "track_name": "Keys",
        "slot": 0,
        "has_content": False
    }
    rendered = render_ascii_piano_roll(data)
    assert "EMPTY" in rendered
    assert "Track 1" in rendered

def test_render_empty_clip():
    data = {
        "track": 1,
        "track_name": "Keys",
        "slot": 0,
        "has_content": True,
        "name": "Intro",
        "notes": []
    }
    rendered = render_ascii_piano_roll(data)
    assert "Intro" in rendered
    assert "Empty clip" in rendered

def test_render_piano_roll_with_notes():
    detail = ClipDetail(
        track=2,
        track_name="Pad",
        slot=1,
        name="Chords",
        has_content=True,
        is_playing=True,
        loop_length=16.0,
        notes=[
            ClipNote(step=0, beat=0.0, pitch=60, name="C4", velocity=90, duration=4.0),
            ClipNote(step=0, beat=0.0, pitch=64, name="E4", velocity=85, duration=4.0),
            ClipNote(step=0, beat=0.0, pitch=67, name="G4", velocity=95, duration=4.0),
            ClipNote(step=16, beat=4.0, pitch=62, name="D4", velocity=88, duration=4.0),
            ClipNote(step=16, beat=4.0, pitch=65, name="F4", velocity=84, duration=4.0),
            ClipNote(step=16, beat=4.0, pitch=69, name="A4", velocity=90, duration=4.0),
        ]
    )
    rendered = render_ascii_piano_roll(detail)
    assert "Pad" in rendered
    assert "Chords" in rendered
    assert "Playing: Yes ▶" in rendered
    assert "C4" in rendered
    assert "E4" in rendered
    assert "G4" in rendered
    assert "■" in rendered  # Note head
    assert "═" in rendered  # Note sustain
    assert "Bar 1" in rendered
    assert "Notes Timeline" in rendered

def test_render_extensive_clip():
    # 16 bars clip (64 beats = 256 steps)
    notes = [
        ClipNote(step=0, beat=0.0, pitch=60, name="C4", velocity=90, duration=4.0),
        ClipNote(step=128, beat=32.0, pitch=64, name="E4", velocity=85, duration=4.0),
        ClipNote(step=240, beat=60.0, pitch=67, name="G4", velocity=95, duration=4.0),
    ]
    detail = ClipDetail(
        track=0,
        track_name="Chords",
        slot=0,
        name="16-Bar Progression",
        has_content=True,
        is_playing=False,
        loop_length=64.0,
        notes=notes
    )
    rendered = render_ascii_piano_roll(detail)
    assert "64.0 beats (16 bars)" in rendered
    assert "Bar 16" in rendered
    assert "G4" in rendered

