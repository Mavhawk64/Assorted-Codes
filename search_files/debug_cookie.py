import json

STATE_PATH = "storage_state.json"

with open(STATE_PATH, "r", encoding="utf-8") as f:
    state = json.load(f)

matches = [
    c
    for c in state.get("cookies", [])
    if c.get("name", "").startswith("QueueITAccepted")
]

print("Found QueueITAccepted cookies:", len(matches))
for c in matches[:5]:
    print("name=", c.get("name"))
    print("domain=", c.get("domain"))
    print("path=", c.get("path"))
    print("secure=", c.get("secure"))
    print("expires=", c.get("expires"))
    print("---")
