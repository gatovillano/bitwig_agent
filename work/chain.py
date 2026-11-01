#!/usr/bin/env python3
"""Configura las cadenas de efectos de la percusion Fossora via el bridge."""
import json, urllib.request, sys

BRIDGE = "http://127.0.0.1:8989"

def call(path, payload=None, method=None):
    if payload is None:
        req = urllib.request.Request(BRIDGE + path, method="GET")
    else:
        req = urllib.request.Request(BRIDGE + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method=method or "POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"__error__": e.read().decode()[:300]}

def tracks():
    p = call("/api/project")
    return {t["name"]: t["index"] for t in p["tracks"]}, p

def devices(track):
    d = call("/api/track/inspect", {"track": track})
    if "__error__" in d: return []
    return [(x["index"], x["name"]) for x in d.get("devices", [])]

def ensure(track, effect, pos="end"):
    """Inserta el efecto si no esta ya presente."""
    names = [n for _, n in devices(track)]
    if effect in names:
        return f"ya existe {effect} en track {track}"
    r = call("/api/effect/add", {"track": track, "effect": effect, "position": pos})
    if "__error__" in r:
        return f"ERROR {effect}: {r['__error__'][:160]}"
    return f"+ {effect} -> track {track}"

def setparam(track, device, param, value, page=None):
    payload = {"track": track, "device": device, "parameter": param, "value": value}
    if page: payload["page"] = page
    r = call("/api/device/parameter", payload)
    if "__error__" in r:
        return f"ERROR {param}: {r['__error__'][:200]}"
    return f"  {param} = {value} (idx {r.get('parameter_index')})"

def setvol(track, db):
    r = call("/api/track/control", {"track": track, "volume": db})
    return f"vol track{track} = {db}dB" if "__error__" not in r else f"vol ERR {r}"

def setpan(track, pan):
    r = call("/api/track/control", {"track": track, "pan": pan})
    return f"pan track{track} = {pan}"

if __name__ == "__main__":
    idx, proj = tracks()
    print("TRACKS:", json.dumps(idx, ensure_ascii=False))
