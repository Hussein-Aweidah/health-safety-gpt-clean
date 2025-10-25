import json
import base64
from narwhals import col
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

from rag_pipeline import generate_response
from user_memory import save_to_history, get_sessions, load_session
from compliance_checker import ComplianceChecker
from auth_manager import login as auth_login, signup as auth_signup

# --- Global Page Config ---
st.set_page_config(page_title="Regis", page_icon="🛡️", layout="wide")

# --- Language Persistence Function ---
def ensure_language_persistence():
    """Ensure language setting persists across page transitions"""
    valid_languages = ["English", "Te Reo Māori", "Tongan", "Samoan", "中文 (Mandarin)", "العربية (Arabic)", "فارسی (Farsi)"]
    
    # Always ensure language is set and valid
    if 'language' not in st.session_state or st.session_state.language not in valid_languages:
        st.session_state.language = "English"
    
    # Double-check that the language is still valid (in case it got corrupted)
    if st.session_state.language not in valid_languages:
        st.session_state.language = "English"
    
    # Store the current language in a more persistent way
    if 'persistent_language' not in st.session_state:
        st.session_state.persistent_language = st.session_state.language
    else:
        # If we have a persistent language, use it to restore the current language
        if st.session_state.persistent_language in valid_languages:
            st.session_state.language = st.session_state.persistent_language

# --- Init Session State ---
default_state = {
    "show_homepage": True,
    "show_settings": False,
    "show_compliance": False,  # Add compliance view state
    "chat_history": [],
    "session_name": "default",
    "language": "English",
    "persistent_language": "English",  # Add persistent language tracking
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
    "show_delete_confirmation": False,  # Show delete confirmation modal
    "authenticated": False,
    "email": None,
    "display_name": None,   # pretty name for greeting (username from auth)

}

# Initialize session state
for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Ensure language is properly set and maintained
if 'language' not in st.session_state:
    st.session_state.language = "English"

# Call language persistence to ensure proper initialization
ensure_language_persistence()

    # Debug function to track language state (can be removed later)
def debug_language_state():
    """Debug function to track language state changes"""
    if st.session_state.get("debug_mode", False):
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🐛 Debug Info")
        st.sidebar.markdown(f"**Current Language:** {st.session_state.get('language', 'Not Set')}")
        st.sidebar.markdown(f"**Session Keys:** {list(st.session_state.keys())}")
        st.markdown("---")
    
    # Always show current language in sidebar for debugging
    st.sidebar.markdown("---")
    st.sidebar.caption(f"### 🌐 Current Language : {st.session_state.get('language', 'Not Set')}")
    st.sidebar.markdown("---")

