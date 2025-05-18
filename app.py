# app.py  – HeartBuddy demo (Assistants API v2)

import os
import streamlit as st
import openai
from safety import is_safe   # safety.py must be in repo root

# ── OpenAI client with v2 header ────────────────────────────────────
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    default_headers={"OpenAI-Beta": "assistants=v2"},
)

assistant_id = os.getenv("ASSISTANT_ID")   # must be a *v2* assistant ID
if not assistant_id:
    st.error("Missing ASSISTANT_ID (v2) in secrets.")
    st.stop()

st.set_page_config(page_title="Heartbreak POC", page_icon=":broken_heart:")
st.title("💔 Heal Your Broken Heart – Demo")

# ── Helper functions ───────────────────────────────────────────────
def create_new_thread() -> str:
    thread = client.beta.threads.create()
    return thread.id

def get_assistant_reply(thread_id: str) -> str:
    """Run assistant and return its newest reply."""
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    while run.status not in ("completed", "failed"):
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run.id
        )
    if run.status == "failed":
        return "Sorry, something went wrong. Let's try again."
    msgs = client.beta.threads.messages.list(thread_id=thread_id)
    return msgs.data[0].content[0].text.value

# ── Intake form ────────────────────────────────────────────────────
if "intake_complete" not in st.session_state:
    st.session_state.intake_complete = False

if not st.session_state.intake_complete:
    with st.form("intake"):
        st.subheader("Tell us a bit about your situation")
        event_type = st.selectbox(
            "What happened?", ("Select...", "Break-up", "Bereavement")
        )
        key_fact = st.text_input("In one sentence, what still hurts most?")
        submitted = st.form_submit_button("Start Chat")

        if submitted and event_type != "Select..." and key_fact:
            # persist user context
            st.session_state.event_type = event_type
            st.session_state.key_fact = key_fact
            st.session_state.intake_complete = True

            # New thread for this session
            st.session_state.thread_id = create_new_thread()

            # Prime thread with user’s first message
            client.beta.threads.messages.create(
                thread_id=st.session_state.thread_id,
                role="user",
                content=f"I'm dealing with a {event_type}. "
                        f"What hurts most is: {key_fact}.",
            )

            # Assistant proactive greeting
            first_reply = get_assistant_reply(st.session_state.thread_id)
            st.session_state.messages = [
                {"role": "assistant", "content": first_reply}
            ]
            st.rerun()
    st.stop()

# ── Chat history init ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat so far
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat loop ──────────────────────────────────────────────────────
user_input = st.chat_input("Write something…")

if user_input:
    if not is_safe(user_input):
        with st.chat_message("assistant"):
            st.error("Let's keep the conversation safe for everyone.")
    else:
        # 1 · store in history (for next rerun)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # 2 · ⚡ show it right away
        with st.chat_message("user"):
            st.markdown(user_input)

        # 3 · push to the thread
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=user_input,
        )

        # 4 · spinner + assistant reply
        with st.spinner("HeartBuddy typing…"):
            assistant_message = get_assistant_reply(st.session_state.thread_id)

        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_message}
        )
        
        st.rerun()
