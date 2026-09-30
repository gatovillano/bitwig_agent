# Bitwig MCP Server & AI Agent 🎹🤖⚡

[![Bitwig Studio 6.0+](https://img.shields.io/badge/Bitwig_Studio-6.0%2B-orange?style=flat-square&logo=bitwig)](https://www.bitwig.com/)
[![MCP Server](https://img.shields.io/badge/MCP-Model_Context_Protocol-purple?style=flat-square)](https://modelcontextprotocol.io/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://python.org/)
[![Java 17+](https://img.shields.io/badge/Java-17%2B-red?style=flat-square&logo=openjdk)](https://openjdk.org/)
[![Tests Passing](https://img.shields.io/badge/Tests-69%20Passing-brightgreen?style=flat-square)](https://github.com/gatovillano/bitwig_agent)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

**Bitwig MCP Server & AI Agent** is a comprehensive platform that turns **Bitwig Studio 6.0+** into an AI-controllable, directly programmable music production environment for advanced Large Language Models (**LLMs**) via the open standard **Model Context Protocol (MCP)**.

It empowers assistants such as **Claude Desktop**, **Cursor**, **Antigravity**, **Windsurf**, or any autonomous AI coding agent to:
* Inspect the live session, tracks, instruments, and active plugins in real time.
* Compose complex chord progressions with **smooth Voice Leading** algorithms, sophisticated keyboard voicings, and humanized grooves.
* Generate adaptive basslines harmonically locked to chord changes.
* Write custom melodic and rhythmic sequences note-by-note with surgical precision.
* Inspect clips and visualize their musical content via an **ASCII Piano Roll** directly in the model's response.
* Add native Bitwig instrument tracks (*Polymer*, *Polysynth*, *FM-4*, *Sampler*, *Drum Machine*, etc.) or load `.bwpreset` files.
* Search and recommend synths and audio effects using a **semantic sound design engine** driven by natural language prompts.
* Insert and manage **audio effects**, toggle bypass, open/close plugin GUI windows, and switch presets.
* Control the mixer in real time: track volume (dB or normalized), stereo pan, mute, solo, and arm.
* Control the transport engine (play, stop, set tempo, timeline seek).
* Record live into the **Arranger timeline** using BPM-timed scene launch sequences or manual record controls.
* Organize and automatically group tracks into instrumental families.

---

## 📑 Table of Contents

1. [Why an MCP Server for Bitwig Studio?](#-why-an-mcp-server-for-bitwig-studio)
2. [System Architecture](#-system-architecture)
3. [MCP Tools Reference](#-mcp-tools-reference)
   - [1. `get_project_context`](#1-get_project_context)
   - [2. `create_chord_progression`](#2-create_chord_progression)
   - [3. `create_bassline`](#3-create_bassline)
   - [4. `write_notes`](#4-write_notes)
   - [5. `inspect_track`](#5-inspect_track)
   - [6. `inspect_clip`](#6-inspect_clip)
   - [7. `inspect_arranger`](#7-inspect_arranger)
   - [8. `add_instrument_track`](#8-add_instrument_track)
   - [9. `control_transport`](#9-control_transport)
   - [10. `clear_clip`](#10-clear_clip)
   - [11. `launch_scene`](#11-launch_scene)
   - [12. `record_to_arranger`](#12-record_to_arranger)
   - [13. `add_audio_effect`](#13-add_audio_effect)
   - [14. `control_device`](#14-control_device)
   - [15. `set_device_parameter`](#15-set_device_parameter)
   - [16. `list_audio_effects`](#16-list_audio_effects)
   - [17. `control_track` (Mixer: Volume, Pan, Mute, Solo, Arm)](#17-control_track)
   - [18. `recommend_devices` (Semantic Sound Design Recommender)](#18-recommend_devices)
   - [19. `search_device_browser` & `get_device_info`](#19-search_device_browser--get_device_info)
   - [20. `organize_tracks` & Track Management](#20-organize_tracks)
4. [MCP Client Setup](#-mcp-client-setup)
   - [Claude Desktop](#claude-desktop)
   - [Antigravity / Gemini CLI](#antigravity--gemini-cli)
   - [Cursor & Windsurf](#cursor--windsurf)
5. [Installation & Getting Started](#-installation--getting-started)
   - [Step 1: Install the Extension in Bitwig Studio](#step-1-install-the-extension-in-bitwig-studio)
   - [Step 2: Activate the Controller in Bitwig](#step-2-activate-the-controller-in-bitwig)
   - [Step 3: Install the Python Package](#step-3-install-the-python-package)
6. [Music Theory Engine](#-music-theory-engine)
7. [Alternative Mode: Interactive CLI (`bitwig-agent`)](#-alternative-mode-interactive-cli-bitwig-agent)
8. [Test Suite](#-test-suite)
9. [Project Structure](#-project-structure)
10. [License](#-license)

---

## ⚡ Why an MCP Server for Bitwig Studio?

Until now, using Large Language Models to produce music required manually exporting MIDI files, copy-pasting notes, or wrestling with disconnected scripts outside the DAW.

Thanks to the **Model Context Protocol (MCP)**, the LLM has direct, live access to Bitwig as a native extension of its reasoning:

```
                          ┌─────────────────────────────┐
                          │   MCP Client (Claude,       │
                          │ Cursor, Antigravity, etc.)  │
                          └──────────────┬──────────────┘
                                         │ JSON-RPC (stdio)
                                         ▼
                          ┌─────────────────────────────┐
                          │    Python MCP Server        │
                          │     (bitwig-agent-mcp)      │
                          └──────────────┬──────────────┘
                                         │ Music Engine / HTTP REST
                                         ▼
                          ┌─────────────────────────────┐
                          │  Java Controller Extension  │
                          │   (BitwigAgentBridge :8989) │
                          └──────────────┬──────────────┘
                                         │ Bitwig API Thread-Safe
                                         ▼
                          ┌─────────────────────────────┐
                          │     BITWIG STUDIO 6.0+      │
                          │  Clips, Tracks, Piano Roll  │
                          └─────────────────────────────┘
```

* **Zero-latency context**: The AI can query active tracks, check what synths/plugins are loaded, inspect mixer levels, and see exactly what notes are written in any clip slot.
* **Algorithmic musical creativity**: Rather than random MIDI notes, it leverages a music theory engine that understands complex chord tensions (9ths, 11ths, 13ths, altered dominants), resolves voice movements with minimal semitone jumps (*smooth Voice Leading*), and applies humanized timing and velocity.
* **Non-destructive editing**: Create new clips, overwrite, delete, or inspect without disrupting the producer's creative flow.

---

## 🏗 System Architecture

The ecosystem consists of three decoupled, high-performance layers:

1. **Java Controller Extension (`BitwigAgentBridge.bwextension`)**:
   - Implements Bitwig Studio 6.0 Controller API (`com.bitwig.extension.controller.ControllerExtension`).
   - Hosts an ultra-lightweight, embedded HTTP REST server on `http://127.0.0.1:8989`.
   - Utilizes `host.scheduleTask()` to ensure all modifications to clips, notes, tracks, mixer faders, and transport happen safely on Bitwig's main controller thread without audio glitches.

2. **Python MCP Server (`bitwig-agent-mcp`)**:
   - Exposes standard MCP tools over `stdio`.
   - Bridges the protocol with the music theory engine, semantic device knowledge base, and the Bitwig HTTP client.

3. **Music Theory Engine (`bitwig_agent.theory`) & Device Intelligence (`bitwig_agent.devices`)**:
   - Universal harmonic parser supporting standard modern jazz and pop notation.
   - Euclidean Voice Leading optimizer that minimizes distance between successive chords.
   - Dynamic rhythmic groove generator (`sustained`, `lofi`, `syncopated`, `quarter_stabs`, `arpeggio`).
   - Gaussian humanizer with velocity contours and micro-timing jitter.
   - Comprehensive Bitwig sound design knowledge base and semantic recommender.

---

## 🛠 MCP Tools Reference

Here is the complete reference of all tools exposed by the MCP server:

### 1. `get_project_context`
Inspects the global state of the Bitwig Studio project.
* **Arguments**: None.
* **Returns**: JSON object with project tempo (BPM), playing state (`isPlaying`), playhead position, and a list of all tracks (index, name, type, mute, solo, arm, and occupied clip slots).
* **Example response**:
  ```json
  {
    "tempo": 120.0,
    "isPlaying": false,
    "tracks": [
      {
        "index": 0,
        "name": "Rhodes Piano",
        "arm": false,
        "mute": false,
        "solo": false,
        "occupied_slots": [0, 1]
      },
      {
        "index": 1,
        "name": "Sub Bass",
        "arm": false,
        "mute": false,
        "solo": false,
        "occupied_slots": [0]
      }
    ]
  }
  ```

---

### 2. `create_chord_progression`
Generates and writes a harmonically voiced, humanized chord progression to a clip on the specified track.
* **Arguments**:
  | Parameter | Type | Default | Description |
  |---|---|---|---|
  | `track` | `string` | *(Required)* | Track index (e.g. `"0"`) or name (e.g. `"Keys"`, `"Rhodes"`). |
  | `chords` | `List[string]` | *(Required)* | List of chord symbols, e.g. `["Dm9", "G13", "Cmaj9", "A7alt"]`. |
  | `slot` | `integer` | `0` | Clip Launcher slot index (0-based). |
  | `beats_per_chord` | `number` | `4.0` | Duration in beats per chord (`4.0` = 1 bar in 4/4). |
  | `voicing_style` | `string` | `"keyboard"` | Voicing algorithm: `"keyboard"`, `"rootless"` (modern jazz voicings omitting the root), or `"drop2"`. |
  | `rhythm_pattern` | `string` | `"sustained"` | Groove pattern: `"sustained"`, `"lofi"`, `"syncopated"`, `"quarter_stabs"`, or `"arpeggio"`. |
  | `include_bass` | `boolean` | `true` | Whether to include a low bass root note in the chord clip. |
  | `humanize` | `boolean` | `true` | Applies organic velocity contours and micro-timing variations. |
  | `launch` | `boolean` | `false` | Automatically triggers clip playback upon creation. |

* **Example prompt for the LLM**:
  > *"Create a Neo-Soul progression on the 'Rhodes' track: Dm9 -> G13 -> Cmaj9 -> A7b9#11 with a lofi rhythm pattern, rootless voicings, and start playback."*

---

### 3. `create_bassline`
Generates a dedicated bassline matching a chord progression on the specified bass track.
* **Arguments**:
  | Parameter | Type | Default | Description |
  |---|---|---|---|
  | `track` | `string` | *(Required)* | Track index or name (e.g. `"Bass"`, `"Sub"`). |
  | `chords` | `List[string]` | *(Required)* | Chord symbols for the bassline to accompany. |
  | `slot` | `integer` | `0` | Clip slot index. |
  | `beats_per_chord` | `number` | `4.0` | Length in beats per chord. |
  | `style` | `string` | `"syncopated"` | Rhythm style: `"root"` (simple root hits), `"syncopated"` (funky groove), or `"walking"` (jazz walking bass). |
  | `launch` | `boolean` | `false` | Launches clip playback immediately. |

---

### 4. `write_notes`
Writes arbitrary custom note sequences into a clip slot note-by-note with surgical control over pitch, timing, duration, velocity, and channel.
* **Arguments**:
  | Parameter | Type | Default | Description |
  |---|---|---|---|
  | `track` | `string` | *(Required)* | Track index or name. |
  | `notes` | `List[object]` | *(Required)* | List of note event dictionaries. |
  | `slot` | `integer` | `0` | Clip slot index. |
  | `beats` | `number` | `16.0` | Clip loop length in beats (auto-extends if notes exceed this length). |
  | `clear` | `boolean` | `true` | Clears previous clip notes before writing. |
  | `launch` | `boolean` | `false` | Immediately plays the clip. |
  | `humanize` | `boolean` | `false` | Applies subtle humanization to velocities and timing. |

* **Note event structure in `notes`**:
  - `pitch`: MIDI note number (`0-127`) or note name with octave (`"C4"`, `"F#3"`, `"Bb2"`, `"Db5"`).
  - `step`: 16th-note step index (`0` = beat 1, `4` = beat 2, etc.) **or** `beat` (float: `0.0`, `1.5`, `2.25`).
  - `duration`: Length in beats (`1.0` = quarter note, `0.25` = 16th note, `0.5` = 8th note).
  - `velocity`: MIDI velocity from `1` to `127` (default: `100`).
  - `channel`: MIDI channel from `0` to `15` (default: `0`).

---

### 5. `inspect_track`
Allows the AI to inspect a track's complete configuration.
* **Arguments**: `track` (`string`, required): Track index or name.
* **Returned details**:
  - Mixer parameters: Volume, pan, mute, solo, arm.
  - Complete device chain: Synths (*Polymer*, *Polysynth*), VST/CLAP plugins, audio effects, and loaded presets.
  - List of clips present across all launcher slots.

---

### 6. `inspect_clip`
Inspects an individual clip in the Clip Launcher and returns an **ASCII Piano Roll** visual representation.
* **Arguments**: `track` (`string`), `slot` (`integer`, default `0`).
* **ASCII Piano Roll representation**:
  ```text
    G4  | · · · · · · · · [═══════] · · · · · · · · |
    E4  | · · · · · · · · [═══════] · · · · · · · · |
    C4  | [═══════] · · · · · · · · · · · · · · · · |
    A3  | [═══════] · · · · · · · · · · · · · · · · |
        +---+---+---+---+---+---+---+---+---+---+---+
  Beat:   1       2       3       4       5       6
  ```

---

### 7. `inspect_arranger`
Inspects the state of the Bitwig **Arranger timeline**:
* **Timeline state**: Playhead position (beats and bars), project tempo, recording/overdub status, and loop bounds.
* **Cue Markers (Song Structure)**: List of section markers with name, color, bar number, and beat position (e.g. Intro, Verse, Chorus, Drop, Outro).
* **Selected Arranger Clip**: If a clip is active in the arranger timeline, inspects bounds (`play_start`, `play_stop`, `loop_length`), parent track, notes details, and a full ASCII Piano Roll.

---

### 8. `add_instrument_track`
Creates a new instrument track or loads a native synth/drum machine/preset onto a track.
* **Arguments**:
  | Parameter | Type | Default | Description |
  |---|---|---|---|
  | `name` | `string` | *(Required)* | Name for the track (e.g. `"Lead Synth"`, `"Drum Rack"`). |
  | `instrument` | `string` | `"polymer"` | Instrument: `"polymer"`, `"polysynth"`, `"fm-4"`, `"phase-4"`, `"sampler"`, `"drum_machine"`, `"organ"`, `"poly_grid"`, `"instrument_layer"`, or path to a `.bwpreset`. |
  | `position` | `integer` | `-1` | Position to insert track at (`-1` for end). |
  | `track` | `string` | `null` | If specified, adds the instrument to an existing track instead of creating a new one. |

---

### 9. `control_transport`
Controls the Bitwig playback engine, recording, and timeline position.
* **Arguments**:
  - `action`: `"play"`, `"stop"`, `"restart"`, `"set_tempo"`, `"record"`, `"stop_record"`, `"toggle_record"`, `"return_to_arrangement"`, or `"set_position"`.
  - `tempo`: New tempo in BPM (e.g. `85.0`, `124.0`).
  - `position`: Timeline position in beats (e.g. `0.0` = bar 1, `16.0` = bar 5).

---

### 10. `clear_clip`
Clears notes from a clip slot or removes the clip completely.
* **Arguments**:
  - `track`: Track index or name.
  - `slot`: Clip slot index (default: `0`).
  - `action`: `"notes"` (clears note data while keeping clip) or `"delete"` (deletes the clip entirely).

---

### 11. `launch_scene`
Launches an entire scene row in the Clip Launcher, triggering all clips in that row across all tracks simultaneously.
* **Arguments**: `scene` (`integer`, default `0`).

---

### 12. `record_to_arranger`
Enables the AI to record arrangements and clip sequences directly into the **Arranger timeline** in real time.
* **Arguments**:
  | Parameter | Type | Default | Description |
  |---|---|---|---|
  | `sequence` | `array` | `null` | Ordered list of sections. Each section specifies `scene` (int) and length in `bars` or `beats`. Example: `[{"scene": 0, "bars": 4}, {"scene": 1, "bars": 8}]`. |
  | `start_beat` | `number` | `0.0` | Timeline beat position where recording starts. |
  | `action` | `string` | `"record_sequence"` | Operation mode: `"record_sequence"`, `"start"`, `"stop"`, `"toggle"`, or `"return_to_arrangement"`. |
  | `scene` | `integer` | `null` | Scene index to launch immediately if action is `"start"`. |
  | `stop_on_finish` | `boolean` | `true` | Stops playback when sequence recording finishes. |
  | `return_to_arrangement` | `boolean` | `true` | Restores tracks to arrangement playback when recording finishes. |

---

### 13. `add_audio_effect`
Inserts a native Bitwig audio effect into an existing track or creates a dedicated global Effect/Return track (`Effect Track`).
* **Arguments**:
  | Parameter | Type | Default | Description |
  |---|---|---|---|
  | `effect` | `string` | *(Required)* | Effect name (e.g. `"delay+"`, `"reverb"`, `"compressor"`, `"eq+"`, `"saturator"`, `"flanger"`, `"chorus"`) or `.bwpreset` path. |
  | `track` | `string` | `null` | Track index or name where the effect should be added (not required if `create_effect_track` is true). |
  | `position` | `string`/`int` | `"end"` | Position in chain: `"end"`, `"start"`, or integer index to insert after. |
  | `create_effect_track` | `boolean` | `false` | If true, creates a new Effect/Return track and loads the effect there. |

---

### 14. `control_device`
Controls a device or audio effect: bypass/enable, remove, open/close GUI window, or switch presets.
* **Arguments**:
  | Parameter | Type | Default | Description |
  |---|---|---|---|
  | `track` | `string`/`int` | *(Required)* | Track index or name containing the device. |
  | `device` | `string`/`int` | *(Required)* | Device index or name (e.g. `"Polymer"`, `"Reverb"`). |
  | `action` | `string` | `"toggle"` | Action: `"set_enabled"`, `"toggle"`, `"delete"`, `"next_preset"`, `"previous_preset"`, `"toggle_window"` (opens/closes GUI window), `"open_window"`, `"close_window"`, or `"select"`. |
  | `enabled` | `boolean` | `null` | Target state if action is `"set_enabled"`. |

---

### 15. `set_device_parameter`
Adjusts parameters on any device or effect (filter cutoff, resonance, EQ gain, reverb decay, etc.).
* **Arguments**:
  | Parameter | Type | Default | Description |
  |---|---|---|---|
  | `track` | `string`/`int` | *(Required)* | Track index or name. |
  | `device` | `string`/`int` | *(Required)* | Device index or name. |
  | `parameter` | `string`/`int` | *(Required)* | Parameter name (e.g. `"Cutoff"`, `"Gain"`, `"Q"`) or remote control index (0-7). |
  | `value` | `number` | *(Required)* | Value in Hz for frequency, dB for gain, float for Q, or normalized (0.0 to 1.0). |
  | `page` | `string` | `null` | Remote control page name (e.g. `"Main"`, `"EQ"`). |
  | `normalized` | `boolean` | `null` | If true, treats value as normalized (0.0 to 1.0). |

---

### 16. `list_audio_effects`
Returns the categorized catalog of native Bitwig Studio audio effects (Reverb, Delay, Dynamics, EQ & Filters, Distortion, Modulation, Utility & Spatial).
* **Arguments**: `category` (`string`, optional): Filter by category (e.g. `"reverb"`, `"delay"`, `"dynamics"`, `"eq"`, `"distortion"`, `"modulation"`).

---

### 17. `control_track`
Controls track mixer faders and channel parameters in real time (volume, stereo pan, mute, solo, arm, and renaming).
* **Arguments**:
  | Parameter | Type | Default | Description |
  |---|---|---|---|
  | `track` | `string`/`int` | *(Required)* | Track index or name. |
  | `volume` | `number` | `null` | Volume level: normalized (0.0 to 1.0, where ~0.8 is 0dB) or negative dB (e.g. `-6.0`, `-12.0`). |
  | `pan` | `number` | `null` | Bipolar stereo pan from `-1.0` (Hard Left) through `0.0` (Center) to `+1.0` (Hard Right). |
  | `mute` | `boolean`/`string` | `null` | Mute state (`true`, `false`) or `"toggle"`. |
  | `solo` | `boolean`/`string` | `null` | Solo state (`true`, `false`) or `"toggle"`. |
  | `arm` | `boolean`/`string` | `null` | Record arm state (`true`, `false`) or `"toggle"`. |
  | `name` | `string` | `null` | Optional new name for the track. |

*Direct convenience tools are also available: `set_track_volume`, `set_track_pan`, and `toggle_track_mute`.*

---

### 18. `recommend_devices`
Intelligent semantic sound design recommender. Recommends native Bitwig instruments, audio effects, or containers based on a natural language description.
* **Arguments**:
  | Parameter | Type | Default | Description |
  |---|---|---|---|
  | `description` | `string` | *(Required)* | Natural language sound description (e.g. `"warm vintage analog pad for synthwave"`, `"punchy 808 sub bass"`, `"spacious hall reverb with pre-delay"`). |
  | `num_results` | `integer` | `5` | Maximum number of recommendations to return. |
  | `category` | `string` | `null` | Optional category filter (`"Synth"`, `"Reverb"`, `"Delay"`, `"Dynamics"`, `"EQ"`, etc.). |
  | `type` | `string` | `null` | Optional device type filter (`"Instrument"`, `"Audio Effect"`, `"Container"`). |
* **Returns**: Recommended devices ranked by relevance, contextual explanations, key parameters, and production tips.

---

### 19. `search_device_browser` & `get_device_info`
* **`search_device_browser`**: Searches the Bitwig device catalog by name, sonic characteristics, or sound design tags.
* **`get_device_info`**: Retrieves full technical specifications, synthesis methods (subtractive, FM, wavetable, granular), key parameters, and usage tips for any device.

---

### 20. `organize_tracks` & Track Management
Advanced session organization tools:
* **`move_track`**: Moves tracks before or after another track, or to the start/end of the project.
* **`group_tracks`**: Creates a group track containing the specified tracks.
* **`ungroup_track`**: Ungroups a group track, returning child tracks to the root level.
* **`organize_tracks`**: Executes full session reorganizations or **automatic grouping** (`auto_group=true`) by instrument family (Drums, Bass, Synths, FX).

---

## 🔌 MCP Client Setup

### Claude Desktop

Edit your Claude Desktop configuration file:
* **Linux**: `~/.config/Claude/claude_desktop_config.json`
* **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the `bitwig` server entry:

```json
{
  "mcpServers": {
    "bitwig": {
      "command": "/path/to/bitwig_agent/venv/bin/bitwig-agent-mcp"
    }
  }
}
```

> 💡 **Note**: Replace `/path/to/bitwig_agent` with the absolute path to your repository clone.

---

### Antigravity / Gemini CLI

If using Google Antigravity, add the server definition to your tool configuration or in your active workspace:

```json
{
  "mcpServers": {
    "bitwig": {
      "command": "python",
      "args": ["-m", "bitwig_agent.mcp.server"],
      "cwd": "/path/to/bitwig_agent/python"
    }
  }
}
```

---

### Cursor & Windsurf

In Cursor (under `.cursor/mcp.json` or in `Settings -> Features -> MCP`):

```json
{
  "mcpServers": {
    "bitwig": {
      "command": "/path/to/bitwig_agent/venv/bin/bitwig-agent-mcp"
    }
  }
}
```

Restart your client or reload MCP servers to see the full set of Bitwig tools available.

---

## 🚀 Installation & Getting Started

### Prerequisites
* **Bitwig Studio 6.0 or higher** (Linux, macOS, or Windows).
* **Java 17 or higher** (OpenJDK 17 recommended).
* **Python 3.10 or higher**.

---

### Step 1: Install the Extension in Bitwig Studio

The repository includes a ready-to-use compiled extension at:
`java-extension/build/BitwigAgentBridge.bwextension`

Copy it to your Bitwig Extensions folder:
* **Linux**: `~/Bitwig Studio/Extensions/`
* **macOS**: `~/Documents/Bitwig Studio/Extensions/`
* **Windows**: `%USERPROFILE%\Documents\Bitwig Studio\Extensions\`

On Linux, you can copy it directly:
```bash
mkdir -p "$HOME/Bitwig Studio/Extensions"
cp java-extension/build/BitwigAgentBridge.bwextension "$HOME/Bitwig Studio/Extensions/"
```

*(Optional) To recompile the Java extension from source:*
```bash
./java-extension/build.sh
```

---

### Step 2: Activate the Controller in Bitwig

1. Open **Bitwig Studio**.
2. Open Settings via `Ctrl + ,` (or `Cmd + ,` on macOS).
3. Click the **Controllers** tab.
4. Click **Add controller**.
5. Select **BitwigAgent** -> **Bitwig Agent Bridge**.
6. A notification will appear in Bitwig:
   > *"Bitwig Agent Bridge Active (port 8989)"*

Verify connection in your terminal:
```bash
curl http://127.0.0.1:8989/api/status
```
It will return:
```json
{"status":"ok","name":"Bitwig Agent Bridge","version":"1.0.0","bitwig_api":18}
```

---

### Step 3: Install the Python Package

1. Navigate to the `python` directory:
   ```bash
   cd python
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install in editable mode:
   ```bash
   pip install -e .
   ```

The `bitwig-agent` and `bitwig-agent-mcp` executables will now be available in your virtual environment.

---

## 🎼 Music Theory Engine

The music theory core in `bitwig_agent.theory` solves one of the hardest challenges in AI music composition: **making chords sound musical and natural**.

### Key Features:
1. **Flexible Harmonic Syntax**:
   - Major, minor, augmented, diminished (`C`, `Am`, `Caug`, `Bdim`).
   - Extensions & tensions: 7ths, 9ths, 11ths, 13ths (`Dm9`, `F#m11`, `G13`, `Cmaj9`).
   - Suspended chords (`Dsus4`, `Gsus2`).
   - Altered dominants: `G7alt`, `A7b9#11`, `E7#9`, `C7b13`.
   - Slash chords: `F/G`, `Db/C`, `Ebmaj7/Bb`.

2. **Smooth Voice Leading**:
   - Computes semitone distances across all inversions of the next chord and selects the one that minimizes inner-voice movement.

3. **Voicing Styles**:
   - `keyboard`: Balanced 4-to-5 voice open keyboard voicings.
   - `rootless`: Modern jazz voicings (Bill Evans / Wynton Kelly) where the root is omitted so the bass plays it, leaving space for 3rd, 7th, 9th, and 11th/13th extensions.
   - `drop2`: Drop-2 voicings where the second highest voice is lowered by one octave, ideal for horn sections and wide pads.

4. **Grooves and Humanization**:
   - Built-in rhythmic patterns: sustained chords (`sustained`), syncopated groove (`syncopated`), laid-back lofi syncopation (`lofi`), quarter note hits (`quarter_stabs`), and arpeggios (`arpeggio`).
   - Gaussian humanization with velocity dynamics and micro-timing jitter to prevent a mechanical MIDI feel.

---

## 💻 Alternative Mode: Interactive CLI (`bitwig-agent`)

In addition to the MCP server, the package provides an interactive terminal command-line interface (**CLI**) with autocompletion powered by **LiteLLM**:

```bash
bitwig-agent
```

### CLI Features:
* **Multi-Provider Support**:
  - **Google Gemini** (`gemini-2.5-flash`, `gemini-2.5-pro`).
  - **Anthropic Claude** (`claude-3-7-sonnet`, `claude-3-5-haiku`).
  - **OpenAI** (`gpt-4o`, `gpt-4o-mini`, `o3-mini`).
  - **Groq** (`llama-3.3-70b-versatile`, `mixtral-8x7b-32768`).
  - **Local Ollama** (local offline models with zero API cost).
  - **Antigravity OAuth2** (native integration with Google Antigravity accounts).
* **Interactive Slash Commands**:
  - `/provider`: Switch AI provider on the fly.
  - `/model`: Choose model from available provider models.
  - `/keys`: Securely manage locally stored API keys.
  - `/session` & `/resume`: Conversation history and persistent session management.
  - `/status`: Diagnostics of the Bitwig bridge and active model.

---

## 🧪 Test Suite

The project includes an automated suite of **69 unit and integration tests**:

```bash
cd python
pytest -v
```

### What is tested:
* **`test_theory.py`**: Chord parsing, inversions, voice leading, and note generation.
* **`test_devices.py`**: Sound design semantic recommender, browser search, device info, and category filters.
* **`test_client.py`**: Pydantic models, `NoteEvent` serialization, HTTP connector, Arranger recording, and mixer controls.
* **`test_llm_tools.py`**: Execution of all MCP tools (`control_track`, `recommend_devices`, `add_audio_effect`, `control_device`, `record_to_arranger`, etc.) and argument validation.
* **`test_visualization.py`**: ASCII Piano Roll generation and clip visualizer.
* **`test_completer.py` & `test_session.py`**: Interactive REPL menus, autocompletion, and session persistence.

---

## 📁 Project Structure

```
bitwig_agent/
├── README.md                      # Main documentation & MCP reference
├── .gitignore                     # Git ignore rules
├── .env.example                   # Environment variables template
├── java-extension/                # Native Bitwig Studio extension
│   ├── build.sh                   # Compilation & packaging script
│   ├── build/
│   │   └── BitwigAgentBridge.bwextension  # Compiled extension binary
│   └── src/main/java/com/bitwig/agent/
│       ├── BitwigAgentExtension.java      # Bitwig controller extension
│       ├── BridgeHttpServer.java          # Embedded REST server (:8989)
│       └── JsonUtils.java                 # Lightweight JSON parser
└── python/                        # MCP Server, CLI & Music Theory Engine
    ├── pyproject.toml             # Package configuration & dependencies
    ├── bitwig_agent/
    │   ├── mcp/
    │   │   └── server.py          # Stdio MCP Server (bitwig-agent-mcp)
    │   ├── llm/
    │   │   └── tools.py           # Tool definitions & execution dispatcher
    │   ├── devices.py             # Sound design knowledge base & recommender
    │   ├── theory/                # Music theory, voicings & rhythm engine
    │   ├── client.py              # Typed Bitwig HTTP REST client (Pydantic)
    │   ├── cli.py                 # Interactive terminal REPL
    │   └── config.py              # Configuration & credential management
    └── tests/                     # Automated test suite (pytest)
```

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

<div align="center">
  Built with ❤️ for the Bitwig Studio music production and AI agent community.
</div>
