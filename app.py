"""
app.py - Streamlit entry point.
===============================
Run with:   streamlit run app.py

This file is the "glue": it draws the page, reads what the user did, calls the
services in core/, and stores results in st.session_state. It contains NO
translation / speech logic itself (that is in core/).

HOW STREAMLIT WORKS (important to explain in interviews):
    Every time the user clicks a button or changes a widget, Streamlit RE-RUNS
    this whole script from top to bottom. Normal Python variables are reset on
    each run, so anything we want to remember (history, last result, chat turns)
    goes into `st.session_state`, a dictionary that survives re-runs.

ABOUT THE GOOGLE SERVICES (be honest!):
    Translation, speech recognition and text-to-speech all use UNOFFICIAL, free
    Google web endpoints through the libraries deep-translator, SpeechRecognition
    and gTTS. They are NOT the official Google Cloud APIs.
"""

import hashlib

import streamlit as st

from core.history import (
    add_entry,
    make_entry,
    to_csv_bytes,
    to_json_bytes,
    to_text_bytes,
)
from core.languages import AUTO_DETECT_LABEL, get_language_names
from core.speech_to_text import transcribe
from core.text_to_speech import synthesize
from core.translator import Translator
from ui import components as ui
from utils.exceptions import TranslatorAppError
from utils.logger import get_logger
from utils.validators import MAX_TRANSLATION_CHARS

logger = get_logger(__name__)

# ---- Page setup (must be the first Streamlit call) -------------------------
st.set_page_config(page_title="Two-Way Language Translator", page_icon="🌐", layout="wide")

translator = Translator()  # one shared service object


