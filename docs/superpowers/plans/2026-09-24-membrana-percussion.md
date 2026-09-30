# Membrana Percussion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete 126 BPM hybrid broken beat percussion section for Membrana in Bitwig Studio via Bitwig MCP tools.

**Architecture:** 3-track percussive group (`Kick Gabber FM`, `Percu Organica Rota`, `Siseos & Vapor Granular`) routed through a master `Percu Membrana` bus with `Compressor+`, `Saturator`, `Filter+`, `Tool`, `EQ+`, and `Delay+` devices and custom MIDI patterns.

**Tech Stack:** Bitwig Studio, Bitwig MCP Server (`control_transport`, `add_instrument_track`, `add_audio_effect`, `set_device_parameter`, `write_notes`, `group_tracks`).

## Global Constraints
- Tempo: Exactly 126.00 BPM.
- Key/Root: F / F0-F1 range for Kick sub-impact.
- Ducking: 100% Sidechain Mix on delay/compression.

---

### Task 1: Setup Transport Tempo & Track Structure in Bitwig Studio

**Files:**
- Create: `docs/superpowers/plans/2026-09-24-membrana-percussion.md`

**Interfaces:**
- Produces: Bitwig transport at 126.00 BPM and 3 clean instrument tracks grouped under `Percu Membrana`.

- [ ] **Step 1: Set transport tempo to 126.00 BPM**

Call Bitwig MCP tool `control_transport` with `{ "action": "set_tempo", "tempo": 126.0 }`.

- [ ] **Step 2: Add Track 01 - Kick Gabber FM**

Call Bitwig MCP tool `add_instrument_track` with `{ "name": "Kick Gabber FM", "instrument": "Polymer" }`.

- [ ] **Step 3: Add Track 02 - Percu Organica Rota**

Call Bitwig MCP tool `add_instrument_track` with `{ "name": "Percu Organica Rota", "instrument": "Sampler" }`.

- [ ] **Step 4: Add Track 03 - Siseos & Vapor Granular**

Call Bitwig MCP tool `add_instrument_track` with `{ "name": "Siseos & Vapor Granular", "instrument": "Polymer" }`.

- [ ] **Step 5: Group Tracks into Percu Membrana**

Call Bitwig MCP tool `group_tracks` with `{ "tracks": ["Kick Gabber FM", "Percu Organica Rota", "Siseos & Vapor Granular"], "name": "Percu Membrana" }`.

---

### Task 2: Insert and Configure Device Processing Chains

**Interfaces:**
- Consumes: `Kick Gabber FM`, `Percu Organica Rota`, `Siseos & Vapor Granular`, and `Percu Membrana` tracks.
- Produces: Fully configured audio effect chains (`Saturator`, `Tool`, `EQ+`, `Filter+`, `Compressor+`, `Delay+`).

- [ ] **Step 1: Configure Kick Gabber FM Processing Chain**

Insert `Saturator` on `Kick Gabber FM` (Drive +12 dB) and `Tool` (St. Width 0%).

- [ ] **Step 2: Configure Percu Organica Rota Processing Chain**

Insert `EQ+` (HPF @ 100 Hz) and `Compressor+` (Attack 10 ms, Ratio 1:4).

- [ ] **Step 3: Configure Siseos & Vapor Granular Processing Chain**

Insert `Filter+` (LFO Sweep 2 kHz - 12 kHz) and `Delay+` (Ducking 50%, Stereo blur 40%).

- [ ] **Step 4: Configure Percu Membrana Group Bus Chain**

Insert `Compressor+` (Glue compression, Threshold -18 dB, Ratio 1:4) and `Saturator` (Drive +2.5 dB).

---

### Task 3: Write Broken Beat 126 BPM MIDI Patterns

**Interfaces:**
- Consumes: Configured tracks in Bitwig.
- Produces: 8-bar 126 BPM syncopated broken beat MIDI clips in slots 0 of each track.

- [ ] **Step 1: Write Kick Gabber FM 126 BPM Pattern**

Call `write_notes` on `Kick Gabber FM` (slot 0) with heavy F1 (pitch 29) broken kick hits on beats 0.0, 1.75, 3.0, 4.5, 6.25, 7.0.

- [ ] **Step 2: Write Percu Organica Rota 126 BPM Pattern**

Call `write_notes` on `Percu Organica Rota` (slot 0) with 16th-note syncopated wood/metal/skin hits (pitches 60, 62, 64, 67, 72) and dynamic ghost note velocities (40-127).

- [ ] **Step 3: Write Siseos & Vapor Granular 126 BPM Pattern**

Call `write_notes` on `Siseos & Vapor Granular` (slot 0) with noise burst steps on off-beats (beats 0.75, 2.25, 3.75, 5.25, 6.75) for organic steam release.

- [ ] **Step 4: Verify and Playback Check**

Inspect project context with `get_project_context` and start transport playback to verify 126 BPM broken beat audio.
