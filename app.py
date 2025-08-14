import json
import base64
import streamlit as st
import streamlit.components.v1 as components

from rag_pipeline import generate_response
from user_memory import get_chat_history, save_to_history, get_sessions, load_session

# --- Global Page Config ---
st.set_page_config(page_title="Regis", page_icon="🛡️", layout="wide")

# --- Init Session State ---
default_state = {
    "show_homepage": True,
    "show_settings": False,
    "chat_history": [],
    "session_name": "default",
    "language": "English",
    "role": "General Worker",
    "markdown_mode": True,
    "prefill": "",
    "feedback": []
}
for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------------------
# Helpers: follow-up actions
# ---------------------------
def suggest_followups(role: str):
    """Return a small set of role-aware follow-up actions."""
    return [
        {
            "label": "Make a step-by-step checklist",
            "prompt": f"Convert the guidance above into a concise, role-specific checklist for a {role}. Use numbered steps and cite WorkSafe sections."
        },
        {
            "label": "Draft a 5-min toolbox talk",
            "prompt": f"Write a 5-minute toolbox talk script for a {role} based on the guidance above, with 3 questions to ask the crew."
        },
        {
            "label": "Create a JSA template",
            "prompt": "Generate a Job Safety Analysis table: Task | Hazard | Risk | Controls | Person Responsible. Base it on the guidance above."
        },
    ]


def render_followups(latest_user_q: str, latest_answer: str, role: str, idx_key: int):
    """Render CTA buttons that immediately continue the chat when clicked."""
    st.markdown("**Do you want me to…**")
    actions = suggest_followups(role)
    cols = st.columns(len(actions))
    for i, act in enumerate(actions):
        if cols[i].button(act["label"], key=f"cta_{idx_key}_{i}"):
            # Treat as a new user question and generate immediately
            new_q = act["prompt"]
            resp, src, sp, ep, ts = generate_response(new_q)
            source_info = f"{src} (pp. {sp}–{ep})"
            formatted = (
                f"{resp}\n\n**Source:** `{source_info}`\n*Timestamp:* {ts}"
                if st.session_state.markdown_mode
                else f"{resp}\n\nSource: {source_info} | Timestamp: {ts}"
            )
            # Append the Q/A so the conversation continues
            st.session_state.chat_history.append({"question": new_q, "answer": formatted})
            save_to_history(new_q, resp, source_info, f"{sp}–{ep}", ts,
                            session_name=st.session_state.session_name)
            st.rerun()


