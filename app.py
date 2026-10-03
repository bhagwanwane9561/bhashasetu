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
import re

# --- आवश्यक लायब्ररी स्वयंचलित तपासणी व इम्पोर्ट ---
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

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
    from gTTS import gTTS
except ImportError:
    gTTS = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# --- Gemini API Key सुरक्षित व स्वयंचलित शोध ---
def get_configured_gemini_key():
    # 1. Streamlit Secrets (Cloud Deployment साठी)
    try:
        if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
            k = str(st.secrets["GEMINI_API_KEY"]).strip()
            if k and not k.startswith("AQ."):
                return k
    except Exception:
        pass
    # 2. Environment Variable
    env_k = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_k and not env_k.startswith("AQ."):
        return env_k
    return ""

def get_configured_openai_key():
    try:
        if "OPENAI_API_KEY" in st.secrets and st.secrets["OPENAI_API_KEY"]:
            return str(st.secrets["OPENAI_API_KEY"]).strip()
    except Exception:
        pass
    return os.environ.get("OPENAI_API_KEY", "").strip()

# --- अस्सल मानवी आवाजांचे मॅपिंग (Microsoft Edge Neural Voices) ---
NEURAL_VOICES = {
    "mr": {"female": "mr-IN-AarohiNeural", "male": "mr-IN-ManoharNeural"},
    "ml": {"female": "ml-IN-SobhanaNeural", "male": "ml-IN-MidhunNeural"},
    "kn": {"female": "kn-IN-SapnaNeural", "male": "kn-IN-GaganNeural"},
    "ta": {"female": "ta-IN-PallaviNeural", "male": "ta-IN-ValluvarNeural"},
    "te": {"female": "te-IN-ShrutiNeural", "male": "te-IN-MohanNeural"},
    "hi": {"female": "hi-IN-SwaraNeural", "male": "hi-IN-MadhurNeural"},
    "en": {"female": "en-IN-NeerjaNeural", "male": "en-IN-PrabhatNeural"}
}

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