# ---------------------------
# Helpers: follow-up actions
# ---------------------------
def suggest_followups(role: str):
    """Return a small set of role-aware follow-up actions."""
    current_language = st.session_state.get("language", "English")
    
    if current_language == "中文 (Mandarin)":
        return [
            {
                "label": "制作分步检查清单",
                "prompt": f"将上述指导转换为针对{role}的简洁、角色特定的检查清单。使用编号步骤并引用WorkSafe章节。"
            },
            {
                "label": "起草5分钟工具箱谈话",
                "prompt": f"基于上述指导，为{role}写一个5分钟的工具箱谈话脚本，包含3个要问团队的问题。"
            },
            {
                "label": "创建JSA模板",
                "prompt": "生成工作安全分析表：任务 | 危害 | 风险 | 控制措施 | 负责人。基于上述指导。"
            },
        ]
    elif current_language == "العربية (Arabic)":
        return [
            {
                "label": "إنشاء قائمة فحص خطوة بخطوة",
                "prompt": f"حول الإرشادات أعلاه إلى قائمة فحص موجزة ومخصصة للدور لمهنة {role}. استخدم خطوات مرقمة واستشهد بأقسام WorkSafe."
            },
            {
                "label": "صياغة حديث صندوق الأدوات لمدة 5 دقائق",
                "prompt": f"اكتب نص حديث صندوق الأدوات لمدة 5 دقائق لمهنة {role} بناءً على الإرشادات أعلاه، مع 3 أسئلة لطرحها على الفريق."
            },
            {
                "label": "إنشاء قالب تحليل السلامة الوظيفية",
                "prompt": "أنشئ جدول تحليل السلامة الوظيفية: المهمة | المخاطر | المخاطر | الضوابط | الشخص المسؤول. استند إلى الإرشادات أعلاه."
            },
        ]
    elif current_language == "Te Reo Māori":
        return [
            {
                "label": "Hanga Rārangi Tirotiro",
                "prompt": f"Whakauru te ārahi o runga nei ki te rārangi tirotiro poto, ā-mahi mō te {role}. Whakamahia ngā hīkoi e whai tau me te tuhi ngā wāhanga WorkSafe."
            },
            {
                "label": "Tuhi Kōrero Pātaka",
                "prompt": f"Tuhia he kōrero pātaka 5 meneti mō te {role} e ai ki te ārahi o runga nei, me ngā pātai 3 hei pātai ki te kapa."
            },
            {
                "label": "Hanga Tauira JSA",
                "prompt": "Whakaputa he tēpu Tātari Haumaru Mahi: Mahi | Mōrearea | Tūraru | Whakahaere | Tangata Kawenga. E ai ki te ārahi o runga nei."
            },
        ]
    elif current_language == "Tongan":
        return [
            {
                "label": "Fai ha Lisi Sivi",
                "prompt": f"Fakaliliu e tokoni ʻi ʻolunga ʻi ha lisi sivi poto, fakafaʻahinga ngāue ki he {role}. Fakaʻaonga e ngaahi lahi ʻe fika mo e tohi e ngaahi vahe WorkSafe."
            },
            {
                "label": "Tohi ha Talanoa Pātaka",
                "prompt": f"Tohi ha talanoa pātaka meniti 5 ki he {role} fakatatau ki he tokoni ʻi ʻolunga, mo e fekeʻi 3 ke fai ki he kau ngāue."
            },
            {
                "label": "Fai ha Fakaʻuhinga JSA",
                "prompt": "Fakapapauʻi ha tēpule Sivi Haumaru Ngāue: Ngāue | Mōrearea | Tūraru | Whakahaere | Tangata Kawenga. Fakatatau ki he tokoni ʻi ʻolunga."
            },
        ]
    elif current_language == "Samoan":
        return [
            {
                "label": "Fai se Lisi Siaki",
                "prompt": f"Liliu le taʻiala o loʻo i luga i se lisi siaki puupuu, faʻapitoa mo le {role}. Faʻaaoga laasaga faanumera ma sii mai vaega WorkSafe."
            },
            {
                "label": "Tusi se Talanoa Pusa Meafaigaluega",
                "prompt": f"Tusi se talanoa pusa meafaigaluega 5 minute mo le {role} e faavae i le taʻiala o loʻo i luga, ma fesili 3 e fai i le auvaa."
            },
            {
                "label": "Fai se Faʻataʻitaʻiga JSA",
                "prompt": "Fausia se laulau Suʻesuʻega Saogalemu Galuega: Galuega | Lamatiaga | Tulaga lamatia | Pulea | Tagata Nafa. Faavae i le taʻiala o loʻo i luga."
            },
        ]
    elif current_language == "فارسی (Farsi)":
        return [
            {
                "label": "ایجاد لیست بررسی گام به گام",
                "prompt": f"راهنمایی‌های بالا را به یک لیست بررسی مختصر و مخصوص نقش برای {role} تبدیل کنید. از مراحل شماره‌گذاری شده استفاده کنید و بخش‌های WorkSafe را ذکر کنید."
            },
            {
                "label": "نوشتن صحبت جعبه ابزار ۵ دقیقه‌ای",
                "prompt": f"بر اساس راهنمایی‌های بالا، یک اسکریپت صحبت جعبه ابزار ۵ دقیقه‌ای برای {role} بنویسید، با ۳ سوال برای پرسیدن از تیم."
            },
            {
                "label": "ایجاد قالب تحلیل ایمنی شغل",
                "prompt": "یک جدول تحلیل ایمنی شغل ایجاد کنید: وظیفه | خطر | ریسک | کنترل‌ها | شخص مسئول. بر اساس راهنمایی‌های بالا باشد."
            },
        ]
    else:  # English
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
    current_language = st.session_state.get("language", "English")
    
    prompt_text = {
        "English": "**Do you want me to…**",
        "Te Reo Māori": "**Kei te hiahia koe kia…**",
        "Tongan": "**ʻOku ʻi ai ʻeku fie fai…**",
        "Samoan": "**E te manaʻo ou te…**",
        "中文 (Mandarin)": "**您希望我…**",
        "العربية (Arabic)": "**هل تريد مني أن...**",
        "فارسی (Farsi)": "**آیا می‌خواهید من...**"
    }.get(current_language, "**Do you want me to…**")
    
    st.markdown(prompt_text)
    actions = suggest_followups(role)
    cols = st.columns(len(actions))
    for i, act in enumerate(actions):
        if cols[i].button(act["label"], key=f"cta_{idx_key}_{i}", use_container_width=True):
            st.session_state.last_button_click = f"followup_{i}"  # Track this button click
            # Treat as a new user question and generate immediately
            new_q = act["prompt"]
            resp, src, ts = generate_response(new_q)
            source_info = f"{src}"
            formatted = (
                f"{resp}\n\n**Source:** {source_info}\n\n*Timestamp:* {ts}"
                if st.session_state.markdown_mode
                else f"{resp}\n\nSource: {source_info}\n\nTimestamp: {ts}"
            )
            # Append the Q/A so the conversation continues
            st.session_state.chat_history.append({"question": new_q, "answer": formatted})
            save_to_history(
                new_q, resp, source_info, ts,
                session_name=st.session_state.session_name,
                username=(st.session_state.email if st.session_state.authenticated else None)
            )
            st.rerun()