# --- Homepage View ---
def show_homepage():
    try:
        with open("regis_logo.png", "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
        col1, col2, col3 = st.columns([1, 2.5, 1])
        with col2:
            st.markdown(
                f"""
                <div style='text-align: center; margin-top: 20px;'>
                    <img src='data:image/png;base64,{encoded}' style='max-width: 100%; width: 20vw; height: auto;' />
                </div>
                """,
                unsafe_allow_html=True,
            )
    except Exception as e:
        st.warning(f"⚠️ Logo could not be loaded: {e}")

    st.markdown(
        """
        <div style="display: flex; justify-content: center; gap: 40px; margin-top: 60px; flex-wrap: wrap; font-size: 18px;">
            <div>📚 Based on NZ health & safety law</div>
            <div>🧠 AI-powered answers</div>
            <div>👷 Role-specific insights</div>
            <div>📄 Understands official guidelines</div>
            <div>🕒 Trusted. Timestamped. Traceable.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🚀 Start Chat", use_container_width=True):
        st.session_state.show_homepage = False
        st.session_state.prefill = ""
        st.rerun()


# --- Settings View ---
def show_settings_page():
    st.title("⚙️ Settings")
    st.selectbox("🌐 Language", ["English", "Te Reo Māori", "Tongan", "Samoan"], key="language")
    st.selectbox("👷 Your Job Role", ["General Worker", "Electrician", "Nurse", "Forklift Operator"], key="role")
    st.checkbox("📝 Enable Markdown Formatting", key="markdown_mode")
    st.text_input("💾 Default Session Name", value=st.session_state.session_name, key="session_name")

    st.markdown("---")
    if st.button("✅ Save & Return to Chat"):
        st.session_state.show_settings = False
        st.rerun()
    if st.button("🏠 Return to Homepage"):
        st.session_state.show_settings = False
        st.session_state.show_homepage = True
        st.rerun()


# --- Chat Interface View ---
def run_chat_interface():
    st.title("💬 Ask Regis — Your Health & Safety Assistant")

    # Sidebar
    with st.sidebar:
        if st.button("🏠 Return to Homepage"):
            st.session_state.show_homepage = True
            st.rerun()
        if st.button("⚙️ Open Settings Page"):
            st.session_state.show_settings = True
            st.rerun()

        st.markdown("---")
        st.markdown("## 💾 Session")
        st.text_input("Session Name", value=st.session_state.session_name, key="session_name")
        if st.button("💾 Save Session"):
            save_to_history(None, None, None, None, None, session_name=st.session_state.session_name)
            st.success(f"Session '{st.session_state.session_name}' saved.")
        if st.button("🧹 Clear Chat"):
            st.session_state.chat_history = []

        st.markdown("---")
        st.markdown("## 🕓 Previous Sessions")
        sessions = get_sessions()
        selected = st.selectbox("📂 Load Session", sessions, index=0 if sessions else None)
        if st.button("📥 Load Selected"):
            st.session_state.chat_history = load_session(selected)

    # Chat Input
    user_input = st.chat_input(
        placeholder=st.session_state.prefill or "Ask your health & safety question here…",
        key="chat_input",
    )

    # If the user asked something, answer it
    if user_input:
        st.session_state.prefill = ""
        with st.spinner("Analyzing your question…"):
            resp, src, sp, ep, ts = generate_response(user_input)
            source_info = (
                "Unknown" if not src or src == "Unknown"
                else (f"{src} (pp. {sp}–{ep})" if sp != "N/A" and ep != "N/A" else src)
            )
            formatted = (
                f"{resp}\n\n**Source:** `{source_info}`\n*Timestamp:* {ts}"
                if st.session_state.markdown_mode
                else f"{resp}\n\nSource: {source_info} | Timestamp: {ts}"
            )

            st.session_state.chat_history.append({"question": user_input, "answer": formatted})
            save_to_history(user_input, resp, source_info, f"{sp}–{ep}", ts,
                            session_name=st.session_state.session_name)

    # Display Chat History
    for idx, entry in enumerate(st.session_state.chat_history):
        with st.chat_message("user"):
            st.markdown(entry["question"])
        with st.chat_message("assistant"):
            if st.session_state.markdown_mode:
                st.markdown(entry["answer"])
            else:
                st.text(entry["answer"])

            # Actions under each assistant message
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            if col1.button("📋 Copy", key=f"copy_{idx}"):
                escaped = json.dumps(entry["answer"])
                components.html(
                    f"<script>navigator.clipboard.writeText({escaped});</script>",
                    height=0,
                )
                col1.success("Copied!")

            if col2.button("🔄 Regenerate", key=f"regen_{idx}"):
                q = entry["question"]
                r2, s2, sp2, ep2, t2 = generate_response(q)
                src2 = "Unknown" if not s2 or s2 == "Unknown" else (f"{s2} (pp. {sp2}–{ep2})" if sp2 != "N/A" and ep2 != "N/A" else s2)
                new_fmt = (
                    f"{r2}\n\n**Source:** `{src2}`\n*Timestamp:* {t2}"
                    if st.session_state.markdown_mode
                    else f"{r2}\n\nSource: {src2} | Timestamp: {t2}"
                )
                st.session_state.chat_history.append({"question": q, "answer": new_fmt})
                st.rerun()

            if col3.button("👍", key=f"like_{idx}"):
                st.session_state.feedback.append((idx, True))
                col3.success("Thanks!")
            if col4.button("👎", key=f"dislike_{idx}"):
                st.session_state.feedback.append((idx, False))
                col4.warning("Got it!")

            # Show follow-ups only under the latest assistant message
            if idx == len(st.session_state.chat_history) - 1:
                render_followups(
                    latest_user_q=entry["question"],
                    latest_answer=entry["answer"],
                    role=st.session_state.get("role", "General Worker"),
                    idx_key=idx
                )


# --- Routing ---
if st.session_state.show_homepage:
    show_homepage()
elif st.session_state.show_settings:
    show_settings_page()
else:
    run_chat_interface()