# --- Amazon-Google स्टँडर्ड स्थानिक भाषा शब्दकोश ---
FULL_UI = {
    "mr": {
        "page_title": "युनिव्हर्सल AI व्हॉईस ट्रान्सलेटर",
        "main_title": "🎙️ युनिव्हर्सल AI व्हॉईस ट्रान्सलेटर",
        "sub_title": "बोलीभाषा, स्थानिक संदर्भ व थेट WhatsApp साठी अचूक भाषांतर प्रणाली ✨",
        "lang_section": "🌐 भाषा आणि आवाज निवडा",
        "source_label": "🗣️ तुमची भाषा:",
        "target_label": "🎯 समोरच्याची भाषा:",
        "swap_btn": "🔄 भाषा बदला",
        "gender_label": "👤 आवाज:",
        "male_voice": "पुरुष आवाज",
        "female_voice": "स्त्री आवाज",
        "input_header": "1️⃣ तुम्ही बोला किंवा लिहा",
        "record_btn": "🎙️ बोलण्यासाठी येथे दाबा",
        "manual_expander": "किंवा येथे मजकूर टाईप करा",
        "input_placeholder": "उदा. नमस्कार माझे नाव भगवान आहे. काका कांद्याचा भाव काय चालू आहे?",
        "recognized_text": "मूळ वाक्य:",
        "transcribing": "आवाज ऐकत आहे...",
        "translating": "Gemini AI द्वारे संदर्भानुसार भाषांतर होत आहे...",
        "generating_voice": "नैसर्गिक मानवी व्हॉईस नोट तयार होत आहे...",
        "listen_voice": "🔊 भाषांतरित आवाज ऐका:",
        "download_btn": "🟢 WhatsApp व्हॉईस नोट डाउनलोड करा",
        "download_help": "WhatsApp मध्ये वेव्हफॉर्मसह प्ले होते",
        "share_btn": "📲 WhatsApp वर थेट पाठवा",
        "output_header": "2️⃣ भाषांतरित आवाज व मजकूर",
        "output_label": "अचूक संदर्भानुसार भाषांतर:",
        "engine_label": "इंजिन",
        "voice_label": "आवाज",
        "sidebar_title": "⚙️ AI सेटिंग्ज",
        "emergency_reset": "🔄 मूळ मराठीत रिसेट करा"
    },
    "ml": {
        "page_title": "യൂണിവേഴ്സൽ AI വോയ്‌സ് ട്രാൻസ്ലേറ്റർ",
        "main_title": "🎙️ യൂണിവേഴ്സൽ AI വോയ്‌സ് ട്രാൻസ്ലേറ്റർ",
        "sub_title": "തത്സമയ സംഭാഷണങ്ങൾ കൃത്യമായി വിവർത്തനം ചെയ്യുക ✨",
        "lang_section": "🌐 ഭാഷയും ശബ്ദവും തിരഞ്ഞെടുക്കുക",
        "source_label": "🗣️ നിങ്ങളുടെ ഭാഷ:",
        "target_label": "🎯 കേൾവിക്കാരന്റെ ഭാഷ:",
        "swap_btn": "🔄 ഭാഷ മാറ്റുക",
        "gender_label": "👤 ശബ്ദം:",
        "male_voice": "പുരുഷ ശബ്ദം",
        "female_voice": "സ്ത്രീ ശബ്ദം",
        "input_header": "1️⃣ സംസാരിക്കുക അല്ലെങ്കിൽ എഴുതുക",
        "record_btn": "🎙️ സംസാരിക്കാൻ അമർത്തുക",
        "manual_expander": "അല്ലെങ്കിൽ ഇവിടെ ടൈപ്പ് ചെയ്യുക",
        "input_placeholder": "വാചകം ഇവിടെ എഴുതുക...",
        "recognized_text": "യഥാർത്ഥ വാചകം:",
        "transcribing": "ശ്രദ്ധിക്കുന്നു...",
        "translating": "വിവർത്തനം ചെയ്യുന്നു...",
        "generating_voice": "വോയ്‌സ് നോട്ട് തയ്യാറാക്കുന്നു...",
        "listen_voice": "🔊 ശബ്ദം കേൾക്കുക:",
        "download_btn": "🟢 WhatsApp വോയ്‌സ് നോട്ട് ഡൗൺലോഡ് ചെയ്യുക",
        "download_help": "WhatsApp-ൽ തത്സമയം പ്ലേ ചെയ്യാം",
        "share_btn": "📲 WhatsApp-ൽ അയക്കുക",
        "output_header": "2️⃣ വിവർത്തനം ചെയ്ത ശബ്ദം",
        "output_label": "കൃത്യമായ വിവർത്തനം:",
        "engine_label": "എഞ്ചിൻ",
        "voice_label": "ശബ്ദം",
        "sidebar_title": "⚙️ AI ക്രമീകരണങ്ങൾ",
        "emergency_reset": "🔄 Reset to Marathi / मराठीत परत या"
    },
    "kn": {
        "page_title": "ಯುನಿವರ್ಸಲ್ AI ಧ್ವನಿ ಅನುವಾದಕ",
        "main_title": "🎙️ ಯುನಿವರ್ಸಲ್ AI ಧ್ವನಿ ಅನುವಾದಕ",
        "sub_title": "ನೇರವಾಗಿ WhatsApp ಗೆ ಕಳುಹಿಸಬಹುದಾದ ನಿಖರ ಧ್ವನಿ ಸಂದೇಶ ✨",
        "lang_section": "🌐 ಭಾಷೆ ಮತ್ತು ಧ್ವನಿ ಆಯ್ಕೆಮಾಡಿ",
        "source_label": "🗣️ ನಿಮ್ಮ ಭಾಷೆ:",
        "target_label": "🎯 ಕೇಳುಗರ ಭಾಷೆ:",
        "swap_btn": "🔄 ಭಾಷೆ ಬದಲಿಸಿ",
        "gender_label": "👤 ಧ್ವನಿ:",
        "male_voice": "ಪುರುಷ ಧ್ವನಿ",
        "female_voice": "ಮಹಿಳಾ ಧ್ವನಿ",
        "input_header": "1️⃣ ಮಾತನಾಡಿ ಅಥವಾ ಬರೆಯಿರಿ",
        "record_btn": "🎙️ ಮಾತನಾಡಲು ಒತ್ತಿ",
        "manual_expander": "ಅಥವಾ ಇಲ್ಲಿ ಟೈಪ್ ಮಾಡಿ",
        "input_placeholder": "ಇಲ್ಲಿ ಬರೆಯಿರಿ...",
        "recognized_text": "ಮೂಲ ವಾಕ್ಯ:",
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
        "sub_title": "நேரடியாக WhatsApp-ல் பகிரக்கூடிய துல்லிய குரல் பதிவு ✨",
        "lang_section": "🌐 மொழி மற்றும் குரல் தேர்வு",
        "source_label": "🗣️ உங்கள் மொழி:",
        "target_label": "🎯 கேட்பவரின் மொழி:",
        "swap_btn": "🔄 மொழியை மாற்றவும்",
        "gender_label": "👤 குரல்:",
        "male_voice": "ஆண் குரல்",
        "female_voice": "பெண் குரல்",
        "input_header": "1️⃣ பேசுங்கள் அல்லது எழுதுங்கள்",
        "record_btn": "🎙️ பேச இங்கே அழுத்தவும்",
        "manual_expander": "அல்லது இங்கே தட்டச்சு செய்யவும்",
        "input_placeholder": "இங்கே எழுதவும்...",
        "recognized_text": "மூல வாக்கியம்:",
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
        "sub_title": "నేరుగా WhatsApp లో పంపగల సహజ వాయిస్ నోట్ ✨",
        "lang_section": "🌐 భాష మరియు వాయిస్ ఎంపిక",
        "source_label": "🗣️ మీ భాష:",
        "target_label": "🎯 వినేవారి భాష:",
        "swap_btn": "🔄 భాష మార్చండి",
        "gender_label": "👤 వాయిస్:",
        "male_voice": "పురుష వాయిస్",
        "female_voice": "స్త్రీ వాయిస్",
        "input_header": "1️⃣ మాట్లాడండి లేదా టైప్ చేయండి",
        "record_btn": "🎙️ మాట్లాడటానికి ఇక్కడ నొక్కండి",
        "manual_expander": "లేదా ఇక్కడ టైప్ చేయండి",
        "input_placeholder": "ఇక్కడ రాయండి...",
        "recognized_text": "అసలు వాక్యం:",
        "transcribing": "వింటోంది...",
        "translating": "అనువదిస్తోంది...",
        "generating_voice": "సిద్ధమవుతోంది...",
        "listen_voice": "🔊 వాయిస్ వినండి:",
        "download_btn": "🟢 WhatsApp వాయిస్ నోట్ డౌన్‌లోడ్ చేయండి",
        "download_help": "WhatsApp లో నేరుగా ప్లే అవుతుంది",
        "share_btn": "📲 WhatsApp లో పంపండి",
        "output_header": "2️⃣ అనువదించబడిన వాయిസ്",
        "output_label": "సరియైన అనువాదం:",
        "engine_label": "ఇంజిన్",
        "voice_label": "వాయిస్",
        "sidebar_title": "⚙️ సెట్టింగ్‌లు",
        "emergency_reset": "🔄 Reset to Marathi / मराठीत परत या"
    },
    "hi": {
        "page_title": "AI वॉइस ट्रांसलेटर",
        "main_title": "🎙️ युनिवर्सल AI वॉइस ट्रांसलेटर",
        "sub_title": "सीधे WhatsApp पर भेजने योग्य प्राकृतिक वॉइस नोट ✨",
        "lang_section": "🌐 भाषा और आवाज चुनें",
        "source_label": "🗣️ आपकी भाषा:",
        "target_label": "🎯 सुनने वाले की भाषा:",
        "swap_btn": "🔄 भाषा बदलें",
        "gender_label": "👤 आवाज:",
        "male_voice": "पुरुष आवाज",
        "female_voice": "महिला आवाज",
        "input_header": "1️⃣ बोलें या लिखें",
        "record_btn": "🎙️ बोलने के लिए क्लिक करें",
        "manual_expander": "या यहाँ टाइप करें",
        "input_placeholder": "यहाँ लिखें...",
        "recognized_text": "मूल वाक्य:",
        "transcribing": "आवाज सुन रहा है...",
        "translating": "सटीक अनुवाद हो रहा है...",
        "generating_voice": "वॉइस नोट तैयार हो रहा है...",
        "listen_voice": "🔊 अनुवादित आवाज सुनें:",
        "download_btn": "🟢 WhatsApp वॉइस नोट डाउनलोड करें",
        "download_help": "WhatsApp में वेवफॉर्म के साथ प्ले होगा",
        "share_btn": "📲 WhatsApp पर भेजें",
        "output_header": "2️⃣ अनुवादित आवाज",
        "output_label": "सटीक संदर्भानुसार अनुवाद:",
        "engine_label": "इंजन",
        "voice_label": "आवाज",
        "sidebar_title": "⚙️ AI सेटिंग्स",
        "emergency_reset": "🔄 Reset to Marathi / मराठीत परत या"
    },
    "en": {
        "page_title": "Universal AI Voice Translator",
        "main_title": "🎙️ Universal AI Voice Translator",
        "sub_title": "Accurate colloquial voice translator with WhatsApp voice notes ✨",
        "lang_section": "🌐 Select Language & Voice",
        "source_label": "🗣️ Your Language:",
        "target_label": "🎯 Recipient's Language:",
        "swap_btn": "🔄 Swap Languages",
        "gender_label": "👤 Voice Gender:",
        "male_voice": "Male Voice",
        "female_voice": "Female Voice",
        "input_header": "1️⃣ Speak or Type",
        "record_btn": "🎙️ Click to Speak",
        "manual_expander": "Or type text here",
        "input_placeholder": "e.g. Hello, my name is Bhagwan. What is the onion price?",
        "recognized_text": "Original Text:",
        "transcribing": "Listening...",
        "translating": "Translating via Gemini AI...",
        "generating_voice": "Generating voice note...",
        "listen_voice": "🔊 Listen to Voice:",
        "download_btn": "🟢 Download WhatsApp Voice Note",
        "download_help": "Plays with waveform on WhatsApp",
        "share_btn": "📲 Send via WhatsApp",
        "output_header": "2️⃣ Translated Voice & Text",
        "output_label": "Accurate Translation:",
        "engine_label": "Engine",
        "voice_label": "Voice",
        "sidebar_title": "⚙️ AI Settings",
        "emergency_reset": "🔄 Reset to Marathi"
    }
}

