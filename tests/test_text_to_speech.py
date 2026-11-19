"""Tests for core/text_to_speech.py using a fake gTTS (offline)."""
import pytest
from gtts.tts import gTTSError

from core.text_to_speech import MAX_TTS_CHARS, synthesize
from utils.exceptions import TTSError, UnsupportedLanguageError, ValidationError


class FakeTTS:
    last = None

    def __init__(self, text, lang, slow=False):
        FakeTTS.last = {"text": text, "lang": lang, "slow": slow}

    def write_to_fp(self, fp):
        fp.write(b"ID3-fake-mp3-bytes")

def test_returns_audio_bytes_and_uses_right_language():
    audio = synthesize("नमस्ते", "Hindi", tts_backend=FakeTTS)
    assert audio == b"ID3-fake-mp3-bytes"
    assert FakeTTS.last["lang"] == "hi"
    assert FakeTTS.last["slow"] is False


def test_slow_flag_is_forwarded():
    synthesize("Hello", "English", slow=True, tts_backend=FakeTTS)
    assert FakeTTS.last["slow"] is True


def test_empty_and_too_long_text_rejected():
    with pytest.raises(ValidationError):
        synthesize("  ", "English", tts_backend=FakeTTS)
    with pytest.raises(ValidationError):
        synthesize("a" * (MAX_TTS_CHARS + 1), "English", tts_backend=FakeTTS)


def test_unknown_language_rejected():
    with pytest.raises(UnsupportedLanguageError):
        synthesize("Hi", "Klingon", tts_backend=FakeTTS)


def test_network_failure_becomes_tts_error():
    class Broken:
        def __init__(self, **kw): pass
        def write_to_fp(self, fp): raise gTTSError("offline")
    with pytest.raises(TTSError) as info:
        synthesize("Hi", "English", tts_backend=Broken)
    assert "internet" in info.value.user_message


def test_assertion_error_becomes_tts_error():
    class Rejects:
        def __init__(self, **kw): pass
        def write_to_fp(self, fp): raise AssertionError("No text to speak")
    with pytest.raises(TTSError):
        synthesize("Hi", "English", tts_backend=Rejects)


def test_empty_audio_is_an_error():
    class Silent:
        def __init__(self, **kw): pass
        def write_to_fp(self, fp): pass
    with pytest.raises(TTSError):
        synthesize("Hi", "English", tts_backend=Silent)
