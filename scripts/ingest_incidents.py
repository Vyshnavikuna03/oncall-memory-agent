"""Load data/incidents.json into the Hindsight memory bank.

Usage (from the project root, with .venv active):
    python -m scripts.ingest_incidents --dry-run   # preview only
    python -m scripts.ingest_incidents             # really retain

Safe to re-run: retained IDs are tracked in data/.ingested.json and skipped.
"""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from hindsight_client import Hindsight

ROOT = Path(__file__).resolve().parent.parent
INCIDENTS = ROOT / "data" / "incidents.json"
STATE = ROOT / "data" / ".ingested.json"

# Already retained by scripts/hello_hindsight. Remove an ID from this set if
# you want it re-ingested.
ALREADY_LOADED = {"INC-1001", "INC-1007", "INC-1008"}


def to_text(i: dict) -> str:
    failed = "; ".join(i["failed_fixes"]) if i["failed_fixes"] else "none recorded"
    return (
        f"Incident {i['id']} on {i['service']} ({i['severity']}), {i['date']}. "
        f"Alert: {i['alert']}. Root cause: {i['root_cause']}. "
        f"Fixes that failed: {failed}. Fix that worked: {i['fix']}. "
        f"Runbook: {i['runbook']}. Resolved by {i['resolved_by']} "
        f"in {i['minutes_to_resolve']} minutes."
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    incidents = json.loads(INCIDENTS.read_text(encoding="utf-8"))
    done = set(json.loads(STATE.read_text())) if STATE.exists() else set()
    done |= ALREADY_LOADED
    todo = [i for i in incidents if i["id"] not in done]
    print(f"{len(incidents)} incidents in file, {len(todo)} to retain")

    if args.dry_run:
        for i in todo:
            print(" -", i["id"], i["service"], "|", i["alert"])
        return

    client = Hindsight(
        base_url=os.environ["HINDSIGHT_BASE_URL"],
        api_key=os.environ["HINDSIGHT_API_KEY"],
    )
    bank = os.environ["HINDSIGHT_BANK_ID"]

    for i in todo:
        client.retain(
            bank_id=bank,
            content=to_text(i),
            context=f"incident postmortem for {i['service']}",
            timestamp=f"{i['date']}T09:00:00Z",
            document_id=i["id"],
        )
        done.add(i["id"])
        STATE.write_text(json.dumps(sorted(done)))
        print("retained", i["id"])


if __name__ == "__main__":
    main()