import json
import base64
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

from rag_pipeline import generate_response
from user_memory import get_chat_history, save_to_history, get_sessions, load_session
from compliance_checker import ComplianceChecker

# --- Global Page Config ---
st.set_page_config(page_title="Regis", page_icon="🛡️", layout="wide")

# --- Init Session State ---
default_state = {
    "show_homepage": True,
    "show_settings": False,
    "show_compliance": False,  # Add compliance view state
    "chat_history": [],
    "session_name": "default",
    "language": "English",
    "role": "General Worker",
    "markdown_mode": True,
    "prefill": "",
    "feedback": [],
    "dark_mode": False,  # Add dark mode state
    "current_assessment_id": None,  # Track current compliance assessment
    "mode_selector": "Overview",  # Compliance interface mode selector
    "compliance_view_mode": "overview",  # Internal mode tracking
    "last_button_click": None,  # Track last button click to prevent sidebar override
    "previous_sidebar_mode": None,  # Track previous sidebar selection
    "assessment_to_delete": None,  # Track assessment to be deleted
    "show_delete_confirmation": False  # Show delete confirmation modal
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
            st.session_state.last_button_click = f"followup_{i}"  # Track this button click
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
        st.session_state.last_button_click = "chat"  # Track this button click
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
        st.session_state.last_button_click = "chat"  # Track this button click
        st.rerun()
    if st.button("🏠 Return to Homepage"):
        st.session_state.show_settings = False
        st.session_state.show_homepage = True
        st.session_state.last_button_click = "homepage"  # Track this button click
        st.rerun()
    
    # Add compliance button
    if st.button("📋 Compliance Checker", use_container_width=True):
        st.session_state.show_settings = False
        st.session_state.show_compliance = True
        st.session_state.last_button_click = "compliance"  # Track this button click
        st.rerun()


# --- Chat Interface View ---
def run_chat_interface():
    st.title("💬 Ask Regis — Your Health & Safety Assistant")

    # Sidebar
    with st.sidebar:
        if st.button("🏠 Return to Homepage"):
            st.session_state.show_homepage = True
            st.session_state.last_button_click = "homepage"  # Track this button click
            st.rerun()
        if st.button("⚙️ Open Settings Page"):
            st.session_state.show_settings = True
            st.session_state.last_button_click = "settings"  # Track this button click
            st.rerun()
        
        if st.button("📋 Compliance Checker"):
            st.session_state.show_compliance = True
            st.session_state.last_button_click = "compliance"  # Track this button click
            st.rerun()

        st.markdown("---")
        st.markdown("## 💾 Session")
        st.text_input("Session Name", value=st.session_state.session_name, key="session_name")
        if st.button("💾 Save Session"):
            st.session_state.last_button_click = "save_session"  # Track this button click
            save_to_history(None, None, None, None, None, session_name=st.session_state.session_name)
            st.success(f"Session '{st.session_state.session_name}' saved.")
        if st.button("🧹 Clear Chat"):
            st.session_state.last_button_click = "clear_chat"  # Track this button click
            st.session_state.chat_history = []

        st.markdown("---")
        st.markdown("## 🕓 Previous Sessions")
        sessions = get_sessions()
        selected = st.selectbox("📂 Load Session", sessions, index=0 if sessions else None)
        if st.button("📥 Load Selected"):
            st.session_state.last_button_click = "load_session"  # Track this button click
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
                st.session_state.last_button_click = "copy_message"  # Track this button click
                escaped = json.dumps(entry["answer"])
                components.html(
                    f"<script>navigator.clipboard.writeText({escaped});</script>",
                    height=0,
                )
                col1.success("Copied!")

            if col2.button("🔄 Regenerate", key=f"regen_{idx}"):
                st.session_state.last_button_click = "regenerate_message"  # Track this button click
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
                st.session_state.last_button_click = "like_message"  # Track this button click
                st.session_state.feedback.append((idx, True))
                col3.success("Thanks!")
            if col4.button("👎", key=f"dislike_{idx}"):
                st.session_state.last_button_click = "dislike_message"  # Track this button click
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


# --- Compliance Interface ---
def show_compliance_interface():
    st.title("📋 Compliance Gap Checker")
    st.markdown("**Identify compliance gaps against NZ health & safety standards**")
    
    # Initialize compliance checker
    if 'compliance_checker' not in st.session_state:
        st.session_state.compliance_checker = ComplianceChecker()
    
    # Ensure current_assessment_id is properly initialized
    if 'current_assessment_id' not in st.session_state:
        st.session_state.current_assessment_id = None
    
    # Initialize previous_sidebar_mode if not set
    if 'previous_sidebar_mode' not in st.session_state:
        st.session_state.previous_sidebar_mode = "Overview"
    
    # Debug information (can be removed later)
    # st.sidebar.markdown(f"**Debug:** Assessment ID = {st.session_state.current_assessment_id}")
    # st.sidebar.markdown(f"**Debug:** View Mode = {st.session_state.compliance_view_mode}")
    
    checker = st.session_state.compliance_checker
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("## 📋 Compliance Tools")
        
        if st.button("🏠 Return to Homepage"):
            st.session_state.show_compliance = False
            st.session_state.show_homepage = True
            st.session_state.last_button_click = "homepage"  # Track this button click
            st.rerun()
        
        if st.button("💬 Back to Chat"):
            st.session_state.show_compliance = False
            st.session_state.last_button_click = "chat"  # Track this button click
            st.rerun()
        
        st.markdown("---")
        
        # Mode selection - use a simple key that doesn't conflict with session state
        mode = st.selectbox(
            "Mode",
            ["Overview", "New Assessment", "View Assessments", "Gap Analysis"],
            key="mode_selector"
        )
        
        # Map the display text to internal mode values
        mode_mapping = {
            "Overview": "overview",
            "New Assessment": "new_assessment", 
            "View Assessments": "view_assessments",
            "Gap Analysis": "gap_analysis"
        }
        
        # Get the selected mode and sync with internal view mode
        selected_mode = mode_mapping.get(mode, "overview")
        
        # Simple mode synchronization - always allow sidebar changes
        if st.session_state.compliance_view_mode != selected_mode:
            st.session_state.compliance_view_mode = selected_mode
            st.session_state.previous_sidebar_mode = mode
    
    # Main content based on mode - use the internal view mode
    try:
        if st.session_state.compliance_view_mode == "overview":
            show_compliance_overview(checker)
        elif st.session_state.compliance_view_mode == "new_assessment":
            show_new_assessment_form(checker)
        elif st.session_state.compliance_view_mode == "view_assessments":
            show_assessments_list(checker)
        elif st.session_state.compliance_view_mode == "gap_analysis":
            show_gap_analysis(checker)
        else:
            st.error(f"Unknown compliance mode: {st.session_state.compliance_view_mode}")
            st.session_state.compliance_view_mode = "overview"
            show_compliance_overview(checker)
    except Exception as e:
        st.error(f"Error in compliance interface: {str(e)}")
        st.session_state.compliance_view_mode = "overview"
        show_compliance_overview(checker)

def show_compliance_overview(checker):
    """Show compliance checker overview and statistics."""
    st.markdown("## 🎯 Compliance Overview")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Assessments", len(checker.list_assessments()))
    
    with col2:
        assessments = checker.list_assessments()
        if assessments:
            avg_score = sum(a["overall_score"] for a in assessments) / len(assessments)
            st.metric("Average Compliance", f"{avg_score:.1f}%")
        else:
            st.metric("Average Compliance", "N/A")
    
    with col3:
        if assessments:
            in_progress = sum(1 for a in assessments if a["status"] == "in_progress")
            st.metric("In Progress", in_progress)
        else:
            st.metric("In Progress", 0)
    
    st.markdown("---")
    
    # Quick actions
    st.markdown("## 🚀 Quick Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("➕ Start New Assessment", use_container_width=True, key="quick_new_assessment"):
            # Update the internal view mode
            st.session_state.compliance_view_mode = "new_assessment"
            st.session_state.last_button_click = "new_assessment"  # Track this button click
            # Update sidebar to match button action (simplified)
            st.session_state.previous_sidebar_mode = "New Assessment"
            # st.sidebar.markdown(f"**Debug:** Button clicked, setting mode to: {st.session_state.compliance_view_mode}")
            st.rerun()
    
    with col2:
        if st.button("📊 View All Assessments", use_container_width=True, key="quick_view_assessments"):
            # Update the internal view mode
            st.session_state.compliance_view_mode = "view_assessments"
            st.session_state.last_button_click = "view_assessments"  # Track this button click
            # Update sidebar to match button action
            st.session_state.previous_sidebar_mode = "View Assessments"
            st.rerun()
    
    st.markdown("---")
    
    # Recent assessments
    st.markdown("## 📋 Recent Assessments")
    assessments = checker.list_assessments()
    
    if assessments:
        for assessment in assessments[:5]:  # Show last 5
            with st.expander(f"🏢 {assessment['business_name']} - {assessment['industry']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Score", f"{assessment['overall_score']:.1f}%")
                with col2:
                    st.metric("Status", assessment['status'].replace('_', ' ').title())
                with col3:
                    st.metric("Requirements", f"{assessment['compliant_requirements']}/{assessment['total_requirements']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"View Details", key=f"view_{assessment['id']}"):
                        # Update session state first
                        st.session_state.current_assessment_id = assessment['id']
                        st.session_state.compliance_view_mode = "gap_analysis"
                        st.session_state.last_button_click = "gap_analysis"  # Track this button click
                        # Update sidebar to match button action
                        st.session_state.previous_sidebar_mode = "Gap Analysis"
                        st.sidebar.success(f"Switching to assessment: {assessment['id']}")
                        # st.sidebar.markdown(f"**Debug:** Button clicked, mode set to: {st.session_state.compliance_view_mode}")
                        # Force a rerun to ensure state is updated
                        st.rerun()
                with col2:
                    if st.button(f"🗑️ Delete", key=f"delete_{assessment['id']}", type="secondary"):
                        st.session_state.assessment_to_delete = assessment['id']
                        st.session_state.show_delete_confirmation = True
                        st.session_state.last_button_click = "overview"  # Track this button click
                        # Update sidebar to match button action
                        st.session_state.previous_sidebar_mode = "Overview"
                        st.rerun()
    else:
        st.info("No assessments yet. Start your first compliance assessment!")
    
    # Delete confirmation modal
    if st.session_state.get('show_delete_confirmation') and st.session_state.get('assessment_to_delete'):
         st.markdown("---")
         st.markdown("## 🗑️ Delete Assessment")
         
         assessment_to_delete = checker.get_assessment(st.session_state.assessment_to_delete)
         if assessment_to_delete:
             st.warning(f"Are you sure you want to delete the assessment for **{assessment_to_delete['business_name']}**?")
             st.info("This action cannot be undone.")
             
             col1, col2, col3 = st.columns([1, 1, 1])
             with col1:
                 if st.button("❌ Cancel", key="cancel_delete"):
                     st.session_state.show_delete_confirmation = False
                     st.session_state.assessment_to_delete = None
                     st.session_state.last_button_click = "overview"  # Track this button click
                     # Update sidebar to match button action
                     st.session_state.previous_sidebar_mode = "Overview"
                     st.rerun()
             with col2:
                 if st.button("🗑️ Delete", key="confirm_delete", type="primary"):
                     try:
                         # Call the delete method from ComplianceChecker
                         if hasattr(checker, 'delete_assessment'):
                             checker.delete_assessment(st.session_state.assessment_to_delete)
                             st.success("Assessment deleted successfully!")
                         else:
                             st.error("Delete method not implemented in ComplianceChecker")
                         
                         # Clear the delete state
                         st.session_state.show_delete_confirmation = False
                         st.session_state.assessment_to_delete = None
                         st.session_state.last_button_click = "overview"  # Track this button click
                         # Update sidebar to match button action
                         st.session_state.previous_sidebar_mode = "Overview"
                         st.rerun()
                     except Exception as e:
                         st.error(f"Error deleting assessment: {str(e)}")
                         st.session_state.show_delete_confirmation = False
                         st.session_state.assessment_to_delete = None
                         st.rerun()

def show_new_assessment_form(checker):
    """Show form to create new compliance assessment."""
    st.markdown("## ➕ New Compliance Assessment")
    
    with st.form("new_assessment"):
        business_name = st.text_input("Business Name", placeholder="Enter your business name")
        industry = st.selectbox(
            "Industry",
            ["construction", "healthcare", "manufacturing", "general"],
            format_func=lambda x: x.title()
        )
        assessor = st.text_input("Assessor Name", placeholder="Who is conducting this assessment?")
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Create Assessment", use_container_width=True)
        with col2:
            if st.form_submit_button("Cancel", use_container_width=True):
                st.session_state.compliance_view_mode = "overview"
                st.session_state.last_button_click = "overview"  # Track this button click
                # Update sidebar to match button action
                st.session_state.previous_sidebar_mode = "Overview"
                st.rerun()
        
        if submitted and business_name and assessor:
            with st.spinner("Creating assessment..."):
                assessment_id = checker.create_assessment(business_name, industry, assessor)
                st.session_state.current_assessment_id = assessment_id
                st.success(f"Assessment created successfully! ID: {assessment_id}")
                st.session_state.compliance_view_mode = "gap_analysis"
                st.session_state.last_button_click = "gap_analysis"  # Track this button click
                # Update sidebar to match button action
                st.session_state.previous_sidebar_mode = "Gap Analysis"
                st.rerun()

def show_assessments_list(checker):
    """Show list of all assessments."""
    st.markdown("## 📊 All Assessments")
    
    assessments = checker.list_assessments()
    
    if assessments:
        for assessment in assessments:
            with st.expander(f"🏢 {assessment['business_name']} - {assessment['industry']} ({assessment['created_date'][:10]})"):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Score", f"{assessment['overall_score']:.1f}%")
                with col2:
                    st.metric("Status", assessment['status'].replace('_', ' ').title())
                with col3:
                    st.metric("Requirements", f"{assessment['compliant_requirements']}/{assessment['total_requirements']}")
                with col4:
                    col4a, col4b = st.columns(2)
                    with col4a:
                        if st.button("View Details", key=f"details_{assessment['id']}"):
                            st.session_state.current_assessment_id = assessment['id']
                            st.session_state.compliance_view_mode = "gap_analysis"
                            st.session_state.last_button_click = "gap_analysis"  # Track this button click
                            # Update sidebar to match button action
                            st.session_state.previous_sidebar_mode = "Gap Analysis"
                            st.rerun()
                    with col4b:
                        if st.button("🗑️", key=f"delete_details_{assessment['id']}", type="secondary", help="Delete this assessment"):
                            st.session_state.assessment_to_delete = assessment['id']
                            st.session_state.show_delete_confirmation = True
                            st.session_state.last_button_click = "view_assessments"  # Track this button click
                            # Update sidebar to match button action
                            st.session_state.previous_sidebar_mode = "View Assessments"
                            st.rerun()
                
                # Category breakdown
                st.markdown("**Category Breakdown:**")
                for cat in assessment['categories_summary']:
                    st.progress(cat['score'] / 100)
                    st.caption(f"{cat['name']}: {cat['score']:.1f}% ({cat['compliant']}/{cat['total']})")
    else:
        st.info("No assessments found. Create your first one!")

def show_gap_analysis(checker):
    """Show detailed gap analysis for a specific assessment."""
    st.markdown("## 🔍 Gap Analysis View")
    
    # Add a quick way to go back
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**Loading assessment details...**")
    with col2:
        if st.button("← Back to Overview", key="back_to_overview"):
            st.session_state.compliance_view_mode = "overview"
            st.session_state.previous_sidebar_mode = "Overview"
            st.rerun()
    
    # Quick validation - if no assessment ID, go back immediately
    if not st.session_state.current_assessment_id:
        st.warning("No assessment selected. Please select an assessment first.")
        st.session_state.compliance_view_mode = "view_assessments"
        st.rerun()
        return
    
    # Show immediate loading state
    with st.spinner("Loading assessment data..."):
        pass  # Just show the spinner briefly
    
    # Try to get assessment with timeout protection
    try:
        assessment = checker.get_assessment(st.session_state.current_assessment_id)
        if not assessment:
            st.error("Assessment not found.")
            st.session_state.compliance_view_mode = "view_assessments"
            st.rerun()
            return
    except Exception as e:
        st.error(f"Error loading assessment: {str(e)}")
        st.info("Please try selecting a different assessment or go back to overview.")
        if st.button("← Go Back to Overview", key="error_back"):
            st.session_state.compliance_view_mode = "overview"
            st.session_state.previous_sidebar_mode = "Overview"
            st.rerun()
        return
    
    # Debug information (commented out for performance)
    # st.sidebar.markdown(f"**Debug:** Current Assessment ID = {st.session_state.current_assessment_id}")
    # st.sidebar.markdown(f"**Debug:** Assessment Data = {list(assessment.keys()) if assessment else 'None'}")
    
    # Show raw assessment data for debugging (commented out for performance)
    # with st.expander("🔍 Raw Assessment Data (Debug)"):
    #     st.json(assessment)
    
    # Always show basic assessment info first
    st.markdown(f"## 📊 Assessment: {assessment.get('business_name', 'Unknown')}")
    st.markdown(f"**Industry:** {assessment.get('industry', 'Unknown').title()}")
    st.markdown(f"**Status:** {assessment.get('status', 'Unknown').replace('_', ' ').title()}")
    st.markdown(f"**Created:** {assessment.get('created_date', 'Unknown')}")
    
    # Quick check for assessment completeness
    st.info("✅ Assessment loaded successfully!")
    
    # Check if assessment has required fields
    if not assessment.get('categories'):
        st.error("Assessment data is incomplete. Missing categories.")
        st.info("This might be a new assessment that needs to be properly initialized.")
        
        st.markdown("---")
        st.markdown("### 🚧 Assessment Setup Required")
        st.markdown("This assessment appears to be newly created but doesn't have the required compliance categories initialized.")
        st.markdown("**Possible solutions:**")
        st.markdown("1. **Refresh the page** - The compliance checker might need to reinitialize")
        st.markdown("2. **Check the ComplianceChecker class** - Ensure it properly creates assessments with categories")
        st.markdown("3. **Restart the app** - Session state might be corrupted")
        
        # TEMPORARY: Show a basic assessment interface even without categories
        st.markdown("---")
        st.markdown("### 📝 Basic Assessment Interface (Temporary)")
        st.markdown("Since categories are missing, here's a basic interface to get you started:")
        
        # Add a button to try to reinitialize the assessment
        if st.button("🔄 Try to Reinitialize Assessment", key="reinit_assessment"):
            try:
                # Try to get the assessment again
                refreshed_assessment = checker.get_assessment(st.session_state.current_assessment_id)
                if refreshed_assessment and refreshed_assessment.get('categories'):
                    st.success("Assessment reinitialized successfully!")
                    st.session_state.last_button_click = "gap_analysis"  # Track this button click
                    st.rerun()
                else:
                    st.error("Still missing categories. Check the ComplianceChecker implementation.")
            except Exception as e:
                st.error(f"Error reinitializing: {str(e)}")
        
        # Show a simple form to manually add categories
        st.markdown("---")
        st.markdown("### ➕ Add Basic Compliance Categories")
        with st.form("add_categories"):
            st.text_input("Category 1 (e.g., 'Risk Management')", key="cat1")
            st.text_input("Category 2 (e.g., 'Training & Competency')", key="cat2")
            st.text_input("Category 3 (e.g., 'Equipment & Maintenance')", key="cat3")
            
            if st.form_submit_button("Add Categories"):
                st.session_state.last_button_click = "gap_analysis"  # Track this button click
                st.info("This is a temporary feature. The real fix is to ensure ComplianceChecker creates assessments with proper categories.")
                st.warning("Categories will not be saved until the ComplianceChecker is properly implemented.")
        
        return
    
    st.markdown(f"## 📊 Gap Analysis: {assessment['business_name']}")
    st.markdown(f"**Industry:** {assessment['industry'].title()} | **Status:** {assessment['status'].replace('_', ' ').title()}")
    
    # Overall score
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Overall Compliance", f"{assessment['overall_score']:.1f}%")
    with col2:
        st.metric("Total Requirements", assessment['total_requirements'])
    with col3:
        st.metric("Compliant Requirements", assessment['compliant_requirements'])
    
    st.markdown("---")
    
    # Quick test section
    st.markdown("### 🧪 Quick Test")
    if st.button("🔍 Test Assessment Data", key="test_assessment"):
        st.info("Testing assessment data structure...")
        st.json({
            "has_categories": bool(assessment.get('categories')),
            "category_count": len(assessment.get('categories', [])),
            "total_requirements": assessment.get('total_requirements', 0),
            "assessment_keys": list(assessment.keys())
        })
    
    st.markdown("---")
    
    # Generate gap analysis
    if st.button("🔄 Generate Gap Analysis"):
        st.session_state.last_button_click = "gap_analysis"  # Track this button click
        
        # Show loading state with timeout warning
        with st.spinner("Analyzing compliance gaps... (This may take a few seconds)"):
            try:
                # Add a simple timeout mechanism
                import time
                start_time = time.time()
                
                gaps = checker.generate_gap_analysis(assessment['id'])
                
                # Check if it took too long
                elapsed_time = time.time() - start_time
                if elapsed_time > 10:  # If it took more than 10 seconds
                    st.warning(f"Gap analysis took {elapsed_time:.1f} seconds - this is slower than expected.")
                
                st.success("Gap analysis completed!")
            except Exception as e:
                st.error(f"Error generating gap analysis: {str(e)}")
                st.info("This might be due to incomplete assessment data or a system issue.")
                return
            
            # Display gaps by priority
            if gaps['critical_gaps']:
                st.error("🚨 Critical Gaps (Immediate Action Required)")
                for gap in gaps['critical_gaps']:
                    st.markdown(f"- **{gap['category']}**: {gap['requirement']}")
            
            if gaps['high_priority_gaps']:
                st.warning("⚠️ High Priority Gaps (Within 1 Week)")
                for gap in gaps['high_priority_gaps']:
                    st.markdown(f"- **{gap['category']}**: {gap['requirement']}")
            
            if gaps['medium_priority_gaps']:
                st.info("ℹ️ Medium Priority Gaps (Within 1 Month)")
                for gap in gaps['medium_priority_gaps']:
                    st.markdown(f"- **{gap['category']}**: {gap['requirement']}")
            
            if gaps['low_priority_gaps']:
                st.success("✅ Low Priority Gaps (Ongoing)")
                for gap in gaps['low_priority_gaps']:
                    st.markdown(f"- **{gap['category']}**: {gap['requirement']}")
            
            # Action plan
            if gaps['action_plan']:
                st.markdown("---")
                st.markdown("## 📋 Action Plan")
                for action in gaps['action_plan']:
                    with st.expander(f"{action['priority']}: {action['action']}"):
                        st.markdown(f"**Timeline:** {action['timeline']}")
                        st.markdown(f"**Resources Needed:** {action['resources_needed']}")
                        st.markdown(f"**Assigned To:** {action['assigned_to']}")
                        st.markdown(f"**Estimated Cost:** {action['estimated_cost']}")
    
    st.markdown("---")
    
    # Assessment interface
    st.markdown("## 📝 Assessment Interface")
    
    for cat_idx, category in enumerate(assessment['categories']):
        with st.expander(f"📁 {category['name']} - {category['score']:.1f}%"):
            for req_idx, requirement in enumerate(category['requirements']):
                st.markdown(f"**{requirement['text']}**")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    status = st.selectbox(
                        "Status",
                        ["not_assessed", "compliant", "non_compliant", "partially_compliant"],
                        index=["not_assessed", "compliant", "non_compliant", "partially_compliant"].index(requirement['status']),
                        key=f"status_{cat_idx}_{req_idx}",
                        format_func=lambda x: x.replace('_', ' ').title()
                    )
                
                with col2:
                    priority = st.selectbox(
                        "Priority",
                        ["low", "medium", "high", "critical"],
                        index=["low", "medium", "high", "critical"].index(requirement['priority']),
                        key=f"priority_{cat_idx}_{req_idx}"
                    )
                
                with col3:
                    if st.button("Update", key=f"update_{cat_idx}_{req_idx}"):
                        st.session_state.last_button_click = "gap_analysis"  # Track this button click
                        checker.update_requirement_status(
                            assessment['id'], cat_idx, req_idx, status, 
                            requirement['compliance_level'], requirement['evidence'],
                            requirement['notes'], priority, requirement['action_required'],
                            requirement['target_date'], requirement['assigned_to']
                        )
                        st.success("Updated!")
                        st.rerun()
                
                # Additional fields
                evidence = st.text_input("Evidence", value=requirement['evidence'], key=f"evidence_{cat_idx}_{req_idx}")
                notes = st.text_area("Notes", value=requirement['notes'], key=f"notes_{cat_idx}_{req_idx}")
                action_required = st.text_input("Action Required", value=requirement['action_required'], key=f"action_{cat_idx}_{req_idx}")
                target_date = st.date_input("Target Date", value=datetime.now().date() if not requirement['target_date'] else datetime.fromisoformat(requirement['target_date']).date(), key=f"date_{cat_idx}_{req_idx}")
                assigned_to = st.text_input("Assigned To", value=requirement['assigned_to'], key=f"assign_{cat_idx}_{req_idx}")
                
                st.markdown("---")

# --- Routing ---
if st.session_state.show_homepage:
    show_homepage()
elif st.session_state.show_settings:
    show_settings_page()
elif st.session_state.show_compliance:
    show_compliance_interface()
else:
    run_chat_interface()
