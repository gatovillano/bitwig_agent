from __future__ import annotations
from typing import List, Dict, Any, Optional
from bitwig_agent.client import NoteEvent
from bitwig_agent.theory.voicings import VoicedChord

def generate_chord_events(
    voiced_chords: List[VoicedChord],
    beats_per_chord: float = 4.0,
    rhythm_pattern: str = "sustained",
    include_bass: bool = True,
    base_velocity: int = 80
) -> List[NoteEvent]:
    """
    Translates voiced chords into a timed list of NoteEvent objects
    positioned on Bitwig's 16th-note step grid.
    """
    events: List[NoteEvent] = []
    # 4 steps per beat (16th note resolution)
    steps_per_beat = 4

    current_beat = 0.0

    for vc in voiced_chords:
        chord_start_step = int(current_beat * steps_per_beat)
        pitches = vc.all_pitches if include_bass else vc.upper_pitches

        if rhythm_pattern == "sustained":
            # Hold chord for entire duration (e.g. 4 beats = 1 bar)
            for p in pitches:
                vel = base_velocity if p in vc.upper_pitches else base_velocity + 10
                events.append(NoteEvent(
                    step=chord_start_step,
                    pitch=p,
                    velocity=vel,
                    duration=beats_per_chord
                ))

        elif rhythm_pattern in ("syncopated", "lofi", "soul"):
            # Play on beat 1 (duration 1.5 beats), beat 2.5 (duration 1.5 beats), beat 4.0 (duration 1.0)
            sub_offsets = [0.0, 1.5, 3.0] if beats_per_chord >= 4.0 else [0.0, 1.0]
            for off in sub_offsets:
                sub_step = int((current_beat + off) * steps_per_beat)
                dur = 1.25
                for p in pitches:
                    events.append(NoteEvent(
                        step=sub_step,
                        pitch=p,
                        velocity=base_velocity - 5 if off != 0.0 else base_velocity + 5,
                        duration=dur
                    ))

        elif rhythm_pattern == "quarter_stabs":
            # Play on every quarter note (staccato feel: duration 0.6 beats)
            num_beats = int(beats_per_chord)
            for b in range(num_beats):
                sub_step = int((current_beat + b) * steps_per_beat)
                for p in pitches:
                    events.append(NoteEvent(
                        step=sub_step,
                        pitch=p,
                        velocity=base_velocity,
                        duration=0.6
                    ))

        elif rhythm_pattern == "arpeggio":
            # Ascending arpeggio across 16th or 8th notes
            step_stride = 2 # 8th notes
            for idx, p in enumerate(pitches):
                arp_step = chord_start_step + (idx * step_stride)
                events.append(NoteEvent(
                    step=arp_step,
                    pitch=p,
                    velocity=base_velocity,
                    duration=1.0
                ))

        else:
            # Fallback to sustained
            for p in pitches:
                events.append(NoteEvent(
                    step=chord_start_step,
                    pitch=p,
                    velocity=base_velocity,
                    duration=beats_per_chord
                ))

        current_beat += beats_per_chord

    return events

def generate_bassline_events(
    voiced_chords: List[VoicedChord],
    beats_per_chord: float = 4.0,
    style: str = "root"
) -> List[NoteEvent]:
    """
    Generates a dedicated bassline track for a chord progression.
    """
    events: List[NoteEvent] = []
    steps_per_beat = 4
    current_beat = 0.0

    for vc in voiced_chords:
        root_pitch = vc.bass_pitch
        start_step = int(current_beat * steps_per_beat)

        if style == "root":
            # Sustained root note for the entire chord
            events.append(NoteEvent(
                step=start_step,
                pitch=root_pitch,
                velocity=95,
                duration=beats_per_chord
            ))

        elif style == "syncopated":
            # Beat 1 (root), beat 2.5 (root), beat 3.5 (fifth or octave)
            fifth_pitch = root_pitch + 7
            events.append(NoteEvent(step=start_step, pitch=root_pitch, velocity=100, duration=1.5))
            events.append(NoteEvent(step=start_step + 6, pitch=root_pitch, velocity=85, duration=1.0))
            if beats_per_chord >= 4:
                events.append(NoteEvent(step=start_step + 12, pitch=fifth_pitch, velocity=90, duration=1.0))

        elif style == "walking":
            # Quarter notes: Root, passing tone, 5th, chromatic approach
            fifth_pitch = root_pitch + 7
            third_pitch = root_pitch + (4 if 4 in vc.chord.intervals else 3)
            approach = root_pitch - 1

            events.append(NoteEvent(step=start_step, pitch=root_pitch, velocity=95, duration=0.9))
            events.append(NoteEvent(step=start_step + 4, pitch=third_pitch, velocity=85, duration=0.9))
            events.append(NoteEvent(step=start_step + 8, pitch=fifth_pitch, velocity=90, duration=0.9))
            events.append(NoteEvent(step=start_step + 12, pitch=approach, velocity=80, duration=0.9))

        current_beat += beats_per_chord

    return events