# ============================================================================
# Session state
# ============================================================================
def init_state() -> None:
    """Create every session_state key once, with a default value."""
    defaults = {
        "src_lang": "English",
        "tgt_lang": "Hindi",
        "text_input": "",
        "text_result": None,       # last Text-mode result (dict) or None
        "voice_result": None,      # last Voice-mode result (dict) or None
        "voice_fingerprint": None, # identifies the last recording we processed
        "history": [],             # list[HistoryEntry]
        "conv_lang_a": "English",
        "conv_lang_b": "Hindi",
        "conv_speaker": "Speaker A",
        "conv_turns": [],          # list of chat-turn dicts
        "conv_fingerprint": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


# ============================================================================
# Shared helpers
# ============================================================================
def translate_and_speak(text: str, source: str, target: str) -> dict:
    """Translate `text`, then (optionally) generate audio of the translation.

    Translation errors are raised to the caller. Audio errors are NOT raised:
    a working translation should still be shown even if audio fails.
    """
    translated = translator.translate(text, source, target)

    audio, audio_warning = None, None
    if st.session_state.get("speak_enabled", True):
        try:
            audio = synthesize(translated, target, slow=st.session_state.get("slow_speech", False))
        except TranslatorAppError as exc:
            audio_warning = exc.user_message

    return {"translated": translated, "audio": audio, "audio_warning": audio_warning}


def fingerprint(audio_bytes: bytes, *context: str) -> str:
    """Hash of a recording + the settings used.

    st.audio_input keeps returning the SAME recording on every re-run. Without
    this hash we would translate it again (and again) on each click.
    """
    h = hashlib.sha1(audio_bytes)
    h.update("|".join(context).encode("utf-8"))
    return h.hexdigest()


def swap_languages() -> None:
    """Callback for the swap button: flip From/To (and move the output into the input box)."""
    state = st.session_state
    if state.src_lang == AUTO_DETECT_LABEL:
        return
    state.src_lang, state.tgt_lang = state.tgt_lang, state.src_lang
    if state.text_result:                      # make the translation the new input
        state.text_input = state.text_result["translated"]
        state.text_result = None


# ============================================================================
# Sidebar
# ============================================================================
def render_sidebar() -> None:
    with st.sidebar:
        st.header("Settings")
        st.toggle("Generate audio for translations", value=True, key="speak_enabled")
        st.toggle("Slow speech", value=False, key="slow_speech",
                  help="Speaks more slowly - useful when learning a language.")

        st.divider()
        st.subheader("About")
        st.caption(
            "Built with Python and Streamlit.\n\n"
            "Translation, speech recognition and text-to-speech use **unofficial, free** "
            "Google web endpoints via the `deep-translator`, `SpeechRecognition` and "
            "`gTTS` libraries. They are not the official Google Cloud APIs, have no "
            "uptime guarantee, and can be rate-limited."
        )


# ============================================================================
# Tab 1 - Text translation
# ============================================================================
def render_text_tab(source: str, target: str) -> None:
    st.text_area(
        "Text to translate",
        key="text_input",
        height=170,
        max_chars=MAX_TRANSLATION_CHARS,
        placeholder="Type or paste text here...",
    )

    if st.button("Translate", type="primary", key="translate_btn"):
        text = st.session_state.text_input
        try:
            with st.spinner("Translating..."):
                result = translate_and_speak(text, source, target)
            result.update(target=target, source_text=text)
            st.session_state.text_result = result
            add_entry(st.session_state.history,
                      make_entry("Text", source, target, text.strip(), result["translated"]))
        except TranslatorAppError as exc:
            st.session_state.text_result = None
            st.error(exc.user_message)

    if st.session_state.text_result:
        ui.render_result(st.session_state.text_result)


# ============================================================================
# Tab 2 - Voice translation
# ============================================================================
def render_voice_tab(source: str, target: str) -> None:
    if source == AUTO_DETECT_LABEL:
        st.info("Voice input needs to know which language you will speak. "
                "Choose a specific language in the **From** list above.")
        return

    st.caption(f"Click the microphone, speak in **{source}**, then click stop. "
               "Your browser will ask for microphone permission the first time.")
    recording = st.audio_input("Record your voice", key="voice_audio")

    if recording is not None:
        audio_bytes = recording.getvalue()
        # Only things that change the TRANSCRIPT/TRANSLATION belong in the fingerprint.
        # (Sidebar audio toggles are deliberately excluded so flipping them does not
        # re-send the same recording to the speech service.)
        fp = fingerprint(audio_bytes, source, target)

        if fp != st.session_state.voice_fingerprint:     # a NEW recording (or new settings)
            st.session_state.voice_fingerprint = fp
            try:
                with st.spinner("Listening and translating..."):
                    heard = transcribe(audio_bytes, source)           # 1. speech -> text
                    result = translate_and_speak(heard, source, target)  # 2. translate, 3. speak
                result.update(target=target, heard=heard, heard_language=source)
                st.session_state.voice_result = result
                add_entry(st.session_state.history,
                          make_entry("Voice", source, target, heard, result["translated"]))
            except TranslatorAppError as exc:
                st.session_state.voice_result = {"error": exc.user_message}
    else:
        st.session_state.voice_result = None
        st.session_state.voice_fingerprint = None

    result = st.session_state.voice_result
    if result:
        if "error" in result:
            st.error(result["error"])
        else:
            ui.render_heard(result["heard"], result["heard_language"])
            ui.render_result(result)


# ============================================================================
# Tab 3 - Conversation mode
# ============================================================================
def add_conversation_turn(text: str, speaker: str) -> None:
    """Translate one spoken/typed line into the OTHER speaker's language."""
    lang_a, lang_b = st.session_state.conv_lang_a, st.session_state.conv_lang_b
    source, target = (lang_a, lang_b) if speaker == "Speaker A" else (lang_b, lang_a)

    with st.spinner("Translating..."):
        result = translate_and_speak(text, source, target)

    st.session_state.conv_turns.append({
        "speaker": speaker, "source_lang": source, "target_lang": target,
        "source_text": text.strip(), **result,
    })
    add_entry(st.session_state.history,
              make_entry("Conversation", source, target, text.strip(), result["translated"], speaker))


def render_conversation_tab() -> None:
    names = get_language_names()
    col_a, col_b = st.columns(2)
    col_a.selectbox("Speaker A speaks", names, key="conv_lang_a")
    col_b.selectbox("Speaker B speaks", names, key="conv_lang_b")

    lang_a, lang_b = st.session_state.conv_lang_a, st.session_state.conv_lang_b
    if lang_a == lang_b:
        st.warning("Pick two different languages for the two speakers.")
        return

    # A container reserves the spot ABOVE the input for the chat. We fill it after
    # processing new input so a new message appears immediately.
    transcript = st.container()

    st.radio("Who is speaking?", ["Speaker A", "Speaker B"], horizontal=True, key="conv_speaker")
    speaker = st.session_state.conv_speaker
    speaker_lang = lang_a if speaker == "Speaker A" else lang_b

    # --- typed input (a form so Enter/click sends once and the box clears) ---
    with st.form("conversation_form", clear_on_submit=True):
        message = st.text_area(f"{speaker} - type in {speaker_lang}", height=90,
                               max_chars=MAX_TRANSLATION_CHARS)
        sent = st.form_submit_button("Send", type="primary")
    if sent:
        try:
            add_conversation_turn(message, speaker)
        except TranslatorAppError as exc:
            st.error(exc.user_message)

    # --- spoken input ---
    with st.expander(f"Or speak in {speaker_lang}"):
        recording = st.audio_input(f"{speaker} - record", key="conv_audio")
        if recording is not None:
            audio_bytes = recording.getvalue()
            # Identify the recording by its audio only. The widget keeps returning the same
            # recording on every re-run, so changing speaker/language must NOT replay it.
            fp = fingerprint(audio_bytes)
            if fp != st.session_state.conv_fingerprint:
                st.session_state.conv_fingerprint = fp
                try:
                    heard = transcribe(audio_bytes, speaker_lang)
                    add_conversation_turn(heard, speaker)
                except TranslatorAppError as exc:
                    st.error(exc.user_message)

    with transcript:
        if not st.session_state.conv_turns:
            st.info("No messages yet. Choose who is speaking, then type or record a message below.")
        for turn in st.session_state.conv_turns:
            ui.render_conversation_turn(turn)
        if st.session_state.conv_turns:
            if st.button("Clear conversation", key="clear_conv"):
                st.session_state.conv_turns = []
                st.rerun()


# ============================================================================
# Tab 4 - History + export
# ============================================================================
def render_history_tab() -> None:
    history = st.session_state.history
    if not history:
        st.info("Your translations will appear here. Nothing is stored on a server - "
                "history lasts only for this browser session.")
        return

    mode = st.segmented_control("Show", ["All", "Text", "Voice", "Conversation"],
                                default="All", key="history_filter") or "All"
    shown = [e for e in history if mode == "All" or e.mode == mode]

    # Newest first, as plain dicts so st.dataframe can display them.
    rows = [
        {"Time": e.timestamp, "Mode": e.mode, "Speaker": e.speaker,
         "From": e.source_language, "To": e.target_language,
         "Original": e.source_text, "Translation": e.translated_text}
        for e in reversed(shown)
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

    st.subheader("Export")
    c1, c2, c3, c4 = st.columns(4)
    # We export the whole history (not just the filtered view).
    c1.download_button("Download CSV", to_csv_bytes(history), "translation_history.csv",
                       "text/csv", width="stretch")
    c2.download_button("Download JSON", to_json_bytes(history), "translation_history.json",
                       "application/json", width="stretch")
    c3.download_button("Download TXT", to_text_bytes(history), "translation_history.txt",
                       "text/plain", width="stretch")
    if c4.button("Clear history", width="stretch", key="clear_history"):
        st.session_state.history = []
        st.rerun()


# ============================================================================
# Main
# ============================================================================
def main() -> None:
    init_state()
    ui.load_css()
    render_sidebar()
    ui.render_header()

    source, target = ui.language_selector(on_swap=swap_languages)

    tab_text, tab_voice, tab_conv, tab_history = st.tabs(
        ["Text", "Voice", "Conversation", "History"]
    )
    with tab_text:
        render_text_tab(source, target)
    with tab_voice:
        render_voice_tab(source, target)
    with tab_conv:
        render_conversation_tab()
    with tab_history:
        render_history_tab()


main()
