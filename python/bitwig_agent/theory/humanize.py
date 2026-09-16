from __future__ import annotations
import random
from typing import List
from bitwig_agent.client import NoteEvent

def humanize_events(
    events: List[NoteEvent],
    velocity_variance: int = 6,
    accent_top_voice: bool = True,
    strum_delay_steps: float = 0.0,
    seed: int | None = None
) -> List[NoteEvent]:
    """
    Applies humanization to a list of NoteEvents:
    - Random velocity jitter within [-velocity_variance, +velocity_variance].
    - Accents top melody voice.
    - Softens inner voices.
    """
    if seed is not None:
        random.seed(seed)

    # Group events by step to find chord stacks
    step_groups = {}
    for ev in events:
        step_groups.setdefault(ev.step, []).append(ev)

    humanized: List[NoteEvent] = []

    for step, chord_notes in step_groups.items():
        # Sort notes low to high
        sorted_notes = sorted(chord_notes, key=lambda n: n.pitch)
        num_notes = len(sorted_notes)

        for idx, note in enumerate(sorted_notes):
            vel = note.velocity
            # Jitter
            jitter = random.randint(-velocity_variance, velocity_variance)
            vel += jitter

            # Dynamic contour: top note sings slightly louder
            if accent_top_voice and num_notes > 1 and idx == num_notes - 1:
                vel += 6
            elif num_notes > 2 and 0 < idx < num_notes - 1:
                vel -= 4 # inner voices tuck in slightly

            vel = max(1, min(127, vel))

            # Duration subtle variance
            dur_jitter = random.uniform(-0.04, 0.04)
            dur = max(0.1, round(note.duration + dur_jitter, 3))

            humanized.append(NoteEvent(
                step=note.step,
                pitch=note.pitch,
                velocity=vel,
                duration=dur,
                channel=note.channel
            ))

    # Sort final events by step and pitch
    return sorted(humanized, key=lambda e: (e.step, e.pitch))
