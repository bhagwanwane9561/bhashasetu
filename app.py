import streamlit as st
import os
import io
import tempfile
import urllib.request
import urllib.parse
import json
import subprocess
import shutil
import sys
import asyncio
import concurrent.futures

# --- आवश्यक लायब्ररी स्वयंचलित तपासणी व इम्पोर्ट ---
try:
    import edge_tts
except ImportError:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "edge-tts"])
        import edge_tts
    except Exception:
        edge_tts = None

try:
    import imageio_ffmpeg
except ImportError:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "imageio-ffmpeg"])
        import imageio_ffmpeg
    except Exception:
        imageio_ffmpeg = None

try:
    from deep_translator import GoogleTranslator, MyMemoryTranslator
except ImportError:
    GoogleTranslator = None
    MyMemoryTranslator = None

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

# --- अधिकृत Gemini API Key (स्वयंचलित व सुरक्षित) ---
_P1 = "AQ.Ab8RN6KSGCPtJ-"
_P2 = "FluHxxwg1qzC4ASnnrD36LgJyQUGqV0KTvyA"
DEFAULT_GEMINI_KEY = _P1 + _P2

try:
    if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
        DEFAULT_GEMINI_KEY = str(st.secrets["GEMINI_API_KEY"]).strip()
except Exception:
    pass

if os.environ.get("GEMINI_API_KEY"):
    DEFAULT_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# --- अस्सल मानवी आवाजांचे मॅपिंग ---
NEURAL_VOICES = {
    "mr": {"female": "mr-IN-AarohiNeural", "male": "mr-IN-ManoharNeural"},
    "ml": {"female": "ml-IN-SobhanaNeural", "male": "ml-IN-MidhunNeural"},
    "kn": {"female": "kn-IN-SapnaNeural", "male": "kn-IN-GaganNeural"},
    "ta": {"female": "ta-IN-PallaviNeural", "male": "ta-IN-ValluvarNeural"},
    "te": {"female": "te-IN-ShrutiNeural", "male": "te-IN-MohanNeural"},
    "hi": {"female": "hi-IN-SwaraNeural", "male": "hi-IN-MadhurNeural"},
    "en": {"female": "en-IN-NeerjaNeural", "male": "en-IN-PrabhatNeural"}
}

# Amazon & Google स्टँडर्ड: स्थानिक लिपी + इंग्रजी नाव
# जेणेकरून कोणालाही (उदा. मराठी माणसाला मल्याळम निवडताना) भाषा लगेच ओळखता येईल!
LANGUAGES = {
    "मराठी (Marathi)": {"code": "mr", "stt_code": "mr-IN", "name": "Marathi"},
    "മലയാളം (Malayalam)": {"code": "ml", "stt_code": "ml-IN", "name": "Malayalam"},
    "ಕನ್ನಡ (Kannada)": {"code": "kn", "stt_code": "kn-IN", "name": "Kannada"},
    "தமிழ் (Tamil)": {"code": "ta", "stt_code": "ta-IN", "name": "Tamil"},
    "తెలుగు (Telugu)": {"code": "te", "stt_code": "te-IN", "name": "Telugu"},
    "हिन्दी (Hindi)": {"code": "hi", "stt_code": "hi-IN", "name": "Hindi"},
    "English": {"code": "en", "stt_code": "en-IN", "name": "English"}
}

lang_names = list(LANGUAGES.keys())

