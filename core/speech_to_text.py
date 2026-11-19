"""
core/speech_to_text.py
----------------------
Spoken audio -> text using the `SpeechRecognition` library.

IMPORTANT (be honest in interviews):
    `recognize_google()` calls Google's FREE Web Speech endpoint with a shared
    default key. That is fine for demos and learning, but it is NOT the official
    Google Cloud Speech-to-Text API: it is rate-limited, has no SLA, and Google
    does not promise to keep it available.

Why we don't use sr.Microphone():
    It needs PyAudio and records from the SERVER's microphone, so it would break
    on Streamlit Cloud. Instead the browser records (st.audio_input) and sends
    us WAV bytes, which we read with sr.AudioFile - no PyAudio, no FFmpeg.
"""

from io import BytesIO

import speech_recognition as sr

from core.languages import get_speech_locale
from utils.exceptions import SpeechRecognitionError, TranslatorAppError
from utils.logger import get_logger

logger = get_logger(__name__)


def transcribe(audio_bytes: bytes, language: str, recognizer: sr.Recognizer | None = None) -> str:
    """Convert WAV audio bytes to text.

    Args:
        audio_bytes: raw WAV data (what st.audio_input(...).getvalue() returns).
        language:    display name of the language SPOKEN, e.g. "Kannada".
                     Auto-detect is not possible here - the recognizer must be told.
        recognizer:  injectable for tests.

    Raises:
        SpeechRecognitionError: empty audio, unreadable audio, speech not understood,
                                or the Google service being unreachable.
    """
    if not audio_bytes:
        raise SpeechRecognitionError("No audio was recorded. Please record again.")

    recognizer = recognizer or sr.Recognizer()
    locale = get_speech_locale(language)

    try:
        # sr.AudioFile accepts a file-like object, so we wrap the bytes in BytesIO.
        with sr.AudioFile(BytesIO(audio_bytes)) as source:
            # We deliberately skip adjust_for_ambient_noise(): it consumes the first
            # moments of the clip, which in a browser recording is usually speech.
            audio = recognizer.record(source)  # read the whole clip
    except (ValueError, EOFError) as exc:
        logger.error("Unreadable audio: %s", exc)
        raise SpeechRecognitionError(
            "The recording could not be read. Please try recording again."
        ) from exc

    try:
        text = recognizer.recognize_google(audio, language=locale)
    except sr.UnknownValueError:
        # Google received the audio but found no recognisable words.
        raise SpeechRecognitionError(
            "Could not understand the audio. Speak clearly and check the language selected."
        ) from None
    except sr.RequestError as exc:
        # Network failure, rate limit, or the service rejecting the request.
        logger.error("Speech service error: %s", exc)
        raise SpeechRecognitionError(
            "The speech service is unavailable. Check your internet connection and try again."
        ) from exc
    except TranslatorAppError:
        raise
    except Exception as exc:
        logger.exception("Unexpected speech-recognition failure")
        raise SpeechRecognitionError() from exc

    logger.info("Transcribed %d chars (%s)", len(text), locale)
    return text.strip()
