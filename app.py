# app.py  – Heartbreak POC (Assistants API)

import os
import streamlit as st
import openai
from safety import is_safe   # make sure safety.py is in repo root

# --- NEW: force Assistants v2 -------------------------------------
os.environ["OPENAI_BETA_ASSISTANTS_VERSION"] = "v2"

# ── Config ───────────────────────────────────────────────────────────
openai.api_key = os.getenv("OPENAI_API_KEY")
assistant_id   = os.getenv("ASSISTANT_ID")

if not openai.api_key or not assistant_id:
    st.error("OPENAI_API_KEY or ASSISTANT_ID missing in secrets.")
    st.stop()

st.set_page_config(page_title="Heartbreak POC", page_icon=":broken_heart:")
st.title("💔 Heal Your Broken Heart – Demo")

# ── Helper functions ────────────────────────────────────────────────
def create_new_thread() -> str:
    """Create a fresh thread for a new user session."""
    thread = openai.beta.threads.create()
    return thread.id

def get_assistant_reply(thread_id: str) -> str:
    """Submit the conversation and return HeartBuddy's latest reply."""
    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        timeout=30,
    )
    # Simple polling loop (fine for demo)
    while run.status not in ("completed", "failed"):
        run = openai.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run.id
        )

    if run.status == "failed":
        return "Sorry, something went wrong. Let's try again."
    
    msgs = openai.beta.threads.messages.list(thread_id=thread_id)
    # Assistant’s message is first in the returned list
    return msgs.data[0].content[0].text.value

# ── Intake form ─────────────────────────────────────────────────────
if "intake_complete" not in st.session_state:
    st.session_state.intake_complete = False

if not st.session_state.intake_complete:
    with st.form("intake"):
        st.subheader("Tell us a bit about your situation")
        event_type = st.selectbox(
            "What happened?",
            ("Select...", "Break-up", "Bereavement")
        )
        key_fact = st.text_input(
            "In one sentence, what still hurts most?"
        )
        submitted = st.form_submit_button("Start Chat")
        if submitted and event_type != "Select..." and key_fact:
            # Save user context
            st.session_state.event_type = event_type
            st.session_state.key_fact   = key_fact
            st.session_state.intake_complete = True

            # Create thread & store ID
            st.session_state.thread_id = create_new_thread()

            # Prime the thread with user’s first message
            openai.beta.threads.messages.create(
                thread_id=st.session_state.thread_id,
                role="user",
                content=f"I'm dealing with a {event_type}. "
                        f"What hurts most is: {key_fact}."
            )

            # Assistant proactive greeting
            first_reply = get_assistant_reply(st.session_state.thread_id)
            st.session_state.messages = [
                {"role": "assistant", "content": first_reply}
            ]
            st.rerun()
    st.stop()

# ── Initialise in-memory chat history after intake ─────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display existing conversation
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ── Chat input loop ────────────────────────────────────────────────
user_input = st.chat_input("Write something…")

if user_input:
    # Safety check
    if not is_safe(user_input):
        with st.chat_message("assistant"):
            st.error("Let's keep the conversation safe for everyone.")
    else:
        # Add user message locally and to assistant thread
        st.session_state.messages.append({"role": "user", "content": user_input})
        openai.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=user_input,
        )

        with st.spinner("HeartBuddy typing…"):
            assistant_message = get_assistant_reply(st.session_state.thread_id)

        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_message}
        )

        st.rerun()  # refresh UI to show new messages