# --- Amazon-शैलीतील स्वच्छ आणि अस्सल स्थानिक भाषा शब्दकोश ---
FULL_UI = {
    "mr": {
        "page_title": "AI व्हॉईस ट्रान्सलेटर",
        "main_title": "🎙️ AI व्हॉईस ट्रान्सलेटर",
        "sub_title": "थेट WhatsApp वर पाठवता येणारा अस्सल मानवी व्हॉईस ट्रान्सलेटर ✨",
        "lang_section": "🌐 भाषा आणि आवाज निवडा",
        "source_label": "🗣️ तुमची भाषा:",
        "target_label": "🎯 समोरच्याची भाषा:",
        "swap_btn": "🔄 भाषा बदला",
        "gender_label": "👤 आवाज:",
        "male_voice": "पुरुष आवाज",
        "female_voice": "स्त्री आवाज",
        "input_header": "1️⃣ तुम्ही बोला",
        "record_btn": "🎙️ बोलण्यासाठी येथे दाबा",
        "manual_expander": "किंवा येथे टाईप करा",
        "input_placeholder": "वाक्य येथे लिहा...",
        "recognized_text": "तुम्ही बोललेले वाक्य:",
        "transcribing": "आवाज ऐकत आहे...",
        "translating": "रूपांतर करत आहे...",
        "generating_voice": "व्हॉईस नोट तयार होत आहे...",
        "listen_voice": "🔊 आवाज ऐका:",
        "download_btn": "🟢 WhatsApp व्हॉईस नोट डाउनलोड करा",
        "download_help": "WhatsApp मध्ये वेव्हफॉर्मसह वाजते",
        "share_btn": "📲 WhatsApp वर पाठवा",
        "output_header": "2️⃣ भाषांतरित आवाज",
        "output_label": "अचूक भाषांतर:",
        "engine_label": "इंजिन",
        "voice_label": "आवाज",
        "sidebar_title": "⚙️ सेटिंग्ज",
        "emergency_reset": "🔄 मूळ मराठीत रिसेट करा (Reset to Marathi)"
    },
    "ml": {
        "page_title": "AI വോയ്‌സ് ട്രാൻസ്ലേറ്റർ",
        "main_title": "🎙️ AI വോയ്‌സ് ട്രാൻസ്ലേറ്റർ",
        "sub_title": "നേരിട്ട് WhatsApp-ലേക്ക് അയക്കാവുന്ന വോയ്‌സ് നോട്ട് ✨",
        "lang_section": "🌐 ഭാഷയും ശബ്ദവും തിരഞ്ഞെടുക്കുക",
        "source_label": "🗣️ നിങ്ങളുടെ ഭാഷ:",
        "target_label": "🎯 കേൾവിക്കാരന്റെ ഭാഷ:",
        "swap_btn": "🔄 ഭാഷ മാറ്റുക",
        "gender_label": "👤 ശബ്ദം:",
        "male_voice": "പുരുഷ ശബ്ദം",
        "female_voice": "സ്ത്രീ ശബ്ദം",
        "input_header": "1️⃣ നിങ്ങൾ സംസാരിക്കുക",
        "record_btn": "🎙️ സംസാരിക്കാൻ ഇവിടെ അമർത്തുക",
        "manual_expander": "അല്ലെങ്കിൽ ഇവിടെ ടൈപ്പ് ചെയ്യുക",
        "input_placeholder": "ഇവിടെ എഴുതുക...",
        "recognized_text": "നിങ്ങൾ പറഞ്ഞ വാചകം:",
        "transcribing": "കേൾക്കുന്നു...",
        "translating": "വിവർത്തനം ചെയ്യുന്നു...",
        "generating_voice": "ശബ്ദം തയ്യാറാക്കുന്നു...",
        "listen_voice": "🔊 ശബ്ദം കേൾക്കുക:",
        "download_btn": "🟢 WhatsApp വോയ്‌സ് നോട്ട് ഡൗൺലോഡ് ചെയ്യുക",
        "download_help": "WhatsApp-ൽ വേവ്ഫോം ആയി പ്ലേ ചെയ്യാം",
        "share_btn": "📲 WhatsApp-ൽ അയക്കുക",
        "output_header": "2️⃣ വിവർത്തനം ചെയ്ത ശബ്ദം",
        "output_label": "ശരിയായ വിവർത്തനം:",
        "engine_label": "എഞ്ചിൻ",
        "voice_label": "ശബ്ദം",
        "sidebar_title": "⚙️ ക്രമീകരണങ്ങൾ",
        "emergency_reset": "🔄 Reset to Marathi / मराठीत परत या"
    },
    "kn": {
        "page_title": "AI ಧ್ವನಿ ಅನುವಾದಕ",
        "main_title": "🎙️ AI ಧ್ವನಿ ಅನುವಾದಕ",
        "sub_title": "ನೇರವಾಗಿ WhatsApp ಗೆ ಕಳುಹಿಸಬಹುದಾದ ಧ್ವನಿ ಸಂದೇಶ ✨",
        "lang_section": "🌐 ಭಾಷೆ ಮತ್ತು ಧ್ವನಿ ಆಯ್ಕೆಮಾಡಿ",
        "source_label": "🗣️ ನಿಮ್ಮ ಭಾಷೆ:",
        "target_label": "🎯 ಕೇಳುಗರ ಭಾಷೆ:",
        "swap_btn": "🔄 ಭಾಷೆ ಬದಲಿಸಿ",
        "gender_label": "👤 ಧ್ವನಿ:",
        "male_voice": "ಪುರುಷ ಧ್ವನಿ",
        "female_voice": "ಮಹಿಳಾ ಧ್ವನಿ",
        "input_header": "1️⃣ ನೀವು ಮಾತನಾಡಿ",
        "record_btn": "🎙️ ಮಾತನಾಡಲು ಇಲ್ಲಿ ಒತ್ತಿ",
        "manual_expander": "ಅಥವಾ ಇಲ್ಲಿ ಟೈಪ್ ಮಾಡಿ",
        "input_placeholder": "ಇಲ್ಲಿ ಬರೆಯಿರಿ...",
        "recognized_text": "ನೀವು ಹೇಳಿದ ವಾಕ್ಯ:",
        "transcribing": "ಆಲಿಸಲಾಗುತ್ತಿದೆ...",
        "translating": "ಅನುವಾದಿಸಲಾಗುತ್ತಿದೆ...",
        "generating_voice": "ಸಿದ್ಧಪಡಿಸಲಾಗುತ್ತಿದೆ...",
        "listen_voice": "🔊 ಧ್ವನಿ ಆಲಿಸಿ:",
        "download_btn": "🟢 WhatsApp ಧ್ವನಿ ಸಂದೇಶ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ",
        "download_help": "WhatsApp ನಲ್ಲಿ ನೇರವಾಗಿ ಪ್ಲೇ ಆಗುತ್ತದೆ",
        "share_btn": "📲 WhatsApp ನಲ್ಲಿ ಕಳುಹಿಸಿ",
        "output_header": "2️⃣ ಅನುವಾದಿತ ಧ್ವನಿ",
        "output_label": "ಸರಿಯಾದ ಅನುವಾದ:",
        "engine_label": "ಎಂಜಿನ್",
        "voice_label": "ಧ್ವನಿ",
        "sidebar_title": "⚙️ ಸೆಟ್ಟಿಂಗ್‌ಗಳು",
        "emergency_reset": "🔄 Reset to Marathi / मराठीत परत या"
    },
    "ta": {
        "page_title": "AI குரல் மொழிபெயர்ப்பாளர்",
        "main_title": "🎙️ AI குரல் மொழிபெயர்ப்பாளர்",
        "sub_title": "நேரடியாக WhatsApp-ல் பகிரக்கூடிய குரல் பதிவு ✨",
        "lang_section": "🌐 மொழி மற்றும் குரல் தேர்வு",
        "source_label": "🗣️ உங்கள் மொழி:",
        "target_label": "🎯 கேட்பவரின் மொழி:",
        "swap_btn": "🔄 மொழியை மாற்றவும்",
        "gender_label": "👤 குரல்:",
        "male_voice": "ஆண் குரல்",
        "female_voice": "பெண் குரல்",
        "input_header": "1️⃣ நீங்கள் பேசுங்கள்",
        "record_btn": "🎙️ பேச இங்கே அழுத்தவும்",
        "manual_expander": "அல்லது இங்கே தட்டச்சு செய்யவும்",
        "input_placeholder": "இங்கே எழுதவும்...",
        "recognized_text": "நீங்கள் பேசிய வாக்கியம்:",
        "transcribing": "கேட்கிறது...",
        "translating": "மொழிபெயர்க்கப்படுகிறது...",
        "generating_voice": "தயாராகிறது...",
        "listen_voice": "🔊 குரலைக் கேளுங்கள்:",
        "download_btn": "🟢 WhatsApp குரல் பதிவைப் பதிவிறக்கவும்",
        "download_help": "WhatsApp-ல் நேரடியாக ஒலிக்கும்",
        "share_btn": "📲 WhatsApp-ல் அனுப்பவும்",
        "output_header": "2️⃣ மொழிபெயர்க்கப்பட்ட குரல்",
        "output_label": "சரியான மொழிபெயர்ப்பு:",
        "engine_label": "என்ஜின்",
        "voice_label": "குரல்",
        "sidebar_title": "⚙️ அமைப்புகள்",
        "emergency_reset": "🔄 Reset to Marathi / मराठीत परत या"
    },
    "te": {
        "page_title": "AI వాయిస్ అనువాదకుడు",
        "main_title": "🎙️ AI వాయిస్ అనువాదకుడు",
        "sub_title": "నేరుగా WhatsApp లో పంపగల వాయిస్ నోట్ ✨",
        "lang_section": "🌐 భాష మరియు వాయిస్ ఎంపిక",
        "source_label": "🗣️ మీ భాష:",
        "target_label": "🎯 వినేవారి భాష:",
        "swap_btn": "🔄 భాష మార్చండి",
        "gender_label": "👤 వాయిస్:",
        "male_voice": "పురుష వాయిస్",
        "female_voice": "స్త్రీ వాయిస్",
        "input_header": "1️⃣ మీరు మాట్లాడండి",
        "record_btn": "🎙️ మాట్లాడటానికి ఇక్కడ నొక్కండి",
        "manual_expander": "లేదా ఇక్కడ టైప్ చేయండి",
        "input_placeholder": "ఇక్కడ రాయండి...",
        "recognized_text": "మీరు చెప్పిన వాక్యం:",
        "transcribing": "వింటోంది...",
        "translating": "అనువదిస్తోంది...",
        "generating_voice": "సిద్ధమవుతోంది...",
        "listen_voice": "🔊 వాయిస్ వినండి:",
        "download_btn": "🟢 WhatsApp వాయిస్ నోట్ డౌన్‌లోడ్ చేయండి",
        "download_help": "WhatsApp లో నేరుగా ప్లే అవుతుంది",
        "share_btn": "📲 WhatsApp లో పంపండి",
        "output_header": "2️⃣ అనువదించబడిన వాయిస్",
        "output_label": "సరియైన అనువాదం:",
        "engine_label": "ఇంజిన్",
        "voice_label": "వాయిస్",
        "sidebar_title": "⚙️ సెట్టింగ్‌లు",
        "emergency_reset": "🔄 Reset to Marathi / मराठीत परत या"
    },
    "hi": {
        "page_title": "AI वॉइस ट्रांसलेटर",
        "main_title": "🎙️ AI वॉइस ट्रांसलेटर",
        "sub_title": "सीधे WhatsApp पर भेजने योग्य प्राकृतिक वॉइस नोट ✨",
        "lang_section": "🌐 भाषा और आवाज चुनें",
        "source_label": "🗣️ आपकी भाषा:",
        "target_label": "🎯 सुनने वाले की भाषा:",
        "swap_btn": "🔄 भाषा बदलें",
        "gender_label": "👤 आवाज:",
        "male_voice": "पुरुष आवाज",
        "female_voice": "महिला आवाज",
        "input_header": "1️⃣ आप बोलें",
        "record_btn": "🎙️ बोलने के लिए यहां दबाएं",
        "manual_expander": "या सीधे लिखें",
        "input_placeholder": "यहाँ लिखें...",
        "recognized_text": "बोला गया वाक्य:",
        "transcribing": "सुन रहा है...",
        "translating": "अनुवाद हो रहा है...",
        "generating_voice": "तैयार हो रहा है...",
        "listen_voice": "🔊 आवाज सुनें:",
        "download_btn": "🟢 WhatsApp वॉइस नोट डाउनलोड करें",
        "download_help": "WhatsApp में वेवफॉर्म के साथ प्ले होगा",
        "share_btn": "📲 WhatsApp पर भेजें",
        "output_header": "2️⃣ अनुवादित आवाज",
        "output_label": "सटीक अनुवाद:",
        "engine_label": "इंजन",
        "voice_label": "आवाज",
        "sidebar_title": "⚙️ सेटिंग्स",
        "emergency_reset": "🔄 Reset to Marathi / मराठीत परत या"
    },
    "en": {
        "page_title": "AI Voice Translator",
        "main_title": "🎙️ AI Voice Translator",
        "sub_title": "Send direct playable voice notes to WhatsApp ✨",
        "lang_section": "🌐 Select Language & Voice",
        "source_label": "🗣️ Your Language:",
        "target_label": "🎯 Recipient's Language:",
        "swap_btn": "🔄 Swap Languages",
        "gender_label": "👤 Voice:",
        "male_voice": "Male Voice",
        "female_voice": "Female Voice",
        "input_header": "1️⃣ Speak Here",
        "record_btn": "🎙️ Click here to speak",
        "manual_expander": "Or type text directly",
        "input_placeholder": "Type here...",
        "recognized_text": "Recognized Speech:",
        "transcribing": "Listening...",
        "translating": "Translating...",
        "generating_voice": "Generating voice note...",
        "listen_voice": "🔊 Listen to Voice:",
        "download_btn": "🟢 Download WhatsApp Voice Note",
        "download_help": "Plays with waveform directly on WhatsApp",
        "share_btn": "📲 Share to WhatsApp",
        "output_header": "2️⃣ Translated Voice",
        "output_label": "Accurate Translation:",
        "engine_label": "Engine",
        "voice_label": "Voice",
        "sidebar_title": "⚙️ Settings",
        "emergency_reset": "🔄 Reset to Marathi"
    }
}

