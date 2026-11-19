"""
End-to-end tests of the Streamlit app using Streamlit's built-in AppTest.

AppTest runs app.py headlessly (no browser) and lets us click buttons and read
the page. The network-dependent services are replaced with fakes, so these tests
run offline and fast.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from utils.exceptions import SpeechRecognitionError, TranslationError, TTSError

APP_FILE = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def fake_services(monkeypatch):
    """Replace translate / TTS / STT with offline fakes."""
    import core.speech_to_text, core.text_to_speech, core.translator

    from utils.validators import validate_text

    def fake_translate(self, text, source, target):
        # Mirror the real contract: validate first, then "translate".
        return f"[{target}] {validate_text(text)}"

    monkeypatch.setattr(core.translator.Translator, "translate", fake_translate)
    monkeypatch.setattr(core.text_to_speech, "synthesize",
                        lambda text, language, slow=False, **kw: b"fake-mp3")
    monkeypatch.setattr(core.speech_to_text, "transcribe",
                        lambda audio, language, **kw: "hello there")


def new_app() -> AppTest:
    return AppTest.from_file(APP_FILE, default_timeout=15).run()


def all_markdown(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def test_app_starts_without_errors(fake_services):
    at = new_app()
    assert not at.exception
    assert at.session_state.src_lang == "English"
    assert at.session_state.tgt_lang == "Hindi"


def test_text_translation_flow_and_history(fake_services):
    at = new_app()
    at.text_area(key="text_input").set_value("Good morning")
    at.button(key="translate_btn").click().run()

    assert not at.exception
    assert "[Hindi] Good morning" in all_markdown(at)
    assert at.session_state.text_result["audio"] == b"fake-mp3"
    history = at.session_state.history
    assert len(history) == 1 and history[0].mode == "Text"
    assert history[0].source_language == "English"


def test_empty_text_shows_friendly_error(fake_services):
    at = new_app()
    at.button(key="translate_btn").click().run()
    assert not at.exception
    assert any("enter some text" in e.value for e in at.error)
    assert at.session_state.history == []


def test_same_language_shows_error(monkeypatch):
    # Uses the REAL Translator: validation fails before any network call.
    at = new_app()
    at.selectbox(key="tgt_lang").select("English").run()
    at.text_area(key="text_input").set_value("Hello")
    at.button(key="translate_btn").click().run()
    assert any("same" in e.value for e in at.error)


def test_translation_failure_is_shown_not_crashed(monkeypatch):
    import core.translator

    def boom(self, text, source, target):
        raise TranslationError()
    monkeypatch.setattr(core.translator.Translator, "translate", boom)

    at = new_app()
    at.text_area(key="text_input").set_value("Hello")
    at.button(key="translate_btn").click().run()
    assert not at.exception
    assert any("Translation failed" in e.value for e in at.error)


def test_tts_failure_keeps_translation(monkeypatch, fake_services):
    import core.text_to_speech

    def no_audio(text, language, slow=False, **kw):
        raise TTSError("Could not generate audio.")
    monkeypatch.setattr(core.text_to_speech, "synthesize", no_audio)

    at = new_app()
    at.text_area(key="text_input").set_value("Hello")
    at.button(key="translate_btn").click().run()
    assert not at.exception
    assert "[Hindi] Hello" in all_markdown(at)           # translation still shown
    assert any("audio is unavailable" in w.value for w in at.warning)


def test_swap_moves_translation_into_input(fake_services):
    at = new_app()
    at.text_area(key="text_input").set_value("Hello")
    at.button(key="translate_btn").click().run()
    at.button(key="swap_btn").click().run()

    assert at.session_state.src_lang == "Hindi"
    assert at.session_state.tgt_lang == "English"
    assert at.session_state.text_input == "[Hindi] Hello"
    assert at.session_state.text_result is None


def test_swap_disabled_for_auto_detect(fake_services):
    at = new_app()
    at.selectbox(key="src_lang").select("Auto-detect").run()
    assert at.button(key="swap_btn").disabled


def test_html_in_translation_is_escaped(monkeypatch):
    """XSS check: a <script> tag in the output must be escaped in the HTML card."""
    import core.translator
    monkeypatch.setattr(core.translator.Translator, "translate",
                        lambda self, t, s, tg: "<script>alert(1)</script>")
    at = new_app()
    at.text_area(key="text_input").set_value("x")
    at.button(key="translate_btn").click().run()
    md = all_markdown(at)
    assert "<script>" not in md
    assert "&lt;script&gt;" in md


SEND = "FormSubmitter:conversation_form-Send"


def send_chat_message(at: AppTest, text: str) -> AppTest:
    """The chat box is the second text area (the first belongs to the Text tab)."""
    at.text_area[1].set_value(text)
    return at.button(key=SEND).click().run()


def test_conversation_translates_into_the_other_speakers_language(fake_services):
    at = new_app()                       # defaults: A = English, B = Hindi
    at = send_chat_message(at, "How are you?")
    assert not at.exception

    turn = at.session_state.conv_turns[0]
    assert turn["speaker"] == "Speaker A"
    assert (turn["source_lang"], turn["target_lang"]) == ("English", "Hindi")
    assert turn["translated"] == "[Hindi] How are you?"

    # Now Speaker B replies: direction must flip to Hindi -> English.
    at.radio(key="conv_speaker").set_value("Speaker B").run()
    at = send_chat_message(at, "I am fine")
    turn_b = at.session_state.conv_turns[1]
    assert (turn_b["source_lang"], turn_b["target_lang"]) == ("Hindi", "English")

    history = at.session_state.history
    assert [h.speaker for h in history] == ["Speaker A", "Speaker B"]
    assert all(h.mode == "Conversation" for h in history)


def test_conversation_same_language_warns(fake_services):
    at = new_app()
    at.selectbox(key="conv_lang_b").select("English").run()
    assert not at.exception
    assert any("two different languages" in w.value for w in at.warning)


def test_conversation_empty_message_shows_error(fake_services):
    at = new_app()
    at = send_chat_message(at, "   ")
    assert any("enter some text" in e.value for e in at.error)
    assert at.session_state.conv_turns == []


def test_voice_tab_needs_specific_language_for_auto_detect(fake_services):
    at = new_app()
    at.selectbox(key="src_lang").select("Auto-detect").run()
    assert any("which language you will speak" in i.value for i in at.info)


def test_history_tab_shows_entries_after_translation(fake_services):
    at = new_app()
    at.text_area(key="text_input").set_value("Thanks")
    at.button(key="translate_btn").click().run()
    assert not at.exception
    assert len(at.dataframe) == 1


def test_clear_history(fake_services):
    at = new_app()
    at.text_area(key="text_input").set_value("Thanks")
    at.button(key="translate_btn").click().run()
    at.button(key="clear_history").click().run()
    assert at.session_state.history == []


# ---------------------------------------------------------------------------
# Voice flow. AppTest cannot record from a microphone, so we replace
# st.audio_input with a stub that returns a fake recording.
# ---------------------------------------------------------------------------
class FakeRecording:
    def __init__(self, data=b"RIFFfakewav"):
        self._data = data

    def getvalue(self):
        return self._data


@pytest.fixture
def with_recording(monkeypatch):
    """Make every st.audio_input call return a fake recording."""
    import streamlit
    monkeypatch.setattr(streamlit, "audio_input", lambda *a, **k: FakeRecording())


def test_voice_pipeline_transcribe_translate_speak(fake_services, with_recording):
    at = new_app()
    assert not at.exception
    result = at.session_state.voice_result
    assert result["heard"] == "hello there"
    assert result["translated"] == "[Hindi] hello there"
    assert result["audio"] == b"fake-mp3"
    assert at.session_state.history[0].mode == "Voice"


def test_same_recording_is_processed_only_once(monkeypatch, fake_services, with_recording):
    import core.speech_to_text
    calls = []

    def counting(audio, language, **kw):
        calls.append(language)
        return "hello there"
    monkeypatch.setattr(core.speech_to_text, "transcribe", counting)

    at = new_app()
    # First run: Voice tab (English) + Conversation tab (Speaker A = English) each transcribe once.
    assert calls == ["English", "English"]

    at.toggle(key="slow_speech").set_value(True).run()    # unrelated re-run
    at.radio(key="conv_speaker").set_value("Speaker A").run()
    assert calls == ["English", "English"]                # nothing re-processed

    at.button(key="swap_btn").click().run()               # languages change => voice tab re-processes
    assert calls == ["English", "English", "Hindi"]
    assert len(at.session_state.history) == 3


def test_voice_recognition_error_is_displayed(monkeypatch, fake_services, with_recording):
    import core.speech_to_text

    def cannot_hear(audio, language, **kw):
        raise SpeechRecognitionError("Could not understand the audio.")
    monkeypatch.setattr(core.speech_to_text, "transcribe", cannot_hear)

    at = new_app()
    assert not at.exception
    assert any("Could not understand" in e.value for e in at.error)
    assert at.session_state.history == []


def test_conversation_voice_input(fake_services, with_recording):
    at = new_app()
    turns = at.session_state.conv_turns
    assert len(turns) == 1
    assert turns[0]["source_text"] == "hello there"
    assert turns[0]["translated"] == "[Hindi] hello there"


def test_switching_speaker_does_not_replay_old_recording(fake_services, with_recording):
    """Regression: the recording stays in the widget; changing the speaker must not re-send it."""
    at = new_app()
    assert len(at.session_state.conv_turns) == 1
    at.radio(key="conv_speaker").set_value("Speaker B").run()
    assert len(at.session_state.conv_turns) == 1          # still just the original turn
    assert at.session_state.conv_turns[0]["speaker"] == "Speaker A"
