#!/usr/bin/env python3
"""Reconstruccion atomica de la percusion Fossora: tracks + instrumentos + escenas."""
import json, urllib.request, urllib.error, time

BRIDGE = "http://127.0.0.1:8989"

def call(path, payload=None, method=None):
    if payload is None:
        req = urllib.request.Request(BRIDGE + path, method="GET")
    else:
        req = urllib.request.Request(BRIDGE + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method=method or "POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: return {"__error__": json.loads(e.read().decode()).get("error", str(e))}
        except Exception: return {"__error__": str(e)}

def track_list():
    return call("/api/project")["tracks"]

def find(name):
    for t in track_list():
        if t["name"] == name: return t["index"]
    return None

PAT = json.load(open("fossora_patterns.json"))
notes = PAT["notes"]
CLIP = 32

# Nombres con prefijo para aislar del agente concurrente.
LAYERS = [
    # (capa, track, instrumento, slots por escena)
    ("kick", "FOSSORA Kick Gabber", "polymer",  {0:0, 1:1, 2:2, 3:3}),
    ("perc", "FOSSORA Percu Metal", "fm-4",     {1:1, 2:2, 3:3}),
    ("sh",   "FOSSORA Siseos Vapor", "phase-4",  {2:2, 3:3}),
]
SCENE_START = [0, 32, 64, 96]

print("=== 1. Crear/ajustar tracks ===")
for layer, tname, instr, slots in LAYERS:
    ti = find(tname)
    if ti is None:
        # ¿existe un track con ese nombre pero distinto? buscar por dispositivo
        r = call("/api/instrument/add", {"name": tname, "instrument": instr, "position": -1})
        if "__error__" in r:
            print(f"  ERROR creando {tname}: {r['__error__'][:150]}")
            continue
        ti = find(tname)
        print(f"  + {tname} (idx {ti}) instr={instr}")
    else:
        print(f"  = {tname} (idx {ti}) ya existe")
        # asegurar instrumento correcto
        d = call("/api/track/inspect", {"track": ti})
        devs = [x["name"] for x in d.get("devices", [])]
        if instr not in devs:
            # borrar instrumentos incorrectos, insertar el correcto
            for i in range(len(devs)-1, -1, -1):
                call("/api/device/control", {"track": ti, "device": i, "action": "delete"})
            call("/api/instrument/add", {"name": tname, "instrument": instr, "track": ti})
            print(f"    instrumentos reemplazados -> {instr}")
    time.sleep(0.15)

print("\n=== 2. Escribir las 4 escenas ===")
for layer, tname, instr, slots in LAYERS:
    ti = find(tname)
    if ti is None: continue
    for si, slot in sorted(slots.items()):
        lo = SCENE_START[si] * 4
        hi = (SCENE_START[si] + CLIP) * 4
        sel = [n for n in notes[layer] if lo <= n["step"] < hi]
        out = [{"step": n["step"] - lo, "pitch": n["pitch"], "velocity": n["velocity"],
                "duration": n["duration"], "channel": n.get("channel", 0)} for n in sel]
        r = call("/api/clip/notes", {"track": ti, "slot": slot, "clear": True,
                                     "beats": CLIP, "notes": out})
        st = r.get("status", r.get("__error__", "?"))
        print(f"  {tname:24s} slot{slot} (escena {si+1}): {len(out):3d} notas -> {st}")
    time.sleep(0.15)

print("\n=== 3. Estructura final ===")
for t in track_list():
    if t["name"].startswith("FOSSORA"):
        print(f'  {t["index"]:2d} {t["name"]:24s} {t.get("type")}')