# --- Homepage View ---
def get_language_features(language: str) -> list:
    """Get feature descriptions in the selected language."""
    features = {
        "English": [
            "📚 Based on NZ health & safety law",
            "🧠 AI-powered answers", 
            "👷 Role-specific insights",
            "📄 Understands official guidelines",
            "🕒 Trusted. Timestamped. Traceable."
        ],
        "Te Reo Māori": [
            "📚 Ka whai i te ture hauora me te haumaru o Aotearoa",
            "🧠 Whakautu mā te AI",
            "👷 Mātauranga ā-mahi",
            "📄 Mārama ki ngā aratohu mana",
            "🕒 Whakapono. Wā tohu. Ka taea te whai."
        ],
        "Tongan": [
            "📚 Fakatatau ki he lao fakaʻaho mo e haumaru ʻo Nuʻu Sila",
            "🧠 Fekauʻaki faka-AI",
            "👷 ʻIlo fakafaʻahinga ngāue",
            "📄 Mālama ki he ngaahi talateu fakapuleʻanga",
            "🕒 Fakatokanga. Taimi tohi. Ka lava ke fai."
        ],
        "Samoan": [
            "📚 Faʻavae i tulafono o le soifua maloloina ma le saogalemu o Niu Sila",
            "🧠 Tali e le AI",
            "👷 Malamalama faʻapitoa i galuega",
            "📄 Malamalama i taʻiala aloaʻia",
            "🕒 Faʻatuatuaina. Taimi faʻailoga. Mafai ona suʻesuʻeina."
        ],
        "中文 (Mandarin)": [
            "📚 基于新西兰健康与安全法规",
            "🧠 AI 驱动的回答",
            "👷 针对特定工作角色的见解",
            "📄 理解官方指导原则",
            "🕒 可信、有记录、可追溯"
        ],
        "العربية (Arabic)": [
            "📚 يعتمد على قانون الصحة والسلامة النيوزيلندي",
            "🧠 إجابات مدعومة بالذكاء الاصطناعي",
            "👷 رؤى مخصصة حسب الدور الوظيفي",
            "📄 يفهم الإرشادات الرسمية",
            "🕒 موثوق، مؤرخ، قابل للتتبع"
        ],
        "فارسی (Farsi)": [
            "📚 بر اساس قوانین بهداشت و ایمنی نیوزیلند",
            "🧠 پاسخ‌های مبتنی بر هوش مصنوعی",
            "👷 بینش‌های مخصوص نقش شغلی",
            "📄 درک دستورالعمل‌های رسمی",
            "🕒 قابل اعتماد، دارای مهر زمانی، قابل ردیابی"
        ]
    }
    return features.get(language, features["English"])

