"""Tests for core/speech_to_text.py.

We generate a REAL (silent) WAV file so sr.AudioFile parsing is genuinely
exercised, and only fake the network call to Google (recognize_google).
"""
import io
import wave

import pytest
import speech_recognition as sr

from core.speech_to_text import transcribe
from utils.exceptions import SpeechRecognitionError


def make_wav(seconds: float = 1.0, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)          # 16-bit
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return buf.getvalue()


class FakeRecognizer(sr.Recognizer):
    """Real Recognizer (so .record() works) with only the Google call replaced."""
    def __init__(self, result=None, error=None):
        super().__init__()
        self.result, self.error, self.seen_language = result, error, None

    def recognize_google(self, audio, language="en-US", **kw):
        self.seen_language = language
        if self.error:
            raise self.error
        return self.result


def test_successful_transcription_uses_right_locale():
    rec = FakeRecognizer(result="  namaste  ")
    assert transcribe(make_wav(), "Hindi", recognizer=rec) == "namaste"
    assert rec.seen_language == "hi-IN"


def test_empty_audio_rejected():
    with pytest.raises(SpeechRecognitionError):
        transcribe(b"", "English")


def test_garbage_bytes_rejected():
    with pytest.raises(SpeechRecognitionError) as info:
        transcribe(b"this is not audio at all", "English")
    assert "could not be read" in info.value.user_message


def test_unintelligible_speech():
    rec = FakeRecognizer(error=sr.UnknownValueError())
    with pytest.raises(SpeechRecognitionError) as info:
        transcribe(make_wav(), "English", recognizer=rec)
    assert "understand" in info.value.user_message


def test_service_unavailable():
    rec = FakeRecognizer(error=sr.RequestError("no network"))
    with pytest.raises(SpeechRecognitionError) as info:
        transcribe(make_wav(), "English", recognizer=rec)
    assert "unavailable" in info.value.user_message


def test_unexpected_error_is_wrapped():
    rec = FakeRecognizer(error=RuntimeError("boom"))
    with pytest.raises(SpeechRecognitionError):
        transcribe(make_wav(), "English", recognizer=rec)