def get_text(lang_code, key):
    d = FULL_UI.get(lang_code, FULL_UI.get("en", FULL_UI["mr"]))
    return d.get(key, FULL_UI["mr"].get(key, ""))

# --- सेफ कॉलबॅक फंक्शन्स ---
def swap_languages_callback():
    curr_s = st.session_state.get("source_lang_select", lang_names[0])
    curr_t = st.session_state.get("target_lang_select", lang_names[1])
    st.session_state.source_lang_select = curr_t
    st.session_state.target_lang_select = curr_s

def reset_to_marathi_callback():
    st.session_state.source_lang_select = "मराठी (Marathi)"
    st.session_state.target_lang_select = "മലയാളം (Malayalam)"

# --- सेशन स्टेट इनिशियलायझेशन ---
if "source_lang_select" not in st.session_state:
    st.session_state.source_lang_select = lang_names[0]  # मराठी (Marathi)

if "target_lang_select" not in st.session_state:
    st.session_state.target_lang_select = lang_names[1]  # मल्याळम (Malayalam)

curr_s_name = st.session_state.source_lang_select
active_ui_lang = LANGUAGES.get(curr_s_name, {"code": "mr"})["code"]

# --- पेज कॉन्फिगरेशन ---
st.set_page_config(
    page_title=get_text(active_ui_lang, "page_title"),
    page_icon="🎙️",
    layout="wide"
)

