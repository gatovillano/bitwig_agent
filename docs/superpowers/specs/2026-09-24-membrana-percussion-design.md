# Design Spec: Membrana - Percussion Architecture (126 BPM)

## Executive Summary
This document specifies the architectural design and implementation details for the percussion section of **Membrana**, the third track of the EP **DENSA**. Inspired by Björk's *Fossora*, the track represents cellular breakdown, active fermentation, and chaotic metabolic transition.

---

## 1. Project Specifications & Tempo
* **Project Tempo**: **126.00 BPM** (Abrupt tempo elevation from 118 BPM in *Raíz*).
* **Rhythmic Style**: **Broken Beat Convulso** with unpredictable syncopations and sharp transients.
* **Timbral Concept**: Hybrid Gabber / Organic Sampled Percussion + FM Corrosion + Granular Hiss/Steam.

---

## 2. Track & Bus Architecture in Bitwig Studio

```
[Bus: Percu Membrana (Group Track)]
 ├── Track 01: Kick Gabber FM (FM Synthesis / Heavily Distorted Low-End Kick)
 ├── Track 02: Percu Organica Rota (Scraped Wood, Metal, & Skin Percussion)
 └── Track 03: Siseos & Vapor Granular (White Noise Hiss, Vapor Release & Stereo Glitch)
```

### Track Details

#### Track 01: `Kick Gabber FM`
* **Instrument**: Bitwig `Polymer` / `Sampler` tuned for heavy FM kick synthesis.
* **Devices & FX Chain**:
  1. `Saturator` / `Distortion` (Drive +12 dB, Hard clipping).
  2. `Filter+` (Low-pass resonance for punch).
  3. `Tool` (True Mono 0% for tight low-end centering).
* **Function**: Delivers the anaerobic, heavy distorted pulse of the 126 BPM broken beat.

#### Track 02: `Percu Organica Rota`
* **Instrument**: Acoustic / Sampled percussive kit (Woodblocks, scraped metals, organic strikes).
* **Devices & FX Chain**:
  1. `EQ+` (High-pass @ 100 Hz, notch cuts at 350 Hz).
  2. `Transient Control` / `Compressor+` (Attack boost for razor-sharp transients).
* **Pattern**: Syncopated 16th-note broken beat with ghost notes and velocity variations (40-127).

#### Track 03: `Siseos & Vapor Granular`
* **Instrument**: Noise generator / Granular sampler for organic steam release.
* **Devices & FX Chain**:
  1. `Filter+` (LFO-modulated High-pass filter sweeping 2 kHz - 12 kHz).
  2. `Delay+` (Ducking 50%, Stereo blur 40%).
* **Function**: Emulates steam bursts and cellular breakdown gases.

#### Group Bus: `Percu Membrana`
* **Devices**:
  1. `Compressor+` (Glue compression, Threshold -18 dB, Ratio 1:4, Attack 20 ms, Release 120 ms).
  2. `Saturator` (Soft Drive +2.5 dB for unified bus cohesion).

---

## 3. Implementation Steps (Bitwig MCP Actions)
1. **Set Transport Tempo**: Set tempo to 126.00 BPM.
2. **Create Percussion Group**: Group tracks 0, 1, 2 under `Percu Membrana`.
3. **Add Devices**: Insert `Compressor+`, `Saturator`, `Filter+`, `Tool`, `EQ+`, `Delay+`.
4. **Write MIDI Patterns**: Create broken beat MIDI clips in 126 BPM for Kick, Percu, and Hiss tracks.
