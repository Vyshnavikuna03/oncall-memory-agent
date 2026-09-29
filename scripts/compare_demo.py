"""Run the same alert with memory OFF and ON.

    python -m scripts.compare_demo
    python -m scripts.compare_demo "your own alert text"
"""
import sys

from agent.oncall_agent import answer

ALERT = (
    sys.argv[1] if len(sys.argv) > 1
    else "payments-api latency spiking after deploy v2.15.0, Redis connection errors"
)

print("ALERT:", ALERT)
print("\n" + "=" * 70 + "\nWITHOUT MEMORY\n" + "=" * 70)
print(answer(ALERT, use_memory=False)["answer"])

print("\n" + "=" * 70 + "\nWITH HINDSIGHT MEMORY\n" + "=" * 70)
r = answer(ALERT, use_memory=True)
print(r["answer"])
print("\nRecalled", len(r["memories"]), "memories:")
for m in r["memories"]:
    print(" -", m[:110])