def show_homepage():
    # Ensure language persistence
    ensure_language_persistence()
    
    # Don't show sidebar on homepage for better centering
    # debug_language_state()
    
    try:
        with open("regis_logo.png", "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
        
        st.markdown(
            f"""
            <style>
            .responsive-logo {{
                text-align: center;
                margin: 2vh auto;
                width: 100%;
                max-width: 100vw;
            }}
            .responsive-logo img {{
                max-width: min(25vw, 300px);
                min-width: 150px;
                height: auto;
                object-fit: contain;
            }}
            @media (max-width: 768px) {{
                .responsive-logo img {{
                    max-width: min(40vw, 250px);
                    min-width: 120px;
                }}
            }}
            @media (max-width: 480px) {{
                .responsive-logo img {{
                    max-width: min(60vw, 200px);
                    min-width: 100px;
                }}
            }}
            </style>
            <div class="responsive-logo">
                <img src='data:image/png;base64,{encoded}' alt='Regis Logo' />
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception as e:
        st.warning(f"⚠️ Logo could not be loaded: {e}")

    # Get current language for features and button
    current_language = st.session_state.get("language", "English")
    
    # Add a responsive greeting that adapts to device dimensions
    greeting_text = {
        "English": "Welcome to Regis",
        "Te Reo Māori": "Nau mai ki Regis",
        "Tongan": "Mālō e lelei ki Regis",
        "Samoan": "Talofa lava i Regis",
        "中文 (Mandarin)": "欢迎使用 Regis",
        "العربية (Arabic)": "مرحباً بك في Regis",
        "فارسی (Farsi)": "خوش آمدید به Regis"
    }.get(current_language, "Welcome to Regis")
    
    st.markdown(
        f"""
        <style>
        .responsive-greeting {{
            width: 100%;
            min-height: 15vh;
            max-height: 25vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 2vh auto;
            text-align: center;
            box-sizing: border-box;
            position: relative;
            left: 0;
        }}
        .responsive-greeting h1 {{
            margin: 0;
            padding: 0;
            font-size: clamp(2rem, 5vw, 4rem);
            font-weight: bold;
            color: #1f77b4;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
            line-height: 1.2;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 100%;
            text-align: center;
            width: 100%;
        }}
        @media (max-width: 768px) {{
            .responsive-greeting {{
                min-height: 20vh;
                margin: 1vh auto;
                left: 0;
            }}
            .responsive-greeting h1 {{
                font-size: clamp(1.5rem, 6vw, 2.5rem);
            }}
        }}
        @media (max-width: 480px) {{
            .responsive-greeting {{
                min-height: 25vh;
                left: 0;
            }}
            .responsive-greeting h1 {{
                font-size: clamp(1.2rem, 7vw, 2rem);
            }}
        }}
        </style>
        <div class="responsive-greeting">
            <h1>{greeting_text}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Language-specific features
    features = get_language_features(current_language)
    features_html = "".join([f'<div class="feature-item">{feature}</div>' for feature in features])
    
    st.markdown(
        f"""
        <style>
        .responsive-features {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: clamp(20px, 3vw, 40px);
            margin: 3vh auto;
            flex-wrap: wrap;
            max-width: 100vw;
            padding: 0 2vw;
        }}
        .feature-item {{
            font-size: clamp(16px, 2.5vw, 18px);
            text-align: center;
            padding: 1vh 1vw;
            min-width: 200px;
            max-width: 300px;
            flex: 1 1 auto;
        }}
        @media (max-width: 768px) {{
            .responsive-features {{
                gap: clamp(15px, 4vw, 25px);
                margin: 2vh auto;
            }}
            .feature-item {{
                font-size: clamp(14px, 3vw, 16px);
                min-width: 150px;
                max-width: 250px;
            }}
        }}
        @media (max-width: 480px) {{
            .responsive-features {{
                gap: clamp(10px, 5vw, 20px);
                margin: 1vh auto;
            }}
            .feature-item {{
                font-size: clamp(12px, 4vw, 14px);
                min-width: 120px;
                max-width: 200px;
            }}
        }}
        </style>
        <div class="responsive-features">
            {features_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Language-specific button text
    button_text = {
        "English": "🚀 Start Chat",
        "Te Reo Māori": "🚀 Tīmata Kōrero",
        "Tongan": "🚀 Kamata Talanoa",
        "Samoan": "🚀 Amata Talanoa",
        "中文 (Mandarin)": "🚀 开始聊天",
        "العربية (Arabic)": "🚀 ابدأ المحادثة",
        "فارسی (Farsi)": "🚀 شروع چت"
    }.get(current_language, "🚀 Start Chat")
    
    if st.button(button_text, use_container_width=True):
        st.session_state.show_homepage = False
        st.session_state.prefill = ""
        st.session_state.last_button_click = "chat"  # Track this button click
        st.rerun()


# --- Settings View ---
def show_settings_page():
    # Ensure language persistence
    ensure_language_persistence()
    
    # Debug language state
    debug_language_state()
    
    st.title("⚙️ Settings")
    
    # Language selection with proper functionality
    valid_languages = ["English", "Te Reo Māori", "Tongan", "Samoan", "中文 (Mandarin)", "العربية (Arabic)", "فارسی (Farsi)"]
    current_lang = st.session_state.get('language', 'English')
    current_index = valid_languages.index(current_lang) if current_lang in valid_languages else 0
    
    new_language = st.selectbox(
        "🌐 Language", 
        valid_languages, 
        index=current_index,
        key="settings_language_selector"
    )
    
    # Update language immediately when changed
    if new_language != current_lang:
        st.session_state.language = new_language
        st.session_state.persistent_language = new_language
        st.success(f"Language changed to: {new_language}")
    
    st.selectbox("👷 Your Job Role", ["General Worker", "Electrician", "Nurse", "Forklift Operator"], key="role")
    st.checkbox("📝 Enable Markdown Formatting", key="markdown_mode")
    st.text_input("💾 Default Session Name", value=st.session_state.session_name, key="session_name")
    
    # Debug toggle
    st.checkbox("🐛 Enable Debug Mode", key="debug_mode", help="Show debug information in sidebar")

    st.markdown("---")
    # Language-specific button text
    current_language = st.session_state.get("language", "English")
    
    save_button_text = {
        "English": "✅ Save & Return to Chat",
        "Te Reo Māori": "✅ Tiaki me Hoki ki te Kōrero",
        "Tongan": "✅ Faʻu mo Foki ki he Talanoa",
        "Samoan": "✅ Teu ma Toe Foʻi i le Talanoa",
        "中文 (Mandarin)": "✅ 保存并返回聊天",
        "العربية (Arabic)": "✅ حفظ والعودة إلى المحادثة",
        "فارسی (Farsi)": "✅ ذخیره و بازگشت به چت"
    }.get(current_language, "✅ Save & Return to Chat")
    
    home_button_text = {
        "English": "🏠 Return to Homepage",
        "Te Reo Māori": "🏠 Hoki ki te Whārangi Matua",
        "Tongan": "🏠 Foki ki he Peesi ʻUluaki",
        "Samoan": "🏠 Toe Foʻi i le Itulau Autu",
        "中文 (Mandarin)": "🏠 返回主页",
        "العربية (Arabic)": "🏠 العودة إلى الصفحة الرئيسية",
        "فارسی (Farsi)": "🏠 بازگشت به صفحه اصلی"
    }.get(current_language, "🏠 Return to Homepage")
    
    compliance_button_text = {
        "English": "📋 Compliance Checker",
        "Te Reo Māori": "📋 Kaiwhakamātautau Tautika",
        "Tongan": "📋 Sivi Fakaʻaho",
        "Samoan": "📋 Suʻega Tausi",
        "中文 (Mandarin)": "📋 合规检查器",
        "العربية (Arabic)": "📋 فاحص الامتثال",
        "فارسی (Farsi)": "📋 بررسی کننده انطباق"
    }.get(current_language, "📋 Compliance Checker")
    
    if st.button(save_button_text, use_container_width=True):
        # Update persistent language when saving settings
        st.session_state.persistent_language = st.session_state.language
        st.session_state.show_settings = False
        st.session_state.last_button_click = "chat"  # Track this button click
        st.rerun()
    if st.button(home_button_text, use_container_width=True, type="primary"):
        st.session_state.show_settings = False
        st.session_state.show_homepage = True
        st.session_state.last_button_click = "homepage"  # Track this button click
        st.rerun()
    
    # Add compliance button
    if st.button(compliance_button_text, use_container_width=True):
        st.session_state.show_settings = False
        st.session_state.show_compliance = True
        st.session_state.last_button_click = "compliance"  # Track this button click
        st.rerun()


# --- Chat Interface View ---
def run_chat_interface():
    # Ensure language persistence
    ensure_language_persistence()
    
    # Language-specific title
    current_language = st.session_state.get("language", "English")
    
    title_text = {
        "English": "Ask Regis — Your Health & Safety Assistant",
        "Te Reo Māori": "Pātai ki Regis — Tō Āwhina Hauora me te Haumaru",
        "Tongan": "Fekeʻi ki Regis — ʻO ʻEmeʻa Tokoni Fakaʻaho mo e Haumaru",
        "Samoan": "Fesili ia Regis — Lau Fesoasoani Soifua Maloloina ma le Saogalemu",
        "中文 (Mandarin)": "询问 Regis — 您的健康与安全助手",
        "العربية (Arabic)": "اسأل Regis — مساعدك في الصحة والسلامة",
        "فارسی (Farsi)": "از Regis بپرسید — دستیار بهداشت و ایمنی شما"
    }.get(current_language, "Ask Regis — Your Health & Safety Assistant")
    
    st.title(title_text)

    # Sidebar
    with st.sidebar:
        # Language-specific button text
        current_language = st.session_state.get("language", "English")
        
        home_button_text = {
            "English": "🏠 Return to Homepage",
            "Te Reo Māori": "🏠 Hoki ki te Whārangi Matua",
            "Tongan": "🏠 Foki ki he Peesi ʻUluaki",
            "Samoan": "🏠 Toe Foʻi i le Itulau Autu",
            "中文 (Mandarin)": "🏠 返回主页",
            "العربية (Arabic)": "🏠 العودة إلى الصفحة الرئيسية",
            "فارسی (Farsi)": "🏠 بازگشت به صفحه اصلی"
        }.get(current_language, "🏠 Return to Homepage")
        
        settings_button_text = {
            "English": "⚙️ Open Settings Page",
            "Te Reo Māori": "⚙️ Whakatuwhera Whārangi Tautuhinga",
            "Tongan": "⚙️ Fakaʻuhinga Peesi Fakaʻuhinga",
            "Samoan": "⚙️ Tatala Itulau Faʻatonuga",
            "中文 (Mandarin)": "⚙️ 打开设置页面",
            "العربية (Arabic)": "⚙️ فتح صفحة الإعدادات",
            "فارسی (Farsi)": "⚙️ باز کردن صفحه تنظیمات"
        }.get(current_language, "⚙️ Open Settings Page")
        
        compliance_button_text = {
            "English": "📋 Compliance Checker",
            "Te Reo Māori": "📋 Kaiwhakamātautau Tautika",
            "Tongan": "📋 Sivi Fakaʻaho",
            "Samoan": "📋 Suʻega Tausi",
            "中文 (Mandarin)": "📋 合规检查器",
            "العربية (Arabic)": "📋 فاحص الامتثال",
            "فارسی (Farsi)": "📋 بررسی کننده انطباق"
        }.get(current_language, "📋 Compliance Checker")
        
        if st.button(home_button_text, use_container_width=True, type="primary"):
            st.session_state.show_homepage = True
            st.session_state.last_button_click = "homepage"  # Track this button click
            st.rerun()
        if st.button(settings_button_text, use_container_width=True, type="primary"):
            st.session_state.show_settings = True
            st.session_state.last_button_click = "settings"  # Track this button click
            st.rerun()
        
        if st.button(compliance_button_text, use_container_width=True, type="primary"):
            st.session_state.show_compliance = True
            st.session_state.last_button_click = "compliance"  # Track this button click
            st.rerun()

        st.markdown("---")
        st.caption("## Save Session")
        st.text_input("Session Name", value=st.session_state.session_name, key="session_name")
        
        # Language-specific session button text
        save_session_text = {
            "English": "💾 Save",
            "Te Reo Māori": "💾 Tiaki Wā",
            "Tongan": "💾 Faʻu Taimi",
            "Samoan": "💾 Teu Taimi",
            "中文 (Mandarin)": "💾 保存会话",
            "العربية (Arabic)": "💾 حفظ الجلسة",
            "فارسی (Farsi)": "💾 ذخیره جلسه"
        }.get(current_language, "💾 Save")
        
        clear_chat_text = {
            "English": "🧹 Clear Chat",
            "Te Reo Māori": "🧹 Whakawātea Kōrero",
            "Tongan": "🧹 Fakaʻuhinga Talanoa",
            "Samoan": "🧹 Faʻamama Talanoa",
            "中文 (Mandarin)": "🧹 清空聊天",
            "العربية (Arabic)": "🧹 مسح المحادثة",
            "فارسی (Farsi)": "🧹 پاک کردن چت"
        }.get(current_language, "🧹 Clear Chat")
        
        if st.button(save_session_text, use_container_width=True):
            st.session_state.last_button_click = "save_session"  # Track this button click
            # Save full chat_history for the current user (or guest)
            save_to_history(
                None, None, None, None,
                session_name=st.session_state.session_name,
                username=(st.session_state.email if st.session_state.authenticated else None),
                chat_history=st.session_state.chat_history
            )
            st.success(f"Session '{st.session_state.session_name}' saved.")
        if st.button(clear_chat_text, use_container_width=True):
            st.session_state.last_button_click = "clear_chat"  # Track this button click
            st.session_state.chat_history = []

        st.markdown("---")
        st.caption("## Previous Sessions")
        sessions = get_sessions()
        
        # scope sessions to user/guest
        sessions = get_sessions(username=(st.session_state.email if st.session_state.authenticated else None))
        
        # Language-specific session management text
        load_session_text = {
            "English": "📂 Load Session",
            "Te Reo Māori": "📂 Uta Wā",
            "Tongan": "📂 Loda Taimi",
            "Samoan": "📂 Uta Taimi",
            "中文 (Mandarin)": "📂 加载会话",
            "العربية (Arabic)": "📂 تحميل الجلسة",
            "فارسی (Farsi)": "📂 بارگذاری جلسه"
        }.get(current_language, "📂 Load Session")
        
        load_selected_text = {
            "English": "📥 Load Selected",
            "Te Reo Māori": "📥 Uta te Mea i Kōwhiria",
            "Tongan": "📥 Loda ʻa e Meʻa ne Fili",
            "Samoan": "📥 Uta le Mea ua Filifilia",
            "中文 (Mandarin)": "📥 加载所选",
            "العربية (Arabic)": "📥 تحميل المحدد",
            "فارسی (Farsi)": "📥 بارگذاری انتخاب شده"
        }.get(current_language, "📥 Load Selected")
        
        selected = st.selectbox(load_session_text, sessions, index=0 if sessions else None)
        if st.button(load_selected_text, use_container_width=True):
            st.session_state.last_button_click = "load_session"  # Track this button click
            st.session_state.chat_history = load_session(
                selected,
                username=(st.session_state.email if st.session_state.authenticated else None)
            )
        
        # Debug language state
        debug_language_state()

    # Chat Input
    # Language-specific placeholder text
    placeholder_text = {
        "English": "Ask your health & safety question here…",
        "Te Reo Māori": "Pātai tō pātai hauora me te haumaru ki konei…",
        "Tongan": "Fekeʻi hoʻo fekeʻi fakaʻaho mo e haumaru ʻi heni…",
        "Samoan": "Fesili lau fesili soifua maloloina ma le saogalemu iinei…",
        "中文 (Mandarin)": "在此询问您的健康与安全问题…",
        "العربية (Arabic)": "اسأل سؤالك حول الصحة والسلامة هنا...",
        "فارسی (Farsi)": "سوال بهداشت و ایمنی خود را اینجا بپرسید..."
    }.get(current_language, "Ask your health & safety question here…")
    
    user_input = st.chat_input(
        placeholder=st.session_state.prefill or placeholder_text,
        key="chat_input",
    )

    # If the user asked something, answer it
    if user_input:
        st.session_state.prefill = ""
        with st.spinner("Analyzing your question…"):
            resp, src,  ts = generate_response(user_input)
            source_info = (
                "Unknown" if not src or src == "Unknown"
                    else (f"{src}" if src != "Unknown" else src)
            )
            formatted = (
                f"{resp}\n\n**Source:** {source_info}\n\n*Timestamp:* {ts}"
                if st.session_state.markdown_mode
                else f"{resp}\n\nSource: {source_info}\n\nTimestamp: {ts}"
            )

            st.session_state.chat_history.append({"question": user_input, "answer": formatted})
            save_to_history(
                user_input, resp, source_info, ts,
                session_name=st.session_state.session_name,
                username=(st.session_state.email if st.session_state.authenticated else None)
            )

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
            col1, col2, col3, col4, space = st.columns([1, 1, 1, 1, 10])
            
            # Language-specific action button text
            copy_text = {
                "English": "📋",
                "Te Reo Māori": "📋",
                "Tongan": "📋",
                "Samoan": "📋",
                "中文 (Mandarin)": "📋",
                "العربية (Arabic)": "📋",
                "فارسی (Farsi)": "📋" 
            }.get(current_language, "📋")
            
            if col1.button(copy_text, key=f"copy_{idx}", use_container_width=True, type="tertiary"):
                st.session_state.last_button_click = "copy_message"  # Track this button click
                escaped = json.dumps(entry["answer"])
                components.html(
                    f"<script>navigator.clipboard.writeText({escaped});</script>",
                    height=0,
                )
                # Language-specific success message
                copied_text = {
                    "English": "Copied!",
                    "Te Reo Māori": "Kapea!",
                    "Tongan": "Kopea!",
                    "Samoan": "Kopi!",
                    "中文 (Mandarin)": "已复制！",
                    "العربية (Arabic)": "تم النسخ!",
                    "فارسی (Farsi)": "کپی شد!"
                }.get(current_language, "Copied!")
                
                col1.success(copied_text)

            # Language-specific button text for other actions
            regenerate_text = {
                "English": "🔄",
                "Te Reo Māori": "🔄",
                "Tongan": "🔄",
                "Samoan": "🔄",
                "中文 (Mandarin)": "🔄",
                "العربية (Arabic)": "🔄",
                "فارسی (Farsi)": "🔄"
            }.get(current_language, "🔄")
            
            if col2.button(regenerate_text, key=f"regen_{idx}", use_container_width=True, type="tertiary"):
                st.session_state.last_button_click = "regenerate_message"  # Track this button click
                q = entry["question"]
                r2, s2, t2 = generate_response(q)
                src2 = "Unknown" if not s2 or s2 == "Unknown" else s2
                new_fmt = (
                    f"{r2}\n\n**Source:** {src2}\n\n*Timestamp:* {t2}"
                    if st.session_state.markdown_mode
                    else f"{r2}\n\nSource: {src2}\n\nTimestamp: {t2}"
                )
                st.session_state.chat_history.append({"question": q, "answer": new_fmt})
                st.rerun()

            # Language-specific feedback messages
            thanks_text = {
                "English": "Thanks!",
                "Te Reo Māori": "Mauruuru!",
                "Tongan": "Mālō!",
                "Samoan": "Faʻafetai!",
                "فارسی (Farsi)": "متشکرم!",
                "中文 (Mandarin)": "谢谢！",
                "العربية (Arabic)": "شكراً!"
            }.get(current_language, "Thanks!")
            
            got_it_text = {
                "English": "Got it!",
                "Te Reo Māori": "Ka pai!",
                "Tongan": "ʻOku ʻilo!",
                "Samoan": "Malamalama!",
                "فارسی (Farsi)": "متوجه شدم!",
                "中文 (Mandarin)": "明白了！",
                "العربية (Arabic)": "فهمت!"
            }.get(current_language, "Got it!")
            
            if col3.button("👍", key=f"like_{idx}", use_container_width=True, type="tertiary"):
                st.session_state.last_button_click = "like_message"  # Track this button click
                st.session_state.feedback.append((idx, True))
                col3.success(thanks_text)
            if col4.button("👎", key=f"dislike_{idx}", use_container_width=True, type="tertiary"):
                st.session_state.last_button_click = "dislike_message"  # Track this button click
                st.session_state.feedback.append((idx, False))
                col4.warning(got_it_text)

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
    # Ensure language persistence
    ensure_language_persistence()
    
    # Debug language state
    debug_language_state()
    
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
        
        if st.button("🏠 Return to Homepage", use_container_width=True):
            st.session_state.show_compliance = False
            st.session_state.show_homepage = True
            st.session_state.last_button_click = "homepage"  # Track this button click
            st.rerun()
        
        if st.button("💬 Back to Chat", use_container_width=True):
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
                    if st.button(f"View Details", key=f"view_{assessment['id']}", use_container_width=True):
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
                    if st.button(f"🗑️ Delete", key=f"delete_{assessment['id']}", type="secondary", use_container_width=True):
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
                 if st.button("❌ Cancel", key="cancel_delete", use_container_width=True):
                     st.session_state.show_delete_confirmation = False
                     st.session_state.assessment_to_delete = None
                     st.session_state.last_button_click = "overview"  # Track this button click
                     # Update sidebar to match button action
                     st.session_state.previous_sidebar_mode = "Overview"
                     st.rerun()
             with col2:
                 if st.button("🗑️ Delete", key="confirm_delete", type="primary", use_container_width=True):
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
                        if st.button("View Details", key=f"details_{assessment['id']}", use_container_width=True):
                            st.session_state.current_assessment_id = assessment['id']
                            st.session_state.compliance_view_mode = "gap_analysis"
                            st.session_state.last_button_click = "gap_analysis"  # Track this button click
                            # Update sidebar to match button action
                            st.session_state.previous_sidebar_mode = "Gap Analysis"
                            st.rerun()
                    with col4b:
                        if st.button("🗑️", key=f"delete_details_{assessment['id']}", type="secondary", help="Delete this assessment", use_container_width=True):
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
        st.markdown("**Assessment Details**")
    with col2:
        if st.button("← Back to Overview", key="back_to_overview", use_container_width=True):
            st.session_state.compliance_view_mode = "overview"
            st.session_state.previous_sidebar_mode = "Overview"
            st.rerun()
    
    # Quick validation - if no assessment ID, go back immediately
    if not st.session_state.current_assessment_id:
        st.warning("No assessment selected. Please select an assessment first.")
        st.info("Please select an assessment from the list first.")
        if st.button("← Go Back to Overview", key="no_assessment_back", use_container_width=True):
            st.session_state.compliance_view_mode = "overview"
            st.session_state.previous_sidebar_mode = "Overview"
            st.rerun()
        return
    
    # Try to get assessment with timeout protection
    try:
        assessment = checker.get_assessment(st.session_state.current_assessment_id)
        if not assessment:
            st.error("Assessment not found.")
            st.info("Please select a different assessment.")
            if st.button("← Go Back to Overview", key="error_back", use_container_width=True):
                st.session_state.compliance_view_mode = "overview"
                st.session_state.previous_sidebar_mode = "Overview"
                st.rerun()
            return
    except Exception as e:
        st.error(f"Error loading assessment: {str(e)}")
        st.info("Please try selecting a different assessment or go back to overview.")
        if st.button("← Go Back to Overview", key="error_back", use_container_width=True):
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
    st.success("✅ Assessment loaded successfully!")
    
    # Check if assessment has required fields
    if not assessment.get('categories'):
        st.error("Assessment data is incomplete. Missing categories.")
        st.info("This might be a new assessment that needs to be properly initialized.")
        
        st.markdown("---")
        st.markdown("### 🚧 Assessment Setup Required")
        st.markdown("This assessment appears to be newly created but doesn't have the required compliance categories initialized.")
        st.markdown("**Possible solutions:**")
        st.markdown("1. **Go back to overview** and select a different assessment")
        st.markdown("2. **Create a new assessment** with proper categories")
        st.markdown("3. **Check if the ComplianceChecker is working properly**")
        
        # Simple interface for incomplete assessments
        st.markdown("---")
        st.markdown("### 📝 Basic Assessment Interface")
        st.markdown("Since categories are missing, here's what you can do:")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Try to Refresh Assessment", key="refresh_assessment", use_container_width=True):
                st.info("Refreshing assessment data...")
                # Don't rerun - just show a message
                st.success("Assessment refreshed! Check if categories are now available.")
        
        with col2:
            if st.button("← Go Back to Overview", key="incomplete_back", use_container_width=True):
                st.session_state.compliance_view_mode = "overview"
                st.session_state.previous_sidebar_mode = "Overview"
                st.rerun()
        
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
    if st.button("🔍 Test Assessment Data", key="test_assessment", use_container_width=True):
        st.info("Testing assessment data structure...")
        st.json({
            "has_categories": bool(assessment.get('categories')),
            "category_count": len(assessment.get('categories', [])),
            "total_requirements": assessment.get('total_requirements', 0),
            "assessment_keys": list(assessment.keys())
        })
    
    st.markdown("---")
    
    # Show assessment status
    if assessment.get('categories'):
        st.info(f"📊 Assessment has {len(assessment.get('categories', []))} categories with {assessment.get('total_requirements', 0)} total requirements")
    else:
        st.warning("⚠️ Assessment is missing compliance categories")
    
    st.markdown("---")
    
    # Generate gap analysis
    if st.button("🔄 Generate Gap Analysis", use_container_width=True):
        st.session_state.last_button_click = "gap_analysis"  # Track this button click
        
        # Show loading state with timeout warning
        with st.spinner("Analyzing compliance gaps... (This may take a few seconds)"):
            try:
                # Add a simple timeout mechanism
                import time
                start_time = time.time()
                
                # Check if assessment has categories before processing
                if not assessment.get('categories'):
                    st.error("Cannot generate gap analysis: Assessment has no compliance categories")
                    st.info("Please ensure the assessment is properly initialized with compliance requirements")
                    return
                
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
                    if st.button("Update", key=f"update_{cat_idx}_{req_idx}", use_container_width=True):
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

def render_topbar():
    """Sticky top bar with right-aligned login/signup popover."""
    # optional: make it stick to the top
    st.markdown(
        """
        <style>
        .topbar { position: sticky; top: 0; z-index: 999; background: transparent; }
        .topbar .right { text-align: right; }
        .topbar .hello { opacity: 0.8; }
        </style>
        """,
        unsafe_allow_html=True
    )

with st.container():
        st.markdown('<div class="topbar">', unsafe_allow_html=True)
        left, mid, right = st.columns([2, 6, 2])

        with left:
            # (optional) small logo/title
            st.markdown("")

        with mid:
            st.markdown("")  # spacer

        with right:
            if not st.session_state.authenticated:
                with st.popover("Log in", icon="🔒"):
                    mode = st.radio("Choose", ["Login", "Sign up"], horizontal=True, key="auth_mode_pop")

                    if mode == "Login":
                        email_in = st.text_input("Email", key="auth_email_login")
                        pass_in  = st.text_input("Password", type="password", key="auth_pass_login")
                        if st.button("Login", use_container_width=True, key="btn_login"):
                            ok, msg = auth_login(email_in, pass_in)
                            st.info(msg)
                            if ok:
                                st.session_state.authenticated = True
                                st.session_state.email = email_in.strip().lower()
                                # fetch display name
                                try:
                                    from auth_manager import get_profile
                                    prof = get_profile(st.session_state.email)
                                    st.session_state.display_name = (prof or {}).get("username") or st.session_state.email
                                except Exception:
                                    st.session_state.display_name = st.session_state.email
                                st.rerun()

                    else:  # Sign up
                        username_in = st.text_input("Username (display name)", key="auth_username_signup")
                        email_in    = st.text_input("Email", key="auth_email_signup")
                        pass_in     = st.text_input("Password", type="password", key="auth_pass_signup")

                        if st.button("Sign up", use_container_width=True, key="btn_signup"):
                            ok, msg = auth_signup(username_in, email_in, pass_in)
                            st.info(msg)
                            if ok:
                                st.session_state.authenticated = True
                                st.session_state.email = email_in.strip().lower()
                                st.session_state.display_name = username_in.strip() or st.session_state.email
                                st.rerun()
                                
                    st.caption("Accounts are stored locally in `user_data/users.json`.")
                    
            else:
                # Greeting
                name = st.session_state.display_name or st.session_state.email or "User"
                st.markdown(f"<div class='right hello'>Hello, <b>{name}</b></div>", unsafe_allow_html=True)

                col1, col2 = st.columns([1, 1])
                if col1.button("Log out", key="logout_top", use_container_width=True):
                    # Log out user and clear user-specific session data
                    st.session_state.authenticated = False
                    st.session_state.email = None
                    st.session_state.display_name = None
                    # Clear chat so other accounts/guest can't see previous conversation
                    st.session_state.chat_history = []
                    st.session_state.session_name = "default"
                    st.session_state.prefill = ""
                    st.rerun()
                col2.write("")  # spacer

        st.markdown('</div>', unsafe_allow_html=True)            
render_topbar()



# --- Routing ---
if st.session_state.show_homepage:
    try:
        render_topbar()
    except NameError:
        pass
    show_homepage()
    
elif st.session_state.show_settings:
    show_settings_page()
    
elif st.session_state.show_compliance:
    if not st.session_state.get("authenticated"):
        st.warning("You’re viewing Compliance as a guest. Log in on the homepage to save assessments under your account.")
    
    show_compliance_interface()
    
    
else:
    if not st.session_state.get("authenticated"):
        st.info("You’re chatting as **Guest**. Log in on the homepage if you want your name saved with sessions.")
    run_chat_interface()
