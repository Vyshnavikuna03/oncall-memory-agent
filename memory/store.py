"""
Memory layer for the Incident Response Agent, built on Hindsight.

Design idea: we don't just store raw chat. We store
  1) incident narratives (symptoms -> root cause -> fix), and
  2) OUTCOMES (did the fix work?) as separate memories.
That outcome signal is what lets the agent learn which fixes to trust.
"""
import os
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()


def _make_client() -> Hindsight:
    base_url = os.getenv("HINDSIGHT_BASE_URL", "http://localhost:8888")
    api_key = os.getenv("HINDSIGHT_API_KEY")
    if api_key:
        # Hindsight Cloud needs auth. Verify the exact parameter name in the
        # docs (hindsight.vectorize.io) if this raises a TypeError.
        return Hindsight(base_url=base_url, api_key=api_key)
    return Hindsight(base_url=base_url)


class IncidentMemory:
    def __init__(self, bank_id: str | None = None):
        self.client = _make_client()
        self.bank_id = bank_id or os.getenv("HINDSIGHT_BANK_ID", "oncall-team-demo")

    # ---------- write ----------
    def retain_incident(self, inc: dict) -> None:
        """Store one incident as a readable narrative."""
        text = (
            f"Incident {inc['id']} on {inc['service']} ({inc['severity']}). "
            f"Symptoms: {inc['symptoms']}. "
            f"Logs: {inc.get('logs', 'n/a')}. "
            f"Root cause: {inc['root_cause']}. "
            f"Fix applied: {inc['fix_applied']}. "
            f"Outcome: the fix {inc['outcome'].upper()}"
            f" (resolved in {inc.get('time_to_resolve_minutes', '?')} minutes)."
        )
        self.client.retain(
            bank_id=self.bank_id,
            content=text,
            context=f"incident postmortem for {inc['service']}",
            timestamp=inc["timestamp"],
        )

    def retain_feedback(self, incident_id: str, service: str, suggested_fix: str, worked: bool) -> None:
        """The learning signal: engineer says whether the agent's suggestion worked."""
        verdict = "WORKED" if worked else "DID NOT WORK"
        self.client.retain(
            bank_id=self.bank_id,
            content=(
                f"Feedback on {incident_id} ({service}): the suggested fix "
                f"'{suggested_fix}' {verdict}."
            ),
            context="engineer feedback on agent suggestion",
        )

    # ---------- read ----------
    def recall_similar(self, alert_text: str) -> list[str]:
        """Return memory snippets relevant to a new alert."""
        res = self.client.recall(bank_id=self.bank_id, query=alert_text)
        return [r.text for r in res.results]

    def reflect_patterns(self, question: str) -> str:
        """Higher-level insight, e.g. 'which services have recurring problems?'"""
        res = self.client.reflect(bank_id=self.bank_id, query=question)
        return res.text