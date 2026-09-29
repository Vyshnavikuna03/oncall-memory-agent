# 🚨 On-Call Memory Agent

**An incident-response agent that remembers every outage your team has ever fixed, and gets smarter with each one.**

Built for **Hack with Hyderabad 3.0** ("AI Agents That Learn Using Hindsight") with [Hindsight](https://hindsight.vectorize.io/) as the memory layer.

- 🎥 Demo video: `ADD LINK`
- 🌐 Live demo: `ADD LINK (or "runs locally, see Quick start")`
- 👥 Team: `ADD NAMES`

---

## The problem

It's 2 AM. `payments-api` latency is spiking after a deploy. Somebody on your team fixed almost exactly this problem two months ago, but the fix lives in a old Slack thread, a half-written postmortem, or one engineer's head.

A normal LLM assistant gives generic advice ("check the diff, inspect Redis metrics, maybe raise the pool size"). Worse, it will happily suggest fixes your team **already tried and that failed**.

## The solution

On-Call Memory Agent answers the same alert two ways, side by side:

| Without memory | With Hindsight memory |
|---|---|
| Generic best-practice checklist | Cites your past incidents by ID (e.g. INC-1015, INC-1021) |
| May suggest fixes that already failed | Warns what **not** to try because it failed before |
| Same answer every time | Improves every time an incident is resolved |

When an incident is resolved, the engineer records it in the **Teach the agent** form. The next similar alert benefits immediately.

---

## How Hindsight memory is used

Memory is the core of this project, not an add-on. The agent uses three Hindsight operations:

**1. Retain: building the incident history**
Each past incident (root cause, fixes that failed, fix that worked, service, version) is stored in a Hindsight memory bank with `retain`, using the incident ID as the `document_id` so each incident is tracked as one document. `scripts/ingest_incidents.py` loads the 20-incident starting history from `data/incidents.json`.

**2. Recall: answering a new alert**
When an alert comes in, the agent calls `recall` with the alert text. Hindsight returns the most relevant memories (past incidents, their causes, and what failed). Those are added to the LLM prompt as "PAST INCIDENTS FROM TEAM MEMORY", and the model is instructed to cite incident IDs and to use both what worked and what failed.

**3. The learning loop: getting smarter over time**
The **Teach the agent** form calls `retain` again with the newly resolved incident. Re-running the same alert then recalls the new incident and changes the answer.

```
 New alert ──► Hindsight recall ──► relevant past incidents
                                          │
                                          ▼
                      Groq LLM (alert + recalled incidents) ──► answer
                                                                   │
 Incident resolved ──► Teach the agent form ──► Hindsight retain ◄─┘
                              (memory grows, next answer improves)
```

### Before / after example

Alert: `payments-api latency spiking after deploy v2.15.0, Redis connection errors`

- **Without memory:** a long generic checklist, including "increase Redis timeouts/retries".
- **With memory:** identifies a likely connection leak, cites INC-1015 (same pattern in v2.14.3) and INC-1001, warns that raising `max_connections` failed to fix a previous incident, and recommends rolling back to the last known-good version.
- **After teaching it INC-1021** (a v2.15.0 leak resolved by rollback to v2.14.4): the same alert now cites INC-1021 directly.

`ADD SCREENSHOTS HERE (before, after, recalled memories list)`

---

## Features

- Side-by-side comparison: same alert, with and without memory
- Recalled-memories panel so users can see **why** the agent answered as it did
- One-click sample alerts for a fast demo
- "Teach the agent" learning loop that retains new incidents
- Grounded answers: the model is told not to state a root cause as certain unless a recalled incident confirms it

### Reliability and edge cases

- **LLM failures:** each request retries once, then falls back from `openai/gpt-oss-120b` to `qwen/qwen3-32b`, and returns a readable error message if both fail
- **Hindsight failures:** if recall fails, the agent falls back to general advice instead of crashing
- **UI errors:** analysis and save actions show friendly error messages instead of stack traces
- **Empty recall:** the UI tells the user when no past incidents matched
- **Streamlit reruns:** a fresh Hindsight client is created per call to avoid closed-event-loop errors

---

## Tech stack

- **Memory:** [Hindsight](https://hindsight.vectorize.io/) (Vectorize), via `hindsight-client`
- **LLM:** Groq, using `openai/gpt-oss-120b` with `qwen/qwen3-32b` as fallback
- **UI:** Streamlit
- **Language:** Python 3.12

---

## Project structure

```
incident-agent/
├── app.py                     # Streamlit UI (side-by-side answers + learning form)
├── agent/
│   └── oncall_agent.py        # recall, LLM calls, and learn (retain)
├── memory/                    # Hindsight helper module
├── scripts/
│   ├── ingest_incidents.py    # load the incident history into Hindsight
│   ├── compare_demo.py        # terminal before/after demo
│   └── hello_hindsight.py     # connection smoke test
├── data/
│   ├── incidents.json         # 20 synthetic incidents (INC-1001 to INC-1020)
│   ├── sample_incidents.json
│   └── schema.json
├── requirements.txt
└── .env.example
```

---

## Quick start

**1. Clone and install**

```bash
git clone https://github.com/YOUR-USERNAME/oncall-memory-agent.git
cd oncall-memory-agent
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

**2. Configure keys**

Copy `.env.example` to `.env` and fill in your values:

```
GROQ_API_KEY=your_groq_key_here
HINDSIGHT_API_KEY=your_hindsight_key_here
HINDSIGHT_BASE_URL=your_hindsight_base_url_here
HINDSIGHT_BANK_ID=your_bank_id_here
```

You need a Hindsight instance ([Hindsight Cloud](https://ui.hindsight.vectorize.io) or the open-source version) and a [Groq](https://groq.com/) API key.

**3. Load the incident history (once)**

```bash
python -m scripts.ingest_incidents
```

Hindsight processes memories in the background, so give it a minute before your first alert.

**4. (Optional) Terminal demo**

```bash
python -m scripts.compare_demo
```

**5. Run the app**

```bash
streamlit run app.py
```

Open http://localhost:8501.

---

## Demo walkthrough (about 60 seconds)

1. Click a sample alert such as **Payments: Redis errors after deploy**, then **Analyze alert**.
2. Compare the generic answer (left) with the memory-powered answer (right) and open the recalled memories.
3. Pick a second alert (for example **Auth: random logouts**) and analyze it. The history has nothing directly relevant, so the answer stays general.
4. In **Teach the agent**, record the resolved incident (ID, service, root cause, failed fixes, fix that worked) and click **Save to memory**.
5. Wait a minute, then analyze the same alert again. The answer now cites the new incident.

---

## Real-world impact

On-call engineers lose time re-debugging problems their team has already solved, and institutional knowledge leaves when people do. An agent that remembers root causes, failed fixes and what finally worked can shorten time-to-resolution and reduce repeat incidents.

**Path to adoption:** ingest postmortems from existing tools, trigger analysis directly from PagerDuty or Opsgenie alerts, post answers in Slack, and capture new incidents automatically when a ticket is closed.

## Limitations

- The starting incident history is synthetic, generated to look realistic.
- Recall quality depends on how completely incidents are described when retained.
- Hindsight processes new memories asynchronously, so a just-saved incident can take a minute or two to appear.
- Answers are suggestions for a human on-call engineer, not automated remediation.

---

## Acknowledgements

Built with [Hindsight](https://github.com/vectorize-io/hindsight) by Vectorize for Hack with Hyderabad 3.0.