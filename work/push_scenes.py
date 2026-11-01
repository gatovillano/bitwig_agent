#!/usr/bin/env python3
"""Escribe los patrones por escena en los slots del Clip Launcher via el bridge."""
import json, urllib.request

BRIDGE = "http://127.0.0.1:8989"
PAT = json.load(open("fossora_patterns.json"))
notes = PAT["notes"]

SCENES = [("Semilla", 0), ("Raiz", 32), ("Brote", 64), ("Fructificacion", 96)]
CLIP_BEATS = 32   # 8 compases

# track index, nombre esperado, layer
# Cada capa tiene un slot POR ESCENA GLOBAL (indice de escena = indice de slot).
# Así, lanzar la escena N hace sonar la version de esa capa para la escena N,
# y las capas que aun no existen simplemente no suenan -> acumulacion natural.
# scene_slots indica en que escena empieza a existir cada capa.
# slot == indice de escena (fila del Clip Launcher).
# Cada capa existe solo desde la escena en que entra:
#   kick -> desde escena 1 | perc -> desde escena 2 | siseo -> desde escena 3
# Con "Stop Clips" activo (default de Bitwig) lanzar la escena N detiene la N-1,
# de modo que cada fila suena COMPLETA y progresivamente mas densa.
TRACKS = {
    "kick": (0, "Kick Gabber",    {0: 0, 1: 1, 2: 2, 3: 3}),
    "perc": (2, "Percu Organica", {1: 1, 2: 2, 3: 3}),
    "sh":   (3, "Siseos & Vapor", {2: 2, 3: 3}),
}

def post(path, payload):
    req = urllib.request.Request(
        BRIDGE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def get(path):
    with urllib.request.urlopen(BRIDGE + path, timeout=15) as r:
        return json.loads(r.read().decode())

# Verificar estado del proyecto antes de escribir
proj = get("/api/project")
idx = {t["name"]: t["index"] for t in proj["tracks"]}
print("tracks:", {k: v for k, v in idx.items() if k in
                  ("Kick Gabber", "Percu Organica", "Siseos & Vapor")})

written = []
for layer, (tidx, tname, slots) in TRACKS.items():
    actual = idx.get(tname)
    if actual is None:
        print(f"!! no existe track {tname}, salto capa {layer}")
        continue
    if actual != tidx:
        print(f"!! {tname} esta en indice {actual}, no {tidx}. uso {actual}")
        tidx = actual
    # Escena -> slot
    for si, (sname, sstart) in enumerate(SCENES):
        if si not in slots:
            print(f"  {tname:16s} escena {si+1} {sname:16s}: capa aun no existe (ok)")
            continue
        slot = slots[si]
        # notas de esta capa dentro del rango de la escena
        # n["step"] es indice de 16avos -> beats = step/4.
        lo = sstart * 4
        hi = (sstart + CLIP_BEATS) * 4
        sel = [n for n in notes[layer] if lo <= n["step"] < hi]
        if not sel:
            print(f"  {tname} slot{slot} ({sname}): vacio, no escribo")
            continue
        # rebase a 0 dentro del clip
        out = [{"step": n["step"] - sstart * 4,
                "pitch": n["pitch"],
                "velocity": n["velocity"],
                "duration": n["duration"],
                "channel": n.get("channel", 0)} for n in sel]
        res = post("/api/clip/notes", {
            "track": tidx, "slot": slot, "clear": True,
            "beats": CLIP_BEATS, "notes": out})
        written.append((tname, slot, sname, len(out), res.get("status", res)))
        print(f"  {tname:16s} slot {slot}  escena {si+1} {sname:16s} {len(out):3d} notas -> {res.get('status', res)}")

print()
print("total clips escritos:", len(written))
