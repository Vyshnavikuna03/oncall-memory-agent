"""On-call incident agent: answers an alert with and without Hindsight memory."""
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from hindsight_client import Hindsight

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODELS = ["openai/gpt-oss-120b", "qwen/qwen3-32b"]  # first is preferred, second is fallback
BANK = os.environ["HINDSIGHT_BANK_ID"]

_groq = Groq(api_key=os.environ["GROQ_API_KEY"])


def _client() -> Hindsight:
    """Fresh client per call: avoids 'Event loop is closed' under Streamlit reruns."""
    return Hindsight(
        base_url=os.environ["HINDSIGHT_BASE_URL"],
        api_key=os.environ["HINDSIGHT_API_KEY"],
    )


SYSTEM = (
    "You are an experienced on-call SRE assistant. Given a production alert, "
    "give: 1) Likely root cause, 2) Recommended first steps, 3) What NOT to try. "
    "Be concise and specific. If past incidents are provided, cite them by ID "
    "(e.g. INC-1015) and use both what worked and what failed before. "
    "Never state a root cause as certain unless a recalled incident confirms it; "
    "use 'likely' or 'possibly' and cite the incident IDs you relied on. "
    "If no past incidents are provided, give general best-practice advice only."
)


def recall_memories(alert: str, limit: int = 8) -> list[str]:
    """Ask Hindsight for past incidents relevant to this alert."""
    try:
        res = _client().recall(bank_id=BANK, query=alert)
        items = getattr(res, "results", res)
        texts = [getattr(r, "text", None) or str(r) for r in items]
        return texts[:limit]
    except Exception as e:
        print(f"Hindsight recall failed: {e}")
        return []


def _ask_llm(user_msg: str) -> str:
    last_err = None
    for model in MODELS:
        for attempt in range(2):  # retry once, then fall back to the next model
            try:
                out = _groq.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.2,
                )
                return out.choices[0].message.content
            except Exception as e:  # rate limits, model errors, etc.
                last_err = e
                time.sleep(1.5)
    return f"[LLM error: {last_err}]"


def answer(alert: str, use_memory: bool) -> dict:
    memories = recall_memories(alert) if use_memory else []
    if memories:
        context = "\n".join(f"- {m}" for m in memories)
        msg = f"ALERT: {alert}\n\nPAST INCIDENTS FROM TEAM MEMORY:\n{context}"
    else:
        msg = f"ALERT: {alert}"
    return {"answer": _ask_llm(msg), "memories": memories}


def learn(incident_id: str, service: str, alert: str, root_cause: str,
          failed: str, fix: str) -> None:
    """Retain a newly resolved incident so future alerts benefit."""
    text = (
        f"Incident {incident_id} on {service}. Alert: {alert}. "
        f"Root cause: {root_cause}. Fixes that failed: {failed}. "
        f"Fix that worked: {fix}."
    )
    _client().retain(bank_id=BANK, content=text,
                     context=f"incident postmortem for {service}",
                     document_id=incident_id)