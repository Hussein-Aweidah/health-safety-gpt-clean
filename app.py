import json
import streamlit as st
import streamlit.components.v1 as components
from rag_pipeline import generate_response
from user_memory import get_chat_history, save_to_history, get_sessions, load_session

# --- Global Page Config (only once) ---
st.set_page_config(
    page_title="Regis",
    page_icon="🛡️",
    layout="wide"
)

# --- Initialize session state ---
for key, default in {
    "show_homepage": True,
    "show_settings": False,
    "chat_history": [],
    "session_name": "default",
    "language": "English",
    "role": "General Worker",
    "markdown_mode": True,
    "prefill": "",
    "feedback": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- HOMEPAGE VIEW ---
def show_homepage():
    try:
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        st.image("regis_logo.png", width=140)
        st.markdown("</div>", unsafe_allow_html=True)
    except:
        st.warning("⚠️ Logo could not be loaded.")

    st.markdown("""
        <h1 style='text-align: center; color: #1a1a1a;'>Regis</h1>
        <h4 style='text-align: center; font-weight: normal; color: #444;'>Where Safety Meets Intelligence</h4>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""
    ### 🔍 Why Choose Regis?
    - 📚 **Based on New Zealand health & safety law**
    - 🧠 **AI-powered answers to complex workplace scenarios**
    - 👷 **Role-specific insights**
    - 📄 **Understands official PDFs and guidelines**
    - 🕒 **Trusted. Timestamped. Traceable.**
    """, unsafe_allow_html=True)

    if st.button("🚀 Start Chat", use_container_width=True):
        st.session_state.show_homepage = False
        st.session_state.prefill = ""
        st.rerun()

# --- SETTINGS PAGE VIEW ---
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

# --- GPT CHAT VIEW ---
def run_chat_interface():
    st.title("💬 Ask Regis — Your Health & Safety Assistant")

    # --- SIDEBAR ---
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

    # --- CHAT INPUT ---
    user_input = st.chat_input(
        placeholder=st.session_state.prefill or "Ask your health & safety question here…",
        key="chat_input"
    )

    if user_input:
        st.session_state.prefill = ""
        with st.spinner("Analyzing your question…"):
            resp, src, sp, ep, ts = generate_response(user_input)
            source_info = f"{src} (pp. {sp}–{ep})"
            if st.session_state.markdown_mode:
                formatted = f"{resp}\n\n**Source:** `{source_info}`\n*Timestamp:* {ts}"
            else:
                formatted = f"{resp}\n\nSource: {source_info} | Timestamp: {ts}"

            st.session_state.chat_history.append({"question": user_input, "answer": formatted})
            save_to_history(user_input, resp, source_info, f"{sp}–{ep}", ts,
                            session_name=st.session_state.session_name)

    # --- CHAT HISTORY + UTILITY BUTTONS ---
    for idx, entry in enumerate(st.session_state.chat_history):
        with st.chat_message("user"):
            st.markdown(entry["question"])
        with st.chat_message("assistant"):
            if st.session_state.markdown_mode:
                st.markdown(entry["answer"])
            else:
                st.text(entry["answer"])

            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

            # Copy to clipboard
            escaped = json.dumps(entry["answer"])
            copy_js = (
                "<script>"
                f"navigator.clipboard.writeText({escaped});"
                "</script>"
            )
            if col1.button("📋 Copy", key=f"copy_{idx}"):
                components.html(copy_js)
                col1.success("Copied!")

            # Regenerate
            if col2.button("🔄 Regenerate", key=f"regen_{idx}"):
                q = entry["question"]
                r2, s2, sp2, ep2, t2 = generate_response(q)
                new_fmt = (
                    f"{r2}\n\n**Source:** `{s2} (pp. {sp2}–{ep2})`\n*Timestamp:* {t2}"
                    if st.session_state.markdown_mode
                    else f"{r2}\n\nSource: {s2} (pp. {sp2}–{ep2}) | Timestamp: {t2}"
                )
                st.session_state.chat_history.append({"question": q, "answer": new_fmt})
                st.rerun()

            # Feedback
            if col3.button("👍", key=f"like_{idx}"):
                st.session_state.feedback.append((idx, True))
                col3.success("Thanks!")
            if col4.button("👎", key=f"dislike_{idx}"):
                st.session_state.feedback.append((idx, False))
                col4.warning("Got it!")

# --- ROUTER ---
if st.session_state.show_homepage:
    show_homepage()
elif st.session_state.show_settings:
    show_settings_page()
else:
    run_chat_interface()

