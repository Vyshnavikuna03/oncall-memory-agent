"""Smoke test: retain a few incidents, then recall for a NEW alert.
Run from the project root:  python -m scripts.hello_hindsight
"""
import json
from memory.store import IncidentMemory

mem = IncidentMemory()

with open("data/sample_incidents.json") as f:
    incidents = json.load(f)

for inc in incidents:
    mem.retain_incident(inc)
    print(f"retained {inc['id']}")

# A brand new alert that should remind us of INC-1001
alert = "payments-api latency spiking, logs show redis connection errors"
print("\nNEW ALERT:", alert)
print("\nRECALLED MEMORIES:")
for m in mem.recall_similar(alert):
    print(" -", m)

print("\nREFLECTION:")
print(mem.reflect_patterns("Which services have recurring problems and what fixes failed before?"))