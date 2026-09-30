"""
Bitwig Device Knowledge Base, Semantic Recommender, and Browser Search.

Provides rich metadata, sound design characteristics, and intelligent semantic
recommendations for Bitwig Studio native instruments, audio effects, and containers.
"""

from __future__ import annotations
import re
from typing import Dict, List, Any, Optional

# Comprehensive knowledge base of Bitwig Studio 5/6 native instruments, effects, and utilities
BITWIG_DEVICES_DATABASE: List[Dict[str, Any]] = [
    # ==================== INSTRUMENTS ====================
    {
        "name": "Polymer",
        "type": "Instrument",
        "category": "Synth",
        "creator": "Bitwig",
        "description": "Modular hybrid synthesizer combining an oscillator module (Wavetable, Swarm, Phase-1, Analog, Pulse, etc.), a filter module (SVF, Sallen-Key, Ladder, XP, Comb), and an envelope generator. Extremely versatile, ranging from punchy vintage analog bass to evolving modern wavetable pads.",
        "tags": ["synth", "modular", "analog", "wavetable", "bass", "lead", "pad", "warm", "modern", "punchy", "subtractive", "sub bass", "acid"],
        "parameters": ["Filter Cutoff", "Resonance", "Envelope Attack", "Envelope Decay", "Sub Level", "Drive"],
        "tips": "For warm vintage pads, pair the Wavetable oscillator with the Ladder filter and gentle drive. For punchy bass, use the Analog oscillator with high resonance on Sallen-Key."
    },
    {
        "name": "Polysynth",
        "type": "Instrument",
        "category": "Synth",
        "creator": "Bitwig",
        "description": "Dual-oscillator subtractive polyphonic synthesizer inspired by classic analog keyboards. Features multi-mode filter, sub-oscillator, pulse-width modulation (PWM), unison detune, and built-in LFOs.",
        "tags": ["synth", "polyphonic", "analog", "vintage", "pad", "strings", "brass", "keys", "lead", "warm", "lush", "subtractive", "80s", "synthwave"],
        "parameters": ["Osc 1 Shape", "Osc 2 Detune", "Filter Cutoff", "Resonance", "Filter Envelope", "Amp Release"],
        "tips": "Great for classic 80s synthwave pads and Oberheim/Juno style brass. Detune Oscillator 2 by +7 cents for classic wide analog thickness."
    },
    {
        "name": "Phase-4",
        "type": "Instrument",
        "category": "Synth",
        "creator": "Bitwig",
        "description": "Four-oscillator phase distortion and phase modulation synthesizer inspired by the Casio CZ series and Yamaha DX synths. Capable of bright glassy keys, metallic bells, punchy FM plucks, and aggressive digital basses.",
        "tags": ["synth", "fm", "phase distortion", "digital", "glassy", "metallic", "bells", "electric piano", "ep", "pluck", "punchy", "bright", "bass", "dx7", "cz"],
        "parameters": ["Oscillator Modulation Amount", "Ratio", "Phase Distortion Shape", "Filter Cutoff", "Envelope"],
        "tips": "Excels at DX7 style electric pianos, FM mallets, and punchy metallic UK garage basslines. Modulate Phase Distortion with velocity for dynamic expression."
    },
    {
        "name": "FM-4",
        "type": "Instrument",
        "category": "Synth",
        "creator": "Bitwig",
        "description": "Classic 4-operator frequency modulation (FM) synthesizer with multiple routing algorithms, feedback paths, and dedicated operator envelopes. Ideal for classic 80s FM tones, metallic percussion, and cutting bass.",
        "tags": ["synth", "fm", "frequency modulation", "operator", "metallic", "bass", "bells", "percussion", "digital", "lo-fi", "80s", "bright"],
        "parameters": ["Op 1-4 Frequency Ratio", "Feedback", "Algorithm", "Operator Levels"],
        "tips": "Set Operator 2 to ratio 1.0 with high modulation index into Operator 1 for the classic deep FM bass 'Lately Bass' tone."
    },
    {
        "name": "Sampler",
        "type": "Instrument",
        "category": "Sampler",
        "creator": "Bitwig",
        "description": "Advanced multi-sample playback engine featuring granular synthesis modes, cycling textures, multi-velocity layers, pitch-tracking, and time-stretching. Can turn any sample into an evolving acoustic or ambient instrument.",
        "tags": ["sampler", "granular", "texture", "acoustic", "piano", "vocals", "choir", "ambient", "sound design", "evolving", "time-stretch", "lo-fi"],
        "parameters": ["Playhead Mode (Textures/Cycles)", "Grain Size", "Pitch", "Filter Cutoff", "Loop Start/End"],
        "tips": "Use the 'Textures' granular mode on a vocal or piano sample to create celestial, floating ambient pads."
    },
    {
        "name": "Drum Machine",
        "type": "Instrument",
        "category": "Drums",
        "creator": "Bitwig",
        "description": "Modular drum pad grid rack supporting up to 128 individual sample pads or synthesis devices. Features choke groups, dedicated per-pad effect chains, and nested device layering.",
        "tags": ["drums", "percussion", "drum rack", "beat", "kick", "snare", "hihat", "trap", "hip hop", "electronic", "choke groups"],
        "parameters": ["Pad Level", "Choke Group", "Pitch", "Decay", "Velocity Sensitivity"],
        "tips": "Assign open and closed hi-hats to the same Choke Group (e.g., Choke 1) for natural, realistic drumming performance."
    },
    {
        "name": "Organ",
        "type": "Instrument",
        "category": "Keys",
        "creator": "Bitwig",
        "description": "Drawbar tonewheel organ simulator featuring 9 harmonic drawbars, rotary speaker emulation (Leslie), percussion harmonics, and drive.",
        "tags": ["organ", "tonewheel", "drawbars", "b3", "gospel", "blues", "rock", "vintage", "warm", "rotary", "leslie"],
        "parameters": ["Drawbars 16'-1'", "Rotary Speed (Slow/Fast)", "Drive", "Percussion 2nd/3rd"],
        "tips": "Automate the Rotary speaker speed between Slow (Chorale) and Fast (Tremolo) during musical climaxes."
    },
    {
        "name": "Poly Grid",
        "type": "Instrument",
        "category": "Modular",
        "creator": "Bitwig",
        "description": "Bitwig's flagship modular sound design environment. Hundreds of modules (oscillators, math, logic, filters, delays, envelopes) allowing unlimited custom synthesis, generative music, and complex sound sculpture.",
        "tags": ["modular", "grid", "sound design", "experimental", "generative", "synth", "unlimited", "eurorack", "complex", "custom"],
        "parameters": ["Grid Input", "Grid Output", "Modulators", "Logic", "Oscillators"],
        "tips": "Use for complex generative patches, custom polyphonic synths, or reactive physical modeling."
    },
    {
        "name": "Instrument Layer",
        "type": "Container",
        "category": "Container",
        "creator": "Bitwig",
        "description": "Container that plays multiple instruments simultaneously or splits them across key and velocity zones.",
        "tags": ["container", "layer", "split", "stack", "multitimbral", "massive", "hybrid"],
        "parameters": ["Layer Mix", "Key Split", "Velocity Split"],
        "tips": "Layer a warm analog sub-bass underneath an acoustic piano or pluck for huge, full-frequency modern pop keys."
    },

    # ==================== AUDIO EFFECTS ====================
    # Reverbs & Space
    {
        "name": "Reverb",
        "type": "Audio Effect",
        "category": "Reverb",
        "creator": "Bitwig",
        "description": "Full-featured algorithmic reverb with Split Room simulation, pre-delay, diffusion, decay time control up to infinity, high/low damping filters, and modulation for lush shimmering tails.",
        "tags": ["reverb", "space", "room", "hall", "ambient", "lush", "shimmer", "decay", "wide", "atmosphere", "vocals"],
        "parameters": ["Decay Time", "Room Size", "Pre-delay", "Dampening", "Diffusion", "Mix"],
        "tips": "For vocal space without clutter, use 25ms pre-delay and filter out frequencies below 300 Hz in the reverb path (Abbey Road trick)."
    },
    {
        "name": "Convolution",
        "type": "Audio Effect",
        "category": "Reverb",
        "creator": "Bitwig",
        "description": "Impulse response (IR) convolution reverb and cabinet simulator. Accurately reproduces real acoustic spaces, vintage spring/plate hardware, and guitar amplifier cabinets.",
        "tags": ["reverb", "convolution", "impulse response", "ir", "realistic", "acoustic", "spring", "plate", "guitar", "cabinet", "vintage"],
        "parameters": ["Impulse", "Pre-delay", "Tone", "Gain", "Mix"],
        "tips": "Load a vintage spring reverb IR on an electric guitar or snare for authentic dub and surf rock character."
    },

    # Delays
    {
        "name": "Delay+",
        "type": "Audio Effect",
        "category": "Delay",
        "creator": "Bitwig",
        "description": "Advanced stereo audio delay with analog tape saturation, ducking, modulation, ping-pong diffusion, and color filters.",
        "tags": ["delay", "echo", "tape", "analog", "ping-pong", "ducking", "stereo", "warm", "vintage", "lo-fi", "vocals", "guitar"],
        "parameters": ["Time (Synced/Free)", "Feedback", "Duck", "Drive", "Modulation Depth", "Tone", "Mix"],
        "tips": "Turn up the 'Duck' parameter on lead vocals so the delay automatically ducks while the vocal sings and blooms into the gaps."
    },
    {
        "name": "Delay-1",
        "type": "Audio Effect",
        "category": "Delay",
        "creator": "Bitwig",
        "description": "Lightweight, ultra-clean digital stereo delay with high/low pass filters and feedback modulation.",
        "tags": ["delay", "clean", "digital", "simple", "low-cpu", "echo", "rhythmic"],
        "parameters": ["Time Left", "Time Right", "Feedback", "Mix"],
        "tips": "Set Left to 1/8 note and Right to 1/8 dotted for instant syncopated stereo bounce."
    },

    # Dynamics
    {
        "name": "Compressor+",
        "type": "Audio Effect",
        "category": "Dynamics",
        "creator": "Bitwig",
        "description": "Multi-mode dynamics processor supporting VCA, FET, and Optical compression styles with built-in sidechain EQ, dry/wet parallel compression, and lookahead.",
        "tags": ["compressor", "dynamics", "punch", "glue", "vca", "fet", "optical", "parallel", "sidechain", "mix bus", "drum bus", "vocals"],
        "parameters": ["Threshold", "Ratio", "Attack", "Release", "Knee", "Make-Up", "Mix"],
        "tips": "Use FET mode (ultra-fast attack) to crush drum room mics, or Opto mode (smooth, non-linear release) for vocal leveling."
    },
    {
        "name": "Peak Limiter",
        "type": "Audio Effect",
        "category": "Dynamics",
        "creator": "Bitwig",
        "description": "Brickwall peak limiter with lookahead to prevent digital clipping, maximize loudness, and control final dynamic ceiling.",
        "tags": ["limiter", "mastering", "brickwall", "loudness", "ceiling", "headroom", "clean", "transparent"],
        "parameters": ["Threshold", "Ceiling", "Release", "Lookahead"],
        "tips": "Place at the very end of your Master bus with Ceiling set to -0.3 dB to protect against inter-sample peaks."
    },
    {
        "name": "Gate",
        "type": "Audio Effect",
        "category": "Dynamics",
        "creator": "Bitwig",
        "description": "Noise gate with hysteresis and sidechain frequency filtering to remove bleed from drum microphones or create staccato trance gate rhythms.",
        "tags": ["gate", "noise", "cleanup", "trance gate", "rhythmic", "chatter", "drums", "snare bleed"],
        "parameters": ["Threshold", "Hysteresis", "Attack", "Hold", "Release"],
        "tips": "Use with an external sidechain trigger to create rhythmic pumping trance gates."
    },

    # EQ & Filters
    {
        "name": "EQ+",
        "type": "Audio Effect",
        "category": "EQ",
        "creator": "Bitwig",
        "description": "8-band parametric equalizer featuring interactive spectrum display, multiple filter types (Bell, Shelf, Notch, Tilt, Cut), surgical Q, and mid/side processing.",
        "tags": ["eq", "equalizer", "parametric", "spectrum", "surgical", "clean", "mid-side", "tone", "shaping", "mastering", "mixing"],
        "parameters": ["Bands 1-8 Freq", "Gain", "Q", "Filter Type", "Stereo Mode (Stereo/L-R/M-S)"],
        "tips": "Switch the lowest band to High-Pass 24dB/oct and remove sub-rumble below 30 Hz on all non-bass tracks to maximize mix headroom."
    },
    {
        "name": "EQ-5",
        "type": "Audio Effect",
        "category": "EQ",
        "creator": "Bitwig",
        "description": "Streamlined 5-band equalizer with low CPU footprint, ideal for quick tone balancing across multiple tracks.",
        "tags": ["eq", "low-cpu", "clean", "simple", "broad", "tone shaping"],
        "parameters": ["Low Shelf", "Mid 1-3", "High Shelf"],
        "tips": "Perfect for broad tonal adjustments and gentle high-frequency sheen."
    },
    {
        "name": "Filter+",
        "type": "Audio Effect",
        "category": "Filter",
        "creator": "Bitwig",
        "description": "Dual multimode filter with waveshaper drive stages and complex routing (series, parallel, split stereo). Supports Ladder, SVF, Sallen-Key, and Comb filter models.",
        "tags": ["filter", "ladder", "svf", "comb", "drive", "saturation", "warmth", "analog", "sweeps", "acid", "dj filter"],
        "parameters": ["Cutoff", "Resonance", "Drive", "Filter Type", "Routing"],
        "tips": "Drive the input stage into the Ladder filter model for saturated, thick Moog-style filter sweeps."
    },

    # Distortion & Saturation
    {
        "name": "Saturator",
        "type": "Audio Effect",
        "category": "Distortion",
        "creator": "Bitwig",
        "description": "Wave-shaping saturation and warmth processor with tape, tube, and digital saturation curves. Enhances harmonics, fattens bass, and glues sounds together.",
        "tags": ["saturator", "saturation", "tape", "tube", "warmth", "harmonics", "analog", "fat", "bass", "drums", "glue"],
        "parameters": ["Drive", "Curve (Soft/Hard/Sine/Tape)", "Low Cut", "High Cut", "Mix"],
        "tips": "Apply gentle tape saturation to 808 sub-basses to generate upper harmonic overtones audible on small phone and laptop speakers."
    },
    {
        "name": "Distortion",
        "type": "Audio Effect",
        "category": "Distortion",
        "creator": "Bitwig",
        "description": "Aggressive distortion and fuzz processor with pre/post tone shaping and clipping algorithms.",
        "tags": ["distortion", "fuzz", "aggressive", "hardcore", "industrial", "overdrive", "crunch", "heavy", "metal"],
        "parameters": ["Drive", "Bias", "Tone", "Mix"],
        "tips": "Great for aggressive synth leads, industrial drums, and heavy bass distortion."
    },
    {
        "name": "Bit-8",
        "type": "Audio Effect",
        "category": "Distortion",
        "creator": "Bitwig",
        "description": "Bit depth and sample rate reducer (bitcrusher) with anti-aliasing filter and jitter control for retro chiptune and gritty lo-fi textures.",
        "tags": ["bitcrusher", "lo-fi", "8-bit", "chiptune", "retro", "gritty", "crunch", "digital", "downsample"],
        "parameters": ["Bit Depth (1-16)", "Sample Rate", "Jitter", "Mix"],
        "tips": "Downsample to 12-bit / 22kHz to replicate the crunch of classic vintage hip-hop samplers like the SP-1200."
    },

    # Modulation
    {
        "name": "Chorus+",
        "type": "Audio Effect",
        "category": "Modulation",
        "creator": "Bitwig",
        "description": "Stereo multi-voice chorus with analog BBD (bucket brigade) and digital modes, stereo width enhancement, and warmth.",
        "tags": ["chorus", "modulation", "stereo", "width", "lush", "shimmer", "vintage", "juno", "bbd", "guitars", "synths"],
        "parameters": ["Rate", "Depth", "Voices (1-4)", "Width", "Mix"],
        "tips": "Add to Rhodes or electric piano with 2 voices and wide stereo setting for the quintessential vintage 70s neo-soul sound."
    },
    {
        "name": "Flanger+",
        "type": "Audio Effect",
        "category": "Modulation",
        "creator": "Bitwig",
        "description": "Thick resonant flanger with tape delay feedback and through-zero flanging (TZF) capabilities for dramatic jet-plane sweeps.",
        "tags": ["flanger", "jet", "sweep", "metallic", "psychedelic", "through-zero", "modulation", "guitars", "drums"],
        "parameters": ["Rate", "Depth", "Feedback", "Offset", "Mix"],
        "tips": "Use subtle through-zero flanging on a drum loop to add movement without overpowering the groove."
    },
    {
        "name": "Phaser+",
        "type": "Audio Effect",
        "category": "Modulation",
        "creator": "Bitwig",
        "description": "Multi-stage allpass phaser with up to 32 stages, barberpole frequency sweeping, and tempo synchronization.",
        "tags": ["phaser", "modulation", "swirl", "barberpole", "psychedelic", "funk", "clavi", "synths"],
        "parameters": ["Poles/Stages (2-32)", "Rate", "Depth", "Feedback", "Mix"],
        "tips": "Classic on funk Clavinet and 70s disco string synths with 4 to 8 stages."
    },

    # Utility & Spatial
    {
        "name": "Tool",
        "type": "Audio Effect",
        "category": "Utility",
        "creator": "Bitwig",
        "description": "Essential utility device for clean gain staging, stereo balance/panning, stereo width expansion/mono collapse, phase inversion, and mid/side conversion.",
        "tags": ["utility", "gain", "pan", "stereo width", "mono", "phase", "gain staging", "mix", "mastering"],
        "parameters": ["Gain (dB)", "Pan", "Width (0% mono to 400%)", "Phase Invert L/R"],
        "tips": "Set Width to 0% below 120 Hz using a mid-side split or Multiband FX to ensure bass frequencies remain punchy and strictly mono."
    }
]