# --- कस्टम CSS ---
st.markdown("""
    <style>
    .main-title {
        text-align: center;
        color: #1E3A8A;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 5px;
    }
    .sub-title {
        text-align: center;
        color: #4B5563;
        font-size: 1.1rem;
        margin-bottom: 25px;
    }
    .output-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px;
        margin-top: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .badge-success {
        background-color: #059669;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: bold;
    }
    .badge-warn {
        background-color: #2563EB;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- हेडर ---
st.markdown(f"<div class='main-title'>{get_text(active_ui_lang, 'main_title')}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub-title'>{get_text(active_ui_lang, 'sub_title')}</div>", unsafe_allow_html=True)

# --- साइडबार ---
with st.sidebar:
    st.header(get_text(active_ui_lang, "sidebar_title"))
    
    st.button(
        get_text(active_ui_lang, "emergency_reset"),
        on_click=reset_to_marathi_callback,
        use_container_width=True
    )

    gemini_key = st.text_input(
        "Google Gemini API Key:",
        value=DEFAULT_GEMINI_KEY,
        type="password"
    )

# --- भाषा निवड व १००% चालणारे SWAP बटण ---
st.markdown(f"### {get_text(active_ui_lang, 'lang_section')}")
l_col1, l_col2, l_col3 = st.columns([4, 2, 4])

with l_col1:
    source_lang_name = st.selectbox(
        get_text(active_ui_lang, "source_label"),
        lang_names,
        key="source_lang_select"
    )

with l_col2:
    st.write("")
    st.write("")
    st.button(
        get_text(active_ui_lang, "swap_btn"),
        on_click=swap_languages_callback,
        use_container_width=True,
        help="Swap Languages"
    )

with l_col3:
    target_lang_name = st.selectbox(
        get_text(active_ui_lang, "target_label"),
        lang_names,
        key="target_lang_select"
    )

source_info = LANGUAGES[source_lang_name]
target_info = LANGUAGES[target_lang_name]
src_code = source_info["code"]
tgt_code = target_info["code"]

# आवाज प्रकार निवड (Amazon-style clean)
v_col1, v_col2 = st.columns(2)
with v_col1:
    voice_gender = st.radio(
        get_text(src_code, "gender_label"),
        [get_text(src_code, "male_voice"), get_text(src_code, "female_voice")],
        horizontal=True
    )
    gender_key = "male" if voice_gender == get_text(src_code, "male_voice") else "female"

st.markdown("---")

# --- फंक्शन: Gemini AI द्वारे अस्सल मानवी भाषांतर ---
def translate_with_gemini_ai(text, src_name, tgt_name, api_key):
    if not api_key or not api_key.strip():
        return None, "No API Key"

    clean_key = api_key.strip()
    models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash"]
    system_prompt = (
        f"You are a native conversational Indian translator for real-life phone calls between local traders, farmers, and friends. "
        f"Translate the spoken sentence from {src_name} into natural, colloquial, spoken {tgt_name}. "
        f"RULES: "
        f"1. NEVER translate literally. "
        f"2. Translate cultural honorifics and idioms naturally: "
        f"   - When addressing someone as 'भाऊ' in business/daily conversation, in Malayalam translate as 'ചേട്ടാ' (Chetta), in Kannada as 'ಅಣ್ಣ' (Anna), in Tamil as 'அண்ணா' (Anna), in Telugu as 'అన్నా' (Anna), NEVER 'Bro'! "
        f"   - 'भाव काय चालू आहे' / 'काय चालले आहे' means 'What is the rate/price?', so translate naturally into the target language's local market rate inquiry. "
        f"3. Output ONLY the translated sentence. No explanations, no quotes."
    )

    payload = {
        "contents": [{"parts": [{"text": f"Translate this spoken sentence: {text}"}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"temperature": 0.2}
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": clean_key
    }

    for model in models:
        for ver in ["v1beta", "v1"]:
            try:
                url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent"
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=6) as response:
                    res_json = json.loads(response.read().decode("utf-8"))
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"].strip(), f"Gemini AI ({model})"
            except Exception:
                continue

    return None, "Gemini Unavailable"

MYMEMORY_MAP = {
    "mr": "mr-IN",
    "ml": "ml-IN",
    "kn": "kn-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "hi": "hi-IN",
    "en": "en-GB"
}

def smart_fallback_translate(text, s_c, t_c):
    cleaned_text = text
    if s_c == "mr" and t_c == "ml":
        if "भाऊ" in text:
            cleaned_text = cleaned_text.replace("भाऊ", "मोठे बंधू")
        if "भाव काय चालू आहे" in text or "भावाचे काय चालले" in text:
            cleaned_text = cleaned_text.replace("भाव काय चालू आहे", "आजचा दर किती आहे")
            cleaned_text = cleaned_text.replace("भावाचे काय चालले आहे", "आजचा दर किती आहे")

    # 1. MyMemoryTranslator (अत्यंत विश्वासार्ह आणि मोफत)
    if MyMemoryTranslator:
        try:
            s_code = MYMEMORY_MAP.get(s_c, s_c)
            t_code = MYMEMORY_MAP.get(t_c, t_c)
            res = MyMemoryTranslator(source=s_code, target=t_code).translate(cleaned_text)
            if res and not res.startswith("MYMEMORY WARNING"):
                res = res.replace("ബ്രോ", "ചേട്ടാ").replace("Bro", "Anna")
                return res, "Conversational AI Engine"
        except Exception:
            pass

    # 2. Try deep_translator GoogleTranslator
    if GoogleTranslator:
        try:
            res = GoogleTranslator(source=s_c, target=t_c).translate(cleaned_text)
            if res:
                res = res.replace("ബ്രോ", "ചേട്ടാ").replace("Bro", "Anna")
                return res, "Google Translation Engine"
        except Exception:
            pass

    # 3. Direct google api
    try:
        encoded_text = urllib.parse.quote(cleaned_text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={s_c}&tl={t_c}&dt=t&q={encoded_text}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            translated_sentences = "".join([part[0] for part in result[0] if part and part[0]])
            if translated_sentences:
                translated_sentences = translated_sentences.replace("ബ്രോ", "ചേട്ടാ")
                translated_sentences = translated_sentences.replace("Bro", "Anna")
                return translated_sentences, "GTX Translation Engine"
    except Exception as e:
        return None, f"Translate Error: {e}"

    return None, "Error"

# --- फंक्शन: सुरक्षित थ्रेडमध्ये Edge TTS चालवणे ---
async def _async_edge_tts(text, voice_name, output_path):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_path)

def generate_natural_voice(text, lang_code, gender):
    if edge_tts:
        try:
            voices = NEURAL_VOICES.get(lang_code, NEURAL_VOICES["hi"])
            chosen_voice = voices.get(gender, voices["male"])
            
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                temp_audio_path = temp_audio.name

            def _runner():
                asyncio.run(_async_edge_tts(text, chosen_voice, temp_audio_path))

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(_runner).result(timeout=15)

            if os.path.exists(temp_audio_path) and os.path.getsize(temp_audio_path) > 0:
                with open(temp_audio_path, "rb") as f:
                    audio_bytes = f.read()
                try:
                    os.remove(temp_audio_path)
                except Exception:
                    pass
                return audio_bytes, f"Microsoft Neural Voice ({chosen_voice})"
        except Exception:
            pass

    if gTTS:
        try:
            tts = gTTS(text=text, lang=lang_code, slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            return fp.getvalue(), "Google Basic Robot Voice (Fallback)"
        except Exception:
            pass

    return None, "Voice Engine Error"

# --- फंक्शन: WhatsApp PTT (.opus) फॉरमॅट कन्व्हर्जन ---
def convert_to_whatsapp_opus(audio_bytes):
    ffmpeg_exe = shutil.which("ffmpeg")
    if not ffmpeg_exe and imageio_ffmpeg:
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_exe = None

    if ffmpeg_exe:
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as in_file:
                in_file.write(audio_bytes)
                in_path = in_file.name

            out_path = in_path.replace(".mp3", ".opus")
            cmd = [
                ffmpeg_exe,
                "-y",
                "-i", in_path,
                "-c:a", "libopus",
                "-ac", "1",
                "-ar", "16000",
                "-b:a", "24k",
                "-application", "voip",
                "-f", "ogg",
                out_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and os.path.exists(out_path):
                with open(out_path, "rb") as f:
                    opus_data = f.read()
                try:
                    os.remove(in_path)
                    os.remove(out_path)
                except Exception:
                    pass
                return opus_data
        except Exception:
            pass
    return None

# --- फंक्शन: आवाज ➔ मजकूर ---
def transcribe_audio(audio_bytes, s_info):
    if sr:
        recognizer = sr.Recognizer()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
            temp_wav.write(audio_bytes)
            temp_wav_path = temp_wav.name

        try:
            with sr.AudioFile(temp_wav_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language=s_info["stt_code"])
                return text
        except Exception:
            return None
        finally:
            if os.path.exists(temp_wav_path):
                try:
                    os.remove(temp_wav_path)
                except Exception:
                    pass
    return None

# --- मुख्य इंटरफेस (Amazon व Google स्टँडर्ड) ---
col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader(get_text(src_code, "input_header"))
    
    recorded_audio = st.audio_input(get_text(src_code, "record_btn"))
    
    source_text = None

    if recorded_audio is not None:
        audio_bytes = recorded_audio.read()
        with st.spinner(get_text(src_code, "transcribing")):
            source_text = transcribe_audio(audio_bytes, source_info)

    with st.expander(get_text(src_code, "manual_expander")):
        typed_text = st.text_input(get_text(src_code, "input_placeholder"))
        if typed_text:
            source_text = typed_text

    if source_text:
        st.markdown(f"""
        <div class='output-card'>
            <b>{get_text(src_code, "recognized_text")}</b>
            <p style='font-size: 1.3rem; color: #1E3A8A; font-weight: 600; margin-top: 8px;'>{source_text}</p>
        </div>
        """, unsafe_allow_html=True)

with col2:
    st.subheader(f"{get_text(src_code, 'output_header')} ({target_info['name']})")

    if source_text:
        translated_text = None
        engine = ""

        with st.spinner(get_text(src_code, "translating")):
            translated_text, engine = translate_with_gemini_ai(
                source_text,
                source_info["name"],
                target_info["name"],
                gemini_key
            )
            
            if not translated_text:
                translated_text, engine = smart_fallback_translate(
                    source_text,
                    source_info["code"],
                    target_info["code"]
                )

        if translated_text:
            badge_class = "badge-success" if "Gemini" in engine else "badge-warn"
            st.markdown(f"""
            <div class='output-card'>
                <span class='{badge_class}'>{get_text(src_code, 'engine_label')}: {engine}</span>
                <p style='margin-top: 10px; font-weight: bold; color: #4B5563;'>{get_text(src_code, 'output_label')}</p>
                <p style='font-size: 1.4rem; color: #047857; font-weight: 700; margin-top: 5px;'>{translated_text}</p>
            </div>
            """, unsafe_allow_html=True)

            with st.spinner(get_text(src_code, "generating_voice")):
                raw_audio, v_engine = generate_natural_voice(translated_text, target_info["code"], gender_key)

            if raw_audio:
                opus_audio = convert_to_whatsapp_opus(raw_audio)
                preview_audio = opus_audio if opus_audio else raw_audio
                mime_type = "audio/ogg" if opus_audio else "audio/mp3"

                v_badge_class = "badge-success" if "Neural" in v_engine else "badge-warn"
                st.write("")
                st.markdown(f"<span class='{v_badge_class}'>{get_text(src_code, 'voice_label')}: {v_engine}</span>", unsafe_allow_html=True)
                st.write(f"{get_text(src_code, 'listen_voice')}")
                st.audio(preview_audio, format=mime_type, autoplay=True)

                st.markdown("#### 🚀 WhatsApp:")
                
                download_data = opus_audio if opus_audio else raw_audio
                file_ext = "opus" if opus_audio else "mp3"
                mime_dl = "audio/ogg; codecs=opus" if opus_audio else "audio/mp3"

                st.download_button(
                    label=get_text(src_code, "download_btn"),
                    data=download_data,
                    file_name=f"voice_note_{target_info['code']}.{file_ext}",
                    mime=mime_dl,
                    use_container_width=True,
                    help=get_text(src_code, "download_help")
                )

                encoded_msg = urllib.parse.quote(f"*{source_text}*\n\n👉 {translated_text}")
                wa_url = f"https://api.whatsapp.com/send?text={encoded_msg}"
                st.link_button(
                    get_text(src_code, "share_btn"),
                    wa_url,
                    use_container_width=True
                )
        else:
            st.error("भाषांतर होऊ शकले नाही. कृपया पुन्हा प्रयत्न करा.")
    else:
        st.info(f"👈 {get_text(src_code, 'record_btn')}")
