from __future__ import annotations
import re
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel

NOTE_TO_PC: Dict[str, int] = {
    "C": 0, "B#": 0,
    "C#": 1, "DB": 1, "Db": 1,
    "D": 2,
    "D#": 3, "EB": 3, "Eb": 3,
    "E": 4, "FB": 4, "Fb": 4,
    "F": 5, "E#": 5,
    "F#": 6, "GB": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "AB": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "BB": 10, "Bb": 10,
    "B": 11, "CB": 11, "Cb": 11
}

PC_TO_NAME: List[str] = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

# Canonical intervals (semitones above root)
CHORD_INTERVALS: Dict[str, List[int]] = {
    # Triads
    "": [0, 4, 7],
    "maj": [0, 4, 7],
    "M": [0, 4, 7],
    "m": [0, 3, 7],
    "min": [0, 3, 7],
    "-": [0, 3, 7],
    "dim": [0, 3, 6],
    "o": [0, 3, 6],
    "aug": [0, 4, 8],
    "+": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "sus": [0, 5, 7],

    # 6th chords
    "6": [0, 4, 7, 9],
    "m6": [0, 3, 7, 9],
    "min6": [0, 3, 7, 9],
    "69": [0, 4, 7, 9, 14],
    "6/9": [0, 4, 7, 9, 14],

    # 7ths
    "7": [0, 4, 7, 10],
    "dom7": [0, 4, 7, 10],
    "maj7": [0, 4, 7, 11],
    "M7": [0, 4, 7, 11],
    "Δ7": [0, 4, 7, 11],
    "Δ": [0, 4, 7, 11],
    "m7": [0, 3, 7, 10],
    "min7": [0, 3, 7, 10],
    "-7": [0, 3, 7, 10],
    "m7b5": [0, 3, 6, 10],
    "ø": [0, 3, 6, 10],
    "ø7": [0, 3, 6, 10],
    "dim7": [0, 3, 6, 9],
    "o7": [0, 3, 6, 9],
    "mmaj7": [0, 3, 7, 11],
    "m(maj7)": [0, 3, 7, 11],
    "7sus4": [0, 5, 7, 10],
    "7sus": [0, 5, 7, 10],

    # 9ths & Extensions
    "9": [0, 4, 7, 10, 14],
    "maj9": [0, 4, 7, 11, 14],
    "M9": [0, 4, 7, 11, 14],
    "m9": [0, 3, 7, 10, 14],
    "min9": [0, 3, 7, 10, 14],
    "7b9": [0, 4, 7, 10, 13],
    "7#9": [0, 4, 7, 10, 15],
    "add9": [0, 4, 7, 14],
    "madd9": [0, 3, 7, 14],

    # 11ths
    "11": [0, 4, 7, 10, 14, 17],
    "maj11": [0, 4, 7, 11, 14, 17],
    "m11": [0, 3, 7, 10, 14, 17],
    "min11": [0, 3, 7, 10, 14, 17],
    "7#11": [0, 4, 7, 10, 14, 18],

    # 13ths
    "13": [0, 4, 7, 10, 14, 21],
    "maj13": [0, 4, 7, 11, 14, 21],
    "m13": [0, 3, 7, 10, 14, 21],
    "min13": [0, 3, 7, 10, 14, 21],
    "7b13": [0, 4, 7, 10, 20],

    # Altered Dominants
    "7alt": [0, 4, 10, 13, 15, 20], # 1, 3, b7, b9, #9, b13
    "alt": [0, 4, 10, 13, 15, 20],
}

class ParsedChord(BaseModel):
    raw_name: str
    root: str
    root_pc: int
    quality: str
    intervals: List[int]
    bass: str
    bass_pc: int

CHORD_REGEX = re.compile(
    r"^([A-Ga-g][#b]?)([^/]*)(?:/([A-Ga-g][#b]?))?$"
)

def normalize_note(name: str) -> Tuple[str, int]:
    clean = name.strip()
    if len(clean) > 1:
        first = clean[0].upper()
        acc = clean[1:].replace("♯", "#").replace("♭", "b")
        key = first + acc
    else:
        key = clean.upper()
    if key not in NOTE_TO_PC:
        raise ValueError(f"Unknown note name: '{name}'")
    pc = NOTE_TO_PC[key]
    return PC_TO_NAME[pc], pc

def parse_chord(chord_str: str) -> ParsedChord:
    """
    Parses a chord symbol (e.g. 'Dm9', 'F#7alt', 'Cmaj7', 'Bb13/Eb')
    into its root, pitch-class, quality, intervals and optional slash bass.
    """
    chord_str = chord_str.strip()
    m = CHORD_REGEX.match(chord_str)
    if not m:
        raise ValueError(f"Invalid chord format: '{chord_str}'")

    raw_root, raw_quality, raw_bass = m.groups()
    root_name, root_pc = normalize_note(raw_root)

    quality = raw_quality.strip() if raw_quality else ""
    # Normalize common variations
    norm_q = quality.replace(" ", "")

    if norm_q in CHORD_INTERVALS:
        intervals = CHORD_INTERVALS[norm_q]
    else:
        # Fallback attempts
        low_q = norm_q.lower()
        if low_q in CHORD_INTERVALS:
            intervals = CHORD_INTERVALS[low_q]
        elif low_q.startswith("m") and not low_q.startswith("maj"):
            intervals = CHORD_INTERVALS["m7"] if "7" in low_q else CHORD_INTERVALS["m"]
        elif "maj" in low_q:
            intervals = CHORD_INTERVALS["maj7"]
        elif "7" in low_q:
            intervals = CHORD_INTERVALS["7"]
        else:
            intervals = CHORD_INTERVALS["maj"]

    if raw_bass:
        bass_name, bass_pc = normalize_note(raw_bass)
    else:
        bass_name, bass_pc = root_name, root_pc

    return ParsedChord(
        raw_name=chord_str,
        root=root_name,
        root_pc=root_pc,
        quality=quality,
        intervals=intervals,
        bass=bass_name,
        bass_pc=bass_pc
    )
