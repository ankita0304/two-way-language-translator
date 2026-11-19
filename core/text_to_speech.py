"""
core/text_to_speech.py
----------------------
Text -> spoken audio (MP3) using gTTS.

IMPORTANT (be honest in interviews):
    gTTS (Google Text-to-Speech) is an UNOFFICIAL library that uses Google
    Translate's text-to-speech web endpoint. It is NOT the official Google
    Cloud Text-to-Speech API. It needs internet access and has no SLA.

We build the MP3 in memory (BytesIO) instead of saving a file. Why?
    - No temp files to clean up.
    - Safe when many users run the app at once (no file-name clashes).
    - Streamlit's st.audio() accepts raw bytes directly.
"""

from io import BytesIO

from gtts import gTTS
from gtts.tts import gTTSError

from core.languages import get_tts_code
from utils.exceptions import TranslatorAppError, TTSError
from utils.logger import get_logger
from utils.validators import validate_text

logger = get_logger(__name__)

# gTTS splits long text itself, but we still cap it to keep the app responsive.
MAX_TTS_CHARS = 3000


def synthesize(text: str, language: str, slow: bool = False, tts_backend=gTTS) -> bytes:
    """Convert `text` to MP3 audio bytes.

    Args:
        text:        what to say.
        language:    display name, e.g. "Hindi".
        slow:        speak more slowly (useful for language learners).
        tts_backend: injectable for tests (defaults to the real gTTS class).

    Raises:
        ValidationError: empty or too-long text.
        TTSError:        gTTS failed (usually network problems).
    """
    text = validate_text(text, max_chars=MAX_TTS_CHARS)
    lang_code = get_tts_code(language)

    try:
        buffer = BytesIO()
        tts_backend(text=text, lang=lang_code, slow=slow).write_to_fp(buffer)
        audio_bytes = buffer.getvalue()
    except TranslatorAppError:
        raise
    except gTTSError as exc:
        logger.error("gTTS error: %s", exc)
        raise TTSError("Could not generate audio. Check your internet connection.") from exc
    except (AssertionError, ValueError) as exc:
        # gTTS raises these for "no text to speak" or an unsupported language.
        logger.error("gTTS rejected the input: %s", exc)
        raise TTSError(f"Audio is not available for {language}.") from exc
    except Exception as exc:
        logger.exception("Unexpected TTS failure")
        raise TTSError() from exc

    if not audio_bytes:
        raise TTSError("The audio service returned nothing.")

    logger.info("Generated %d bytes of audio (%s)", len(audio_bytes), lang_code)
    return audio_bytes
