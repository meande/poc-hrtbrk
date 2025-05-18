import os
import streamlit as st
from openai import OpenAI
from prompt_templates import SYSTEM_PROMPT
from safety import is_safe

# --- Config -------------------------------------------------------
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("OPENAI_API_KEY environment variable not set.")
    st.stop()

client = OpenAI(api_key=openai_api_key)

st.set_page_config(page_title="Heartbreak POC", page_icon=":broken_heart:")
st.title("💔 Heal Your Broken Heart – Demo")

# --- Intake form --------------------------------------------------
if "intake_complete" not in st.session_state:
    st.session_state.intake_complete = False
if "event_type" not in st.session_state:
    st.session_state.event_type = ""
if "key_fact" not in st.session_state:
    st.session_state.key_fact = ""

if not st.session_state.intake_complete:
    with st.form("intake"):
        st.subheader("Tell us a bit about your situation")
        event_type = st.selectbox(
            "What happened?",
            ("Select...", "Break‑up", "Bereavement")
        )
        key_fact = st.text_input(
            "In one sentence, what still hurts most?"
        )
        submitted = st.form_submit_button("Start Chat")
        if submitted and event_type != "Select..." and key_fact:
            st.session_state.event_type = event_type
            st.session_state.key_fact = key_fact
            st.session_state.intake_complete = True
            st.rerun()
    st.stop()

# --- Chat memory --------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(
                event=st.session_state.event_type,
                fact=st.session_state.key_fact
            ),
        }
    ]

# Display existing conversation
for m in st.session_state.messages[1:]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- Chat input loop ----------------------------------------------
user_input = st.chat_input("Write something...")

if user_input:
    # Safety check user input
    if not is_safe(user_input):
        with st.chat_message("assistant"):
            st.error("Sorry, let's keep this conversation safe for everyone.")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.spinner("Coach is thinking…"):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
                temperature=0.7,
                max_tokens=300,
                timeout=30
            )
            assistant_message = response.choices[0].message.content
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_message}
            )

        with st.chat_message("assistant"):
            st.markdown(assistant_message)

        # Auto‑scroll to newest message
        st.rerun()
