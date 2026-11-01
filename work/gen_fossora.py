#!/usr/bin/env python3
"""
Percusion sincopada inspirada en 'Fossora' (Bjork, 2022).
4 escenas x 8 compases, con complejidad CRECIENTE (capas acumulativas).

Recursos rítmicos de referencia (Fossora):
  - Kick gabber: sub pesado + click mecanico, tempomedia (Atopos)
  - "clattering percussion": golpes metalicos, densos y desplazados
  - Siseos: shimmer filtrado en agudos
"""
import json

BPM = 110.0
BAR = 4                 # beats por compas
SCENES = 4
BARS_PER_SCENE = 8
CLIP_BEATS = BAR * BARS_PER_SCENE      # 32 beats

# --- helper --------------------------------------------------------------
def n(beat, dur, vel, pitch):
    """nota -> write_notes. beat en beats, dur en beats, step en 16avos."""
    return {"pitch": pitch,
            "step": int(round(beat * 4)),
            "duration": max(0.05, round(dur * 4) / 4.0),
            "velocity": vel}

KICK_P = 29   # F1  -> sub grave (raiz F)
PERC_P = [60, 64, 67, 72]   # C4 E4 G4 C5 -> metalico
SH_P   = [84, 86, 88, 91]   # agudos siseo

kick, perc, sh = [], [], []

def bar_offset(scene_idx):
    return scene_idx * CLIP_BEATS

# ======================================================================
# ESCENA 1 - "Semilla"  (compases 1-8)
# Solo kick. Pesado, con un contratiempo. Maxima claridad.
# ======================================================================
o = bar_offset(0)
for b in range(8):
    base = o + b * BAR
    # offsets SIEMPRE dentro de [0,4): evita colisiones entre compases
    for off, v in [(0.0, 120), (2.0, 104), (2.75, 90), (3.5, 86)]:
        kick.append(n(base + off, 0.25, v, KICK_P))

# ======================================================================
# ESCENA 2 - "Raiz"  (compases 9-16)
# Kick mas sincopado (entra el 16avo) + percusion metalica en offbeats.
# ======================================================================
o = bar_offset(1)
for b in range(8):
    base = o + b * BAR
    for off, v in [(0.0, 122), (1.75, 98), (2.75, 104),
                   (3.0, 92), (3.5, 86)]:
        kick.append(n(base + off, 0.25, v, KICK_P))
    # metalica: offbeats y contratiempos
    for off, v, p in [(0.5, 96, 60), (1.0, 70, 64), (1.5, 104, 60),
                       (2.5, 88, 64), (3.25, 76, 67), (3.75, 66, 72)]:
        perc.append(n(base + off, 0.18, v, p))

# ======================================================================
# ESCENA 3 - "Brote"  (compases 17-24)
# Kick en 16avos con mas sincopa, perc mas densa, entra el siseo.
# ======================================================================
o = bar_offset(2)
for b in range(8):
    base = o + b * BAR
    for off, v in [(0.0, 124), (0.75, 100), (1.5, 106), (2.0, 118),
                   (2.75, 102), (3.5, 110), (3.75, 92)]:
        kick.append(n(base + off, 0.22, v, KICK_P))
    for off, v, p in [(0.25, 100, 60), (0.5, 72, 64), (0.75, 108, 60),
                       (1.25, 86, 67), (1.5, 74, 64), (1.75, 96, 60),
                       (2.25, 104, 60), (2.5, 70, 64), (2.75, 110, 60),
                       (3.25, 88, 67), (3.5, 76, 64), (3.75, 98, 60)]:
        perc.append(n(base + off, 0.16, v, p))
    # siseo: shimmer disperso
    for off, v, p in [(0.25, 58, 84), (2.75, 54, 88), (3.5, 48, 86)]:
        sh.append(n(base + off, 0.2, v, p))

# ======================================================================
# ESCENA 4 - "Fructificacion"  (compases 25-32)
# Maxima densidad. Kick relentlessly en 16avos, perc en stabs,
# siseo en capas. El clatter se vuelve gabber total.
# ======================================================================
o = bar_offset(3)
for b in range(8):
    base = o + b * BAR
    for off, v in [(0.0, 126), (0.5, 100), (1.0, 108), (1.5, 104),
                   (2.0, 120), (2.5, 102), (3.0, 110), (3.5, 106)]:
        kick.append(n(base + off, 0.2, v, KICK_P))
    for off, v, p in [(0.25, 102, 60), (0.5, 72, 64), (0.75, 110, 60),
                       (1.25, 86, 67), (1.5, 74, 64), (1.75, 98, 60),
                       (2.25, 106, 60), (2.5, 70, 64), (2.75, 112, 60),
                       (3.25, 88, 67), (3.5, 76, 64), (3.75, 100, 60)]:
        perc.append(n(base + off, 0.14, v, p))
    for off, v, p in [(0.25, 60, 84), (1.25, 52, 88), (2.25, 58, 86),
                      (3.25, 64, 84), (3.75, 50, 90)]:
        sh.append(n(base + off, 0.2, v, p))

# --- Validacion: cada nota debe caer dentro de su compas ---------------
def validate(lst, layer):
    bad = []
    for x in lst:
        beat = x["step"] / 4.0
        if beat >= CLIP_BEATS:
            bad.append(("fuera de rango", beat))
    # detectar steps duplicados
    seen = {}
    for x in lst:
        seen.setdefault(x["step"], []).append(x)
    dup = {k: len(v) for k, v in seen.items() if len(v) > 1}
    return bad, dup

TOTAL_BEATS = CLIP_BEATS * SCENES   # 128 beats = 32 compases
for layer, lst in (("kick", kick), ("perc", perc), ("sh", sh)):
    bad, dup = validate(lst, layer)
    over = [b for b in bad if b[1] >= TOTAL_BEATS]
    print(f"[validacion] {layer}: fuera_de_rango={len(over)} "
          f"steps_duplicados={len(dup)} (total_beats={TOTAL_BEATS})")
    if dup:
        print("   ejemplos dup:", list(dup.items())[:6])
    # por escena: cada nota debe estar en la escena que le corresponde
    for s in range(SCENES):
        lo, hi = s * CLIP_BEATS, (s + 1) * CLIP_BEATS
        c = sum(1 for x in lst if lo <= x["step"] / 4.0 < hi)
        if c:
            print(f"   escena {s+1}: {c:3d} notas")
    # ninguna nota debe caer en huecos entre escenas
    for x in lst:
        beat = x["step"] / 4.0
        sc = int(beat // CLIP_BEATS)
        if sc >= SCENES:
            print(f"   !! nota fuera de escena: beat {beat}")

out = {"tempo": BPM, "clip_beats": CLIP_BEATS,
       "notes": {"kick": kick, "perc": perc, "sh": sh}}
json.dump(out, open("fossora_patterns.json", "w"), indent=1)

for k, v in out["notes"].items():
    if v:
        print(f"{k:5s} {len(v):4d} notas | steps {min(x['step'] for x in v)}-{max(x['step'] for x in v)}"
              f" | beats {min(x['step'] for x in v)/4:.1f}-{max(x['step'] for x in v)/4:.1f}")
    else:
        print(f"{k:5s}    0 notas")