def get_text(lang_code, key):
    d = FULL_UI.get(lang_code, FULL_UI.get("en", FULL_UI["mr"]))
    return d.get(key, FULL_UI["mr"].get(key, ""))

# --- कॉलबॅक फंक्शन्स ---
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
        border: 1px solid #CBD5E1;
        border-radius: 12px;
        padding: 20px;
        margin-top: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .badge-gemini {
        background-color: #059669;
        color: white;
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.9rem;
        font-weight: bold;
        display: inline-block;
    }
    .badge-fallback {
        background-color: #D97706;
        color: white;
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: bold;
        display: inline-block;
    }
    .badge-voice {
        background-color: #2563EB;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: bold;
        display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# --- कडक System Instruction आणि भारतीय संदर्भ ग्लॉसरी ---
SYSTEM_INSTRUCTION = """You are an elite, native-level bilingual interpreter and cultural translator for Indian spoken languages (including Marathi, Malayalam, Kannada, Tamil, Telugu, Hindi, English).
Your mission is to provide 100% accurate, natural, colloquial translation for spoken conversations between ordinary citizens, merchants, farmers, businesspersons, relatives, and friends.

CRITICAL LINGUISTIC AND CONTEXTUAL RULES:

1. STRICT PRESERVATION OF PERSONAL NAMES AND PROPER NOUNS:
- Indian personal names (e.g., भगवान / Bhagwan, रमेश / Ramesh, सुरेश / Suresh, राम / Ram, विठ्ठल / Vitthal, ज्ञानेश्वर / Dnyaneshwar, मारुती / Maruti, आनंद / Anand, इत्यादी) are PROPER NOUNS referring to human individuals.
- NEVER EVER translate personal names literally as common nouns, deities, or English words!
  * FORBIDDEN: Translating 'भगवान' as 'God', 'Lord', 'देव', or Malayalam 'ദൈവം'.
  * MANDATORY: Transliterate the name phonetically into the target script:
    - Marathi: भगवान -> Malayalam: ഭഗവാൻ (Bhagwan)
    - Marathi: रमेश -> Malayalam: രമേഷ് (Ramesh)
    - Marathi: सुरेश -> Kannada: ಸುರೇಶ್ (Suresh)
    - Marathi: भगवान -> Kannada: ಭಗವಾನ್ (Bhagwan)
    - Marathi: भगवान -> Tamil: பகவான் (Bhagwan)

2. COMMERCIAL, MARKET & AGRICULTURAL CONTEXT:
- In Indian daily life and commerce, words like 'भाव' (Bhav), 'दर' (Dar), 'किंमत' (Kimmat) refer to "market rate", "selling price", or "commodity cost".
- NEVER EVER translate 'भाव' as "inflation rate" (महागाईचा दर / നാണയപ്പെരുപ്പ നിരക്ക്), "economic inflation index", or "emotion/sentiment"!
  * Example: "कांद्याचा भाव काय चालू आहे" means "What is the market price of onions right now?"
    - Correct Malayalam: "ഉള്ളിയുടെ വില / റേറ്റ് എന്താണ്?" or "ഉള്ളിക്ക് ഇപ്പോൾ എന്ത് വിലയുണ്ട്?"
    - Correct Kannada: "ಈರುಳ್ಳಿ ಬೆಲೆ / ರೇಟ್ ಎಷ್ಟಿದೆ?"
    - Correct Tamil: "வெங்காயத்தின் விலை / ரேட் என்ன?"
    - Correct Telugu: "ఉల్లిపాయల రేటు ఎంత?"

3. CULTURAL RESPECT MARKERS & HONORIFICS:
- Words like 'काका' (Kaka), 'मामा' (Mama), 'भाऊ' (Bhau), 'दादा' (Dada), 'अण्णा' (Anna) are terms of respect and social warmth.
- Translate them naturally into the target language's spoken honorifics:
  * In Malayalam: 'भाऊ' -> 'ചേട്ടാ' (Chetta), 'काका' -> 'അങ്കിൾ' (Uncle) or 'അമ്മാവാ' / 'ചേട്ടാ'.
  * In Kannada: 'भाऊ' / 'दादा' -> 'ಅಣ್ಣ' (Anna), 'काका' -> 'ಕಾಕ' / 'ಚಿಕ್ಕಪ್ಪ'.
  * In Tamil: 'भाऊ' / 'दादा' -> 'அண்ணா' (Anna), 'काका' -> 'சித்தப்பா' / 'மாமா'.
  * In Telugu: 'भाऊ' / 'दादा' -> 'అన్నా' (Anna), 'काका' -> 'బాబాయ్' / 'అంకుల్'.
- NEVER translate them into English slang like "Bro", "dude", or stiff dictionary definitions.

4. SPOKEN COLLOQUIAL FLUENCY:
- Output natural, flowing spoken language that sounds like a real human talking on a phone call or sending a WhatsApp voice note.
- Absolutely NO robotic, literal word-by-word substitution.
- Preserve the exact conversational tone (friendly, respectful, inquiry, trade).

5. OUTPUT RESTRICTIONS:
- Output ONLY the final translated sentence in the target language script.
- Do NOT include notes, explanations, phonetic romanization in brackets, quotation marks, or prefixes.
"""

# --- साइडबार कॉन्फिगरेशन ---
with st.sidebar:
    st.header(get_text(active_ui_lang, "sidebar_title"))
    
    st.button(
        get_text(active_ui_lang, "emergency_reset"),
        on_click=reset_to_marathi_callback,
        use_container_width=True
    )
    st.markdown("---")

    configured_key = get_configured_gemini_key()
    gemini_key = st.text_input(
        "🔑 Google Gemini API Key:",
        value=configured_key,
        type="password",
        help="Google AI Studio (aistudio.google.com) वरून मोफत API Key मिळवा."
    )

    model_options = ["gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
    selected_model = st.selectbox(
        "🧠 AI मॉडेल:",
        model_options,
        index=0,
        help="Gemini 1.5 Pro हे बोलीभाषा व संदर्भासाठी सर्वोत्तम मॉडेल आहे."
    )

    if gemini_key and gemini_key.strip():
        os.environ["GEMINI_API_KEY"] = gemini_key.strip()
        st.success(f"✅ Gemini LLM सक्रिय ({selected_model})")
    else:
        st.warning("⚠️ अचूक भाषांतरासाठी Gemini API Key टाका (किंवा Streamlit Cloud Secrets मध्ये जोडा).")

    st.markdown("---")
    configured_openai = get_configured_openai_key()
    openai_key = st.text_input(
        "🎙️ OpenAI Whisper Key (ऐच्छिक):",
        value=configured_openai,
        type="password",
        help="उच्च दर्जाच्या Whisper STT साठी OpenAI Key (नसल्यास मोफत Google STT वापरले जाईल)."
    )

# --- हेडर ---
st.markdown(f"<div class='main-title'>{get_text(active_ui_lang, 'main_title')}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub-title'>{get_text(active_ui_lang, 'sub_title')}</div>", unsafe_allow_html=True)

if not (gemini_key and gemini_key.strip()):
    st.info("💡 **टीप:** नावांचे अचूक उच्चार (उदा. 'भगवान'चे 'देव' न होणे) आणि 'कांद्याचा भाव' अचूक ओळखण्यासाठी डाव्या बाजूला तुमची **Google Gemini API Key** प्रविष्ट करा. [Google AI Studio वरून मोफत की मिळवा](https://aistudio.google.com/app/apikey).")

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

# आवाज प्रकार निवड (पुरुष / स्त्री)
v_col1, v_col2 = st.columns(2)
with v_col1:
    voice_gender = st.radio(
        get_text(src_code, "gender_label"),
        [get_text(src_code, "male_voice"), get_text(src_code, "female_voice")],
        horizontal=True
    )
    gender_key = "male" if voice_gender == get_text(src_code, "male_voice") else "female"

st.markdown("---")

# --- फंक्शन: Google Gemini 1.5 Pro / Flash द्वारे अचूक संदर्भ भाषांतर ---
def translate_with_gemini_ai(text, src_name, tgt_name, api_key, model_choice="gemini-1.5-pro"):
    if not api_key or not api_key.strip():
        return None, "No API Key"

    clean_key = api_key.strip()
    models_to_try = [model_choice]
    for m in ["gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]:
        if m not in models_to_try:
            models_to_try.append(m)

    user_prompt = f"Translate the following spoken sentence from {src_name} to {tgt_name}:\n\"{text}\""

    # 1. अधिकृत google-genai SDK वापरणे
    if genai is not None:
        for model in models_to_try:
            try:
                client = genai.Client(api_key=clean_key)
                if types is not None and hasattr(types, "GenerateContentConfig"):
                    config = types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.1
                    )
                else:
                    config = {"system_instruction": SYSTEM_INSTRUCTION, "temperature": 0.1}

                response = client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=config
                )
                if response and response.text:
                    out = response.text.strip().strip('"').strip("'")
                    return out, f"Google Gemini ({model})"
            except Exception:
                continue

    # 2. थेट Google Generative Language REST API (सुरक्षित बॅकअप)
    for model in models_to_try:
        for ver in ["v1beta", "v1"]:
            try:
                url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent?key={clean_key}"
                payload = {
                    "contents": [{"parts": [{"text": user_prompt}]}],
                    "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                    "generationConfig": {"temperature": 0.1}
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_json = json.loads(response.read().decode("utf-8"))
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            out = parts[0]["text"].strip().strip('"').strip("'")
                            return out, f"Google Gemini ({model})"
            except Exception:
                continue

    return None, "Gemini Unavailable"

# --- स्मार्ट संरक्षित फॉलबॅक भाषांतर (नावे व संदर्भ सुरक्षित ठेवणारे) ---
NAME_PROTECTION = {
    "भगवान": {"token": "__NAME_BHAGWAN__", "ml": "ഭഗവാൻ", "kn": "ಭಗವಾನ್", "ta": "பகவான்", "te": "భగవాన్", "hi": "भगवान", "en": "Bhagwan"},
    "रमेश": {"token": "__NAME_RAMESH__", "ml": "രമേഷ്", "kn": "ರಮೇಶ್", "ta": "ரமேஷ்", "te": "రమేష్", "hi": "रमेश", "en": "Ramesh"},
    "सुरेश": {"token": "__NAME_SURESH__", "ml": "സുരേഷ്", "kn": "ಸುರೇಶ್", "ta": "சுரேஷ்", "te": "సురేశ్", "hi": "सुरेश", "en": "Suresh"},
    "विठ्ठल": {"token": "__NAME_VITTHAL__", "ml": "വിഠൽ", "kn": "ವಿಠ್ಠಲ", "ta": "விட்டல்", "te": "విఠల్", "hi": "विट्ठल", "en": "Vitthal"},
    "ज्ञानेश्वर": {"token": "__NAME_DNYAN__", "ml": "ജ്ഞാനേശ്വർ", "kn": "ಜ್ಞಾನೇಶ್ವರ", "ta": "ஞானேஸ்வர்", "te": "జ్ఞానేశ్వర్", "hi": "ज्ञानेश्वर", "en": "Dnyaneshwar"},
}

def smart_fallback_translate(text, s_c, t_c):
    cleaned = text
    restorations = {}

    # नावांची सुरक्षा: फॉलबॅक इंजिनला 'भगवान'चे 'God' किंवा 'देव' करू न देणे
    for name, info in NAME_PROTECTION.items():
        if name in cleaned:
            cleaned = cleaned.replace(name, info["token"])
            restorations[info["token"]] = info.get(t_c, name)

    # बाजारभाव संदर्भाचे रक्षण
    if "कांद्याचा भाव" in cleaned:
        cleaned = cleaned.replace("कांद्याचा भाव", "कांद्याचा आजचा दर")
    if "भाव काय चालू आहे" in cleaned:
        cleaned = cleaned.replace("भाव काय चालू आहे", "आजचा दर किती चालू आहे")

    res = None
    engine_name = "Fallback Engine"

    # 1. GoogleTranslator
    if GoogleTranslator:
        try:
            res = GoogleTranslator(source=s_c, target=t_c).translate(cleaned)
            engine_name = "Google Basic Translator"
        except Exception:
            pass

    # 2. MyMemoryTranslator
    if not res and MyMemoryTranslator:
        try:
            mymemory_map = {"mr": "mr-IN", "ml": "ml-IN", "kn": "kn-IN", "ta": "ta-IN", "te": "te-IN", "hi": "hi-IN", "en": "en-GB"}
            s_m = mymemory_map.get(s_c, s_c)
            t_m = mymemory_map.get(t_c, t_c)
            res = MyMemoryTranslator(source=s_m, target=t_m).translate(cleaned)
            engine_name = "Basic Fallback Translator"
        except Exception:
            pass

    # 3. Direct Google GTX API
    if not res:
        try:
            encoded_text = urllib.parse.quote(cleaned)
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={s_c}&tl={t_c}&dt=t&q={encoded_text}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                res = "".join([part[0] for part in result[0] if part and part[0]])
                engine_name = "GTX Basic Engine"
        except Exception:
            pass

    if res:
        # टोकन्स व नावांची अचूक पुनर्रचना (स्पेस किंवा स्पेलिंग फरकांसह)
        if "भगवान" in text:
            tgt_name = NAME_PROTECTION["भगवान"].get(t_c, "Bhagwan")
            res = re.sub(r'\s*(__\s*NAME_BH[A-Z]*\s*__|XBHAGWANX|ദൈവം|God|Lord)\s*', f' {tgt_name} ', res, flags=re.IGNORECASE)
        if "रमेश" in text:
            tgt_name = NAME_PROTECTION["रमेश"].get(t_c, "Ramesh")
            res = re.sub(r'\s*(__\s*NAME_RAM[A-Z]*\s*__|XRAMESHX)\s*', f' {tgt_name} ', res, flags=re.IGNORECASE)
        if "सुरेश" in text:
            tgt_name = NAME_PROTECTION["सुरेश"].get(t_c, "Suresh")
            res = re.sub(r'\s*(__\s*NAME_SUR[A-Z]*\s*__|XSURESHX)\s*', f' {tgt_name} ', res, flags=re.IGNORECASE)

        for token, target_name in restorations.items():
            res = res.replace(token, target_name)

        # बोलीभाषेतील आदरयुक्त शब्द व बाजारभाव सुधारणा
        if t_c == "ml":
            res = res.replace("ബ്രോ", "ചേട്ടാ").replace("Bro", "ചേട്ടാ")
            if "ദൈവം" in res and "भगवान" in text:
                res = res.replace("ദൈവം", "ഭഗവാൻ")
            if "നാണയപ്പെരുപ്പ" in res:
                res = res.replace("നാണയപ്പെരുപ്പ നിരക്ക്", "വില / റേറ്റ്").replace("നാണയപ്പെരുപ്പം", "വില")
            if "നടക്കുന്നത്" in res and "भाव" in text:
                res = res.replace("നടക്കുന്നത്", "എന്താണ്")
        elif t_c in ["kn", "ta", "te"]:
            res = res.replace("Bro", "Anna").replace("bro", "anna")

        res = re.sub(r'\s+', ' ', res).strip()
        return res, engine_name

    return None, "Error"

# --- फंक्शन: सुरक्षित थ्रेडमध्ये Edge Neural TTS चालवणे ---
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
            return fp.getvalue(), "Google Basic Voice (Fallback)"
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

# --- फंक्शन: ऑडिओ ऑप्टिमायझेशन (मोठ्या फाईल्स 80% हलक्या करणे) ---
def optimize_audio_size(audio_bytes):
    if not audio_bytes or len(audio_bytes) < 512 * 1024:
        return audio_bytes

    ffmpeg_exe = shutil.which("ffmpeg")
    if not ffmpeg_exe and imageio_ffmpeg:
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_exe = None

    if ffmpeg_exe:
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as in_f:
                in_f.write(audio_bytes)
                in_p = in_f.name
            out_p = in_p.replace(".wav", "_opt.wav")

            # 16kHz, Mono, 16-bit PCM कॉम्प्रेस
            cmd = [
                ffmpeg_exe, "-y", "-i", in_p,
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                out_p
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
            if res.returncode == 0 and os.path.exists(out_p):
                with open(out_p, "rb") as f:
                    opt_bytes = f.read()
                try:
                    os.remove(in_p)
                    os.remove(out_p)
                except Exception:
                    pass
                return opt_bytes
        except Exception:
            pass
    return audio_bytes

# --- फंक्शन: Gemini Multimodal द्वारे थेट ऑडिओ वाचन (मोठ्या फाईल्ससाठी) ---
def transcribe_with_gemini(audio_bytes, s_info, api_key):
    if not api_key or not api_key.strip() or genai is None:
        return None
    try:
        client = genai.Client(api_key=api_key.strip())
        prompt = f"Listen carefully to this spoken {s_info['name']} audio. Transcribe the exact words spoken into {s_info['name']} script without missing any word. Return ONLY the transcribed text, no quotes or notes."
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                prompt
            ]
        )
        if response and response.text:
            return response.text.strip().strip('"').strip("'")
    except Exception:
        pass
    return None

# --- फंक्शन: आवाज ➔ मजकूर (Whisper किंवा Google STT किंवा Gemini) ---
def transcribe_audio(audio_bytes, s_info, openai_api_key=None, gemini_api_key=None):
    # पायरी १: मोठ्या ऑडिओचे स्वयंचलित कॉम्प्रेशन
    compact_audio = optimize_audio_size(audio_bytes)

    # 1. Whisper API (उपलब्ध असल्यास)
    if openai_api_key and openai_api_key.strip() and OpenAI is not None:
        try:
            client = OpenAI(api_key=openai_api_key.strip())
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
                temp_wav.write(compact_audio)
                temp_wav_path = temp_wav.name
            try:
                with open(temp_wav_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language=s_info["code"],
                        prompt="मराठी संभाषण, बोलीभाषा, स्थानिक नावे जसे की भगवान, रमेश, बाजारभाव."
                    )
                if transcript and transcript.text:
                    return transcript.text.strip()
            finally:
                if os.path.exists(temp_wav_path):
                    os.remove(temp_wav_path)
        except Exception:
            pass

    # 2. मोफत Google Speech Recognition
    if sr:
        recognizer = sr.Recognizer()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
            temp_wav.write(compact_audio)
            temp_wav_path = temp_wav.name

        try:
            with sr.AudioFile(temp_wav_path) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language=s_info["stt_code"])
                if text:
                    return text
        except Exception:
            pass
        finally:
            if os.path.exists(temp_wav_path):
                try:
                    os.remove(temp_wav_path)
                except Exception:
                    pass

    # 3. Gemini Multimodal Audio (मोठ्या किंवा अस्पष्ट आवाजासाठी अंतिम शक्तिशाली बॅकअप)
    if gemini_api_key and gemini_api_key.strip():
        gemini_text = transcribe_with_gemini(compact_audio, s_info, gemini_api_key)
        if gemini_text:
            return gemini_text

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
            source_text = transcribe_audio(audio_bytes, source_info, openai_key, gemini_key)

    with st.expander(get_text(src_code, "manual_expander"), expanded=(source_text is None)):
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
            if gemini_key and gemini_key.strip():
                translated_text, engine = translate_with_gemini_ai(
                    source_text,
                    source_info["name"],
                    target_info["name"],
                    gemini_key,
                    model_choice=selected_model
                )
            
            if not translated_text:
                translated_text, engine = smart_fallback_translate(
                    source_text,
                    source_info["code"],
                    target_info["code"]
                )

        if translated_text:
            is_gemini = "Gemini" in engine
            badge_class = "badge-gemini" if is_gemini else "badge-fallback"
            st.markdown(f"""
            <div class='output-card'>
                <span class='{badge_class}'>{get_text(src_code, 'engine_label')}: {engine}</span>
                <p style='margin-top: 10px; font-weight: bold; color: #4B5563;'>{get_text(src_code, 'output_label')}</p>
                <p style='font-size: 1.4rem; color: #047857; font-weight: 700; margin-top: 5px;'>{translated_text}</p>
            </div>
            """, unsafe_allow_html=True)

            if not is_gemini:
                st.caption("⚠️ हे भाषांतर बेसिक फॉलबॅक इंजिनद्वारे झाले आहे. 100% अचूक बोलीभाषा व संदर्भासाठी सेटिंग्जमध्ये **Gemini API Key** प्रविष्ट करा.")

            with st.spinner(get_text(src_code, "generating_voice")):
                raw_audio, v_engine = generate_natural_voice(translated_text, target_info["code"], gender_key)

            if raw_audio:
                opus_audio = convert_to_whatsapp_opus(raw_audio)
                preview_audio = opus_audio if opus_audio else raw_audio
                mime_type = "audio/ogg" if opus_audio else "audio/mp3"

                st.write("")
                st.markdown(f"<span class='badge-voice'>{get_text(src_code, 'voice_label')}: {v_engine}</span>", unsafe_allow_html=True)
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
