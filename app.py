"""Streamlit UI for the On-Call Memory Agent.  Run:  streamlit run app.py"""
import asyncio

import streamlit as st

# Streamlit runs scripts in a worker thread that may have no asyncio loop,
# and the Hindsight client needs one.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from agent.oncall_agent import answer, learn  # noqa: E402

st.set_page_config(page_title="On-Call Memory Agent", page_icon="🚨", layout="wide")
st.title("🚨 On-Call Memory Agent")
st.caption("Same alert, two answers: one without memory, one powered by Hindsight.")

SAMPLES = {
    "Payments: Redis errors after deploy": "payments-api latency spiking after deploy v2.15.0, Redis connection errors",
    "Auth: random logouts": "auth-service users randomly logged out, spike in 401 responses",
    "DB: connections maxed": "db-primary application errors 'too many clients', connection count at max",
    "Search: empty results": "search-service returning empty results for all queries",
}

with st.sidebar:
    st.header("Sample alerts")
    for label, text in SAMPLES.items():
        if st.button(label, use_container_width=True):
            st.session_state["alert"] = text
    st.divider()
    st.caption("Memory bank: incident history retained in Hindsight.")

alert = st.text_area("Incoming alert", key="alert", height=80,
                     placeholder="e.g. payments-api latency spiking, Redis errors")

if st.button("Analyze alert", type="primary", disabled=not alert.strip()):
    with st.spinner("Asking the agent without memory, then with Hindsight..."):
        try:
            st.session_state["plain"] = answer(alert, use_memory=False)
            st.session_state["mem"] = answer(alert, use_memory=True)
        except Exception as e:
            st.session_state.pop("plain", None)
            st.session_state.pop("mem", None)
            st.error("Something went wrong while analyzing the alert. Please try again.")
            st.caption(str(e))

if "mem" in st.session_state and "plain" in st.session_state:
    left, right = st.columns(2)
    with left:
        st.subheader("Without memory")
        st.markdown(st.session_state["plain"]["answer"])
    with right:
        st.subheader("With Hindsight memory")
        st.markdown(st.session_state["mem"]["answer"])

    mems = st.session_state["mem"]["memories"]
    if not mems:
        st.info("No past incidents were recalled for this alert, so the "
                "memory answer is general advice. Teach the agent below.")
    with st.expander(f"🧠 Recalled {len(mems)} memories from Hindsight", expanded=True):
        for m in mems:
            st.markdown(f"- {m}")

    st.divider()
    st.subheader("Incident resolved? Teach the agent")
    with st.form("learn_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        inc_id = c1.text_input("Incident ID", placeholder="e.g. INC-1022")
        service = c2.text_input("Service", placeholder="e.g. auth-service")
        root = st.text_input("Root cause")
        failed = st.text_input("Fixes that failed", value="none")
        fix = st.text_input("Fix that worked")
        if st.form_submit_button("Save to memory"):
            if inc_id.strip() and service.strip() and root.strip() and fix.strip():
                try:
                    learn(inc_id.strip(), service.strip(), alert,
                          root.strip(), failed.strip() or "none", fix.strip())
                    st.success(f"{inc_id} retained. Hindsight may take a minute to "
                               "process it; then re-run the same alert to see it recalled.")
                except Exception as e:
                    st.error("Could not save the incident. Please try again.")
                    st.caption(str(e))
            else:
                st.warning("Fill in the incident ID, service, root cause and fix.")