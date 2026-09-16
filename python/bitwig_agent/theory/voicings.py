from __future__ import annotations
import itertools
from typing import List, Optional
from pydantic import BaseModel
from bitwig_agent.theory.chords import ParsedChord, parse_chord

class VoicedChord(BaseModel):
    chord: ParsedChord
    bass_pitch: int
    upper_pitches: List[int]

    @property
    def all_pitches(self) -> List[int]:
        return sorted([self.bass_pitch] + self.upper_pitches)

def get_chord_pitch_classes(chord: ParsedChord, style: str = "keyboard") -> List[int]:
    """
    Extracts the key pitch classes for voicing.
    For jazz/keyboard voicings with 5+ notes, prioritizes 3rd, 7th, extensions, and root.
    """
    pcs = [(chord.root_pc + interval) % 12 for interval in chord.intervals]
    # Remove duplicate pitch classes while preserving order
    seen = set()
    unique_pcs = []
    for p in pcs:
        if p not in seen:
            seen.add(p)
            unique_pcs.append(p)

    if style == "rootless" and len(unique_pcs) > 3:
        # Remove root from upper harmony if there are enough color notes
        unique_pcs = [p for p in unique_pcs if p != chord.root_pc]

    # Keep between 3 and 5 voices for clean keyboard voicing
    if len(unique_pcs) > 5:
        # Typically omit 5th if present (interval 7)
        fifth_pc = (chord.root_pc + 7) % 12
        if fifth_pc in unique_pcs:
            unique_pcs.remove(fifth_pc)

    return unique_pcs[:4]

def voice_first_chord(
    pcs: List[int],
    target_center: int = 65, # around F4
    min_pitch: int = 55,     # G3
    max_pitch: int = 79      # G5
) -> List[int]:
    """
    Arranges pitch classes into a compact, well-centered chord in the target octave.
    """
    # Find base octave for each pc closest to target center
    voiced = []
    for pc in pcs:
        best_pitch = None
        best_dist = 999
        for oct_num in range(3, 6):
            pitch = oct_num * 12 + pc
            dist = abs(pitch - target_center)
            if dist < best_dist:
                best_dist = dist
                best_pitch = pitch
        voiced.append(best_pitch)
    return sorted(voiced)

def find_best_voice_leading(
    prev_pitches: List[int],
    new_pcs: List[int],
    min_pitch: int = 53, # F3
    max_pitch: int = 81  # A5
) -> List[int]:
    """
    Finds the octave assignments for new_pcs that minimize total movement
    relative to prev_pitches (smooth voice leading).
    """
    target_size = len(new_pcs)
    # Generate pitch candidates for each pc within [min_pitch, max_pitch]
    pc_options = []
    for pc in new_pcs:
        opts = []
        for oct_num in range(2, 8):
            pitch = oct_num * 12 + pc
            if min_pitch <= pitch <= max_pitch:
                opts.append(pitch)
        if not opts:
            opts = [4 * 12 + pc]
        pc_options.append(opts)

    # Carthesian product of candidates
    best_combo = None
    min_cost = float("inf")

    prev_sorted = sorted(prev_pitches)
    prev_center = sum(prev_sorted) / len(prev_sorted) if prev_sorted else 65

    for combo in itertools.product(*pc_options):
        sorted_combo = sorted(combo)
        # Avoid voicings where notes are too cramped (e.g. cluster < 2 semitones unless intended)
        has_clash = any(sorted_combo[i+1] - sorted_combo[i] < 1 for i in range(len(sorted_combo)-1))
        if has_clash:
            continue

        # Cost = sum of squared movements to nearest voices + penalty for moving away from register
        cost = 0.0
        for p_new in sorted_combo:
            closest_dist = min(abs(p_new - p_old) for p_old in prev_sorted)
            cost += closest_dist ** 2

        # Center drift penalty
        combo_center = sum(sorted_combo) / len(sorted_combo)
        cost += (combo_center - prev_center) ** 2 * 0.2

        if cost < min_cost:
            min_cost = cost
            best_combo = sorted_combo

    if best_combo is None:
        return voice_first_chord(new_pcs)
    return best_combo

def voice_progression(
    chords: List[ParsedChord | str],
    style: str = "keyboard",
    bass_octave: int = 2
) -> List[VoicedChord]:
    """
    Takes a progression of chords and returns smooth, voice-led keyboard voicings.
    """
    parsed_chords: List[ParsedChord] = []
    for c in chords:
        if isinstance(c, str):
            parsed_chords.append(parse_chord(c))
        else:
            parsed_chords.append(c)

    if not parsed_chords:
        return []

    results: List[VoicedChord] = []
    prev_upper: Optional[List[int]] = None

    for c in parsed_chords:
        # Bass note (octave 2/3: e.g. 36-48)
        bass_pitch = 12 * (bass_octave + 1) + c.bass_pc
        while bass_pitch < 36:
            bass_pitch += 12
        while bass_pitch > 48:
            bass_pitch -= 12

        pcs = get_chord_pitch_classes(c, style=style)

        if prev_upper is None:
            upper = voice_first_chord(pcs)
        else:
            upper = find_best_voice_leading(prev_upper, pcs)

        # Apply Drop-2 if requested
        if style == "drop2" and len(upper) >= 4:
            # Drop 2nd highest note down an octave
            drop_note = upper[-2] - 12
            new_upper = sorted([upper[0], upper[1], upper[3], drop_note])
            upper = new_upper

        prev_upper = upper
        results.append(VoicedChord(
            chord=c,
            bass_pitch=bass_pitch,
            upper_pitches=upper
        ))

    return results
