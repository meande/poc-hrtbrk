import os
import streamlit as st
from openai import OpenAI
from prompt_templates import SYSTEM_PROMPT
from safety import is_safe

# --- Config -------------------------------------------------------
assistant_id = os.getenv("ASSISTANT_ID")
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    st.error("OPENAI_API_KEY environment variable not set.")
    st.stop()

client = OpenAI(api_key=openai_api_key)

st.set_page_config(page_title="Heartbreak POC", page_icon=":broken_heart:")
st.title("💔 Heal Your Broken Heart – Demo")

# -----------------------------------------------------------
def create_new_thread():
    thread = openai.beta.threads.create()
    return thread.id

def get_assistant_reply(thread_id):
    """
    Post the conversation (messages already added) and return the assistant's next reply
    """
    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        timeout=30,
    )
    # Poll until complete (simple loop for demo)
    while run.status not in ("completed", "failed"):
        run = openai.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run.id
        )
    if run.status == "failed":
        return "Sorry, something went wrong. Let's try again."
    msgs = openai.beta.threads.messages.list(thread_id=thread_id)
    # The last message is the assistant's
    return msgs.data[0].content[0].text.value
# -----------------------------------------------------------

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

            # create a new thread & store it
            st.session_state.thread_id = create_new_thread()
            # Add the user's intake answers to the thread so the assistant sees them
            openai.beta.threads.messages.create(
                thread_id=st.session_state.thread_id,
                role="user",
                content=f"I\'m dealing with a {event_type}. What hurts most is: {key_fact}."
            )
            # Get assistant's proactive first reply
            first_reply = get_assistant_reply(st.session_state.thread_id)
            st.session_state.messages = [
                {"role": "assistant", "content": first_reply}
            ]

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
        openai.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=user_input
        )
        with st.spinner("HeartBuddy typing…"):
            assistant_message = get_assistant_reply(st.session_state.thread_id)
        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_message}
        )

        # Auto‑scroll to newest message
        st.rerun()
