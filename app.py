import json
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

# --- Homepage View ---
def show_homepage():
    try:
        st.markdown(
            """
            <div style='display: flex; justify-content: center; align-items: center; margin-top: 60px;'>
                <img src='assets/regis_logo.png' width='200'/>
            </div>
            """,
            unsafe_allow_html=True
        )
    except:
        st.warning("⚠️ Logo could not be loaded.")

    # Horizontal benefits list
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
        unsafe_allow_html=True
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
        selected = st.selectbox("📂 Load Session", sessions)
        if st.button("📥 Load Selected"):
            st.session_state.chat_history = load_session(selected)

    # Chat Input
    user_input = st.chat_input(
        placeholder=st.session_state.prefill or "Ask your health & safety question here…",
        key="chat_input"
    )

    if user_input:
        st.session_state.prefill = ""
        with st.spinner("Analyzing your question…"):
            resp, src, sp, ep, ts = generate_response(user_input)
            source_info = f"{src} (pp. {sp}–{ep})"
            formatted = (
                f"{resp}\n\n**Source:** `{source_info}`\n*Timestamp:* {ts}"
                if st.session_state.markdown_mode else
                f"{resp}\n\nSource: {source_info} | Timestamp: {ts}"
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

            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

            if col1.button("📋 Copy", key=f"copy_{idx}"):
                escaped = json.dumps(entry["answer"])
                components.html(f"<script>navigator.clipboard.writeText({escaped});</script>")
                col1.success("Copied!")

            if col2.button("🔄 Regenerate", key=f"regen_{idx}"):
                q = entry["question"]
                r2, s2, sp2, ep2, t2 = generate_response(q)
                new_fmt = (
                    f"{r2}\n\n**Source:** `{s2} (pp. {sp2}–{ep2})`\n*Timestamp:* {t2}"
                    if st.session_state.markdown_mode else
                    f"{r2}\n\nSource: {s2} (pp. {sp2}–{ep2}) | Timestamp: {t2}"
                )
                st.session_state.chat_history.append({"question": q, "answer": new_fmt})
                st.rerun()

            if col3.button("👍", key=f"like_{idx}"):
                st.session_state.feedback.append((idx, True))
                col3.success("Thanks!")
            if col4.button("👎", key=f"dislike_{idx}"):
                st.session_state.feedback.append((idx, False))
                col4.warning("Got it!")

# --- Routing ---
if st.session_state.show_homepage:
    show_homepage()
elif st.session_state.show_settings:
    show_settings_page()
else:
    run_chat_interface()