class BitwigDeviceRecommender:
    """
    Intelligent semantic recommender and search engine for Bitwig Studio devices and effects.
    Uses multi-attribute weighted keyword and semantic tag scoring.
    """

    @classmethod
    def recommend(
        cls,
        task_description: str,
        num_results: int = 5,
        category: Optional[str] = None,
        device_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recommends Bitwig devices matching a natural language prompt.
        """
        if not task_description or not task_description.strip():
            return []

        # Tokenize and normalize query
        tokens = [t.lower() for t in re.findall(r"\b[a-zA-Z0-9\+#\-]+\b", task_description)]
        text_lower = task_description.lower()

        scored_devices: List[Dict[str, Any]] = []

        for dev in BITWIG_DEVICES_DATABASE:
            # Check filters
            if category and category.lower() not in dev["category"].lower():
                continue
            if device_type and device_type.lower() not in dev["type"].lower():
                continue

            score = 0.0
            matched_reasons: List[str] = []

            # 1. Exact name match in query
            if dev["name"].lower() in text_lower:
                score += 4.0
                matched_reasons.append(f"Name matches '{dev['name']}'")

            # 2. Category match
            if dev["category"].lower() in text_lower:
                score += 2.5
                matched_reasons.append(f"Belongs to category '{dev['category']}'")

            # 3. Tags matching
            dev_tags = [t.lower() for t in dev["tags"]]
            tag_hits = [t for t in tokens if t in dev_tags]
            if tag_hits:
                score += len(tag_hits) * 1.5
                matched_reasons.append(f"Matches character tags: {', '.join(tag_hits)}")

            # 4. Keyword presence in description
            desc_lower = dev["description"].lower()
            desc_hits = [t for t in tokens if len(t) > 2 and t in desc_lower]
            if desc_hits:
                score += len(desc_hits) * 0.8

            # 5. Tips matching
            tips_lower = dev.get("tips", "").lower()
            tips_hits = [t for t in tokens if len(t) > 2 and t in tips_lower]
            if tips_hits:
                score += len(tips_hits) * 0.5

            if score > 0.5:
                # Normalize score between 0.0 and 1.0 (approximate)
                norm_score = min(1.0, round(score / 8.0, 2))
                explanation = "; ".join(matched_reasons) if matched_reasons else f"Well suited for {task_description}"
                scored_devices.append({
                    "device": dev["name"],
                    "type": dev["type"],
                    "category": dev["category"],
                    "creator": dev["creator"],
                    "relevance_score": norm_score,
                    "explanation": explanation,
                    "description": dev["description"],
                    "parameters": dev["parameters"],
                    "tips": dev.get("tips", "")
                })

        # Sort by relevance_score descending
        scored_devices.sort(key=lambda d: d["relevance_score"], reverse=True)
        return scored_devices[:num_results]

    @classmethod
    def search(
        cls,
        query: str,
        category: Optional[str] = None,
        device_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Searches devices by name, tags, or category.
        """
        q = query.strip().lower()
        results: List[Dict[str, Any]] = []

        for dev in BITWIG_DEVICES_DATABASE:
            if category and category.lower() not in dev["category"].lower():
                continue
            if device_type and device_type.lower() not in dev["type"].lower():
                continue

            if not q or (
                q in dev["name"].lower()
                or q in dev["category"].lower()
                or q in dev["description"].lower()
                or any(q in t.lower() for t in dev["tags"])
            ):
                results.append({
                    "name": dev["name"],
                    "type": dev["type"],
                    "category": dev["category"],
                    "creator": dev["creator"],
                    "tags": dev["tags"],
                    "description": dev["description"],
                    "parameters": dev["parameters"]
                })

            if len(results) >= limit:
                break

        return results

    @classmethod
    def get_info(cls, device_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves detailed information for a specific device by name.
        """
        query = device_name.strip().lower()
        for dev in BITWIG_DEVICES_DATABASE:
            if dev["name"].lower() == query or query in dev["name"].lower():
                return dev
        return None

    @classmethod
    def get_categories(cls) -> Dict[str, Any]:
        """
        Returns all unique device categories, types, and device counts.
        """
        categories: Dict[str, List[str]] = {}
        types: Dict[str, List[str]] = {}

        for dev in BITWIG_DEVICES_DATABASE:
            c = dev["category"]
            t = dev["type"]
            categories.setdefault(c, []).append(dev["name"])
            types.setdefault(t, []).append(dev["name"])

        return {
            "categories": categories,
            "types": types,
            "total_devices": len(BITWIG_DEVICES_DATABASE)
        }
