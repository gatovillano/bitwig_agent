#!/usr/bin/env python3
"""Cliente del bridge Bitwig con resolucion robusta de paginas de controles remotos."""
import json, urllib.request, urllib.error, re, time

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
        try:
            return {"__error__": json.loads(e.read().decode()).get("error", str(e))}
        except Exception:
            return {"__error__": str(e)}
    except Exception as e:
        return {"__error__": str(e)}

def track_list():
    return call("/api/project")["tracks"]

def find(name):
    for t in track_list():
        if t["name"] == name:
            return t["index"]
    return None

def inspect(track):
    return call("/api/track/inspect", {"track": track})

def device_list(track):
    return [(x["index"], x["name"], x.get("pages", [])) for x in inspect(track).get("devices", [])]

def _avail(err):
    """Parsea la lista de parametros disponibles del mensaje de error."""
    m = re.search(r"Available parameters on current page: \[(.*?)\]", err or "", re.S)
    if not m:
        return []
    return re.findall(r"\[?\d+\]?\s*([^,\]]+)", m.group(1))

def probe(track, device, page):
    r = call("/api/device/parameter",
             {"track": track, "device": device, "parameter": "__probe__",
              "value": 0.0, "page": page})
    return _avail(r.get("__error__", ""))

def set_param(track, device, param, value, pages=None, tries=2):
    """Sondea paginas hasta encontrar el parametro y lo escribe."""
    pages = pages or []
    tried = set()
    for attempt in range(tries):
        candidates = list(pages) if attempt == 0 else [p for p in pages if p not in tried]
        for pg in candidates:
            tried.add(pg)
            avail = probe(track, device, pg)
            names = [a.strip() for a in avail]
            if any(n.lower() == param.lower() for n in names):
                r = call("/api/device/parameter",
                         {"track": track, "device": device, "parameter": param,
                          "value": value, "page": pg})
                if "__error__" not in r:
                    return True, pg
    # sin page
    r = call("/api/device/parameter",
             {"track": track, "device": device, "parameter": param, "value": value})
    if "__error__" not in r:
        return True, None
    return False, r.get("__error__", "")[:160]

def set_vol(track, db):
    return call("/api/track/control", {"track": track, "volume": db})

def set_pan(track, pan):
    return call("/api/track/control", {"track": track, "pan": pan})
