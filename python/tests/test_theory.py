import pytest
from bitwig_agent.theory.chords import parse_chord
from bitwig_agent.theory.voicings import voice_progression
from bitwig_agent.theory.rhythm import generate_chord_events, generate_bassline_events
from bitwig_agent.theory.humanize import humanize_events
from bitwig_agent.theory import build_chord_progression, build_bassline

def test_parse_standard_chords():
    c = parse_chord("C")
    assert c.root == "C"
    assert c.root_pc == 0
    assert c.intervals == [0, 4, 7]

    dm7 = parse_chord("Dm7")
    assert dm7.root == "D"
    assert dm7.root_pc == 2
    assert dm7.intervals == [0, 3, 7, 10]

    g13 = parse_chord("G13")
    assert g13.root == "G"
    assert g13.root_pc == 7
    assert 21 in g13.intervals or 14 in g13.intervals

    eb_alt = parse_chord("Eb7alt")
    assert eb_alt.root == "Eb"
    assert eb_alt.root_pc == 3

def test_parse_slash_chords():
    slash = parse_chord("F/G")
    assert slash.root == "F"
    assert slash.bass == "G"
    assert slash.bass_pc == 7

def test_voice_progression_smoothness():
    chords = ["Dm9", "G13", "Cmaj9", "A7alt"]
    voiced = voice_progression(chords, style="keyboard")
    assert len(voiced) == 4

    for vc in voiced:
        # Bass pitch should be in lower register (36 to 48)
        assert 36 <= vc.bass_pitch <= 48
        # Upper voices should be in playable keyboard register (50 to 85)
        for p in vc.upper_pitches:
            assert 48 <= p <= 85

    # Check that voice leading between chord 0 and 1 does not make wild jumps (> 7 semitones on average)
    v0 = voiced[0].upper_pitches
    v1 = voiced[1].upper_pitches
    avg_jump = sum(min(abs(p1 - p0) for p0 in v0) for p1 in v1) / len(v1)
    assert avg_jump < 4.0 # Very smooth jazz voice leading!

def test_build_chord_progression_events():
    chords = ["Dm9", "G13", "Cmaj7"]
    events = build_chord_progression(
        chords=chords,
        beats_per_chord=4.0,
        rhythm_pattern="sustained",
        include_bass=True,
        humanize=True
    )
    assert len(events) > 0

    # Steps should start at 0, 16, 32
    steps = set(e.step for e in events)
    assert 0 in steps
    assert 16 in steps
    assert 32 in steps

    for ev in events:
        assert 0 <= ev.pitch <= 127
        assert 1 <= ev.velocity <= 127
        assert ev.duration > 0

def test_build_bassline():
    chords = ["Dm7", "G7", "Cmaj7"]
    bass_events = build_bassline(chords, beats_per_chord=4.0, style="syncopated")
    assert len(bass_events) >= 6
    for ev in bass_events:
        assert 24 <= ev.pitch <= 60

def test_build_extensive_progression():
    # 16 chords, 4 beats each = 64 beats = 256 steps (beyond the old 128 step limit)
    chords = [
        "Dm9", "G13", "Cmaj9", "A7alt",
        "Dm9", "G13", "Em7", "A7",
        "Fmaj7", "Fm7", "Em7", "A7alt",
        "Dm7", "G7b9", "Cmaj7", "Cmaj7"
    ]
    events = build_chord_progression(
        chords=chords,
        beats_per_chord=4.0,
        rhythm_pattern="sustained",
        include_bass=True,
        humanize=False
    )
    max_step = max(e.step for e in events)
    # The 16th chord starts at beat 60 -> step 240
    assert max_step == 240
    assert len(events) == 16 * 5  # 4 upper voices + 1 bass per chord

