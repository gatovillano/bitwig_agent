#!/usr/bin/env python3
"""Guarda el estado completo de la percusion FOSSORA (patrones + parametros) para poder
reconstruirlo tras reiniciar Bitwig."""
import json, rpc, time

OUT = "fossora_state.json"
K = rpc.find("FOSSORA Kick Gabber")
P = rpc.find("FOSSORA Percu Metal")
S = rpc.find("FOSSORA Siseos Vapor")
assert None not in (K,P,S), (K,P,S)

state = {"tempo": rpc.call("/api/project")["tempo"], "tracks": {}}
for layer, ti in (("kick",K),("perc",P),("sh",S)):
    ins = rpc.inspect(ti)
    devs = []
    for d in ins["devices"]:
        devs.append({
            "index": d["index"], "name": d["name"],
            "params": {p["name"]: p["value"] for p in d.get("parameters",[])},
            "pages": d.get("pages",[]),
        })
    clips = {}
    for s in range(4):
        c = rpc.call("/api/clip/inspect", {"track": ti, "slot": s})
        if c.get("has_content"):
            clips[str(s)] = c.get("notes",[])
    state["tracks"][layer] = {
        "index": ti, "volume": ins.get("volume"), "pan": ins.get("pan"),
        "devices": devs, "clips": clips,
    }
json.dump(state, open(OUT,"w"), indent=1)
n = sum(len(v) for t in state["tracks"].values() for v in t["clips"].values())
print(f"guardado {OUT}: {n} notas, tempo {state['tempo']}")
for layer, t in state["tracks"].items():
    print(f"  {layer}: {len(t['clips'])} clips, {len(t['devices'])} devices, vol={t['volume']}")
