
"""
core/translator.py
------------------
Text translation service using the local LibreTranslate server.

An optional backend can be injected for testing.
"""

import re
import requests

from deep_translator.exceptions import (
    RequestError as BackendRequestError,
    TooManyRequests,
    TranslationNotFound,
)

from core.languages import get_translate_code
from utils.exceptions import TranslationError, TranslatorAppError
from utils.logger import get_logger
from utils.validators import validate_language_pair, validate_text

logger = get_logger(__name__)

CHUNK_SIZE = 4500
LIBRETRANSLATE_URL = "http://127.0.0.1:5000/translate"

_SENTENCE_END = re.compile(r"(?<=[.!?।॥])\s+")


def split_text(text: str, limit: int = CHUNK_SIZE) -> list[str]:
    """Split long text into smaller chunks."""

    if len(text) <= limit:
        return [text]

    chunks = []
    current = ""

    for sentence in _SENTENCE_END.split(text):

        while len(sentence) > limit:
            if current:
                chunks.append(current)
                current = ""

            chunks.append(sentence[:limit])
            sentence = sentence[limit:]

        if current and len(current) + 1 + len(sentence) > limit:
            chunks.append(current)
            current = sentence
        else:
            current = (
                f"{current} {sentence}".strip()
                if current
                else sentence
            )

    if current:
        chunks.append(current)

    return chunks


class Translator:
    """Translate text using LibreTranslate or an injected test backend."""

    def __init__(self, backend=None):
        self.backend = backend

    def translate(self, text: str, source: str, target: str) -> str:

        text = validate_text(text)

        source_code = get_translate_code(source)
        target_code = get_translate_code(target)

        validate_language_pair(source_code, target_code)

        try:
            parts = []

            backend_instance = None

            if self.backend is not None:
                backend_instance = self.backend(
                    source=source_code,
                    target=target_code,
                )

            for chunk in split_text(text):

                if backend_instance is not None:

                    translated_text = backend_instance.translate(chunk)

                else:

                    response = requests.post(
                        LIBRETRANSLATE_URL,
                        json={
                            "q": chunk,
                            "source": source_code,
                            "target": target_code,
                            "format": "text",
                        },
                        timeout=60,
                    )

                    response.raise_for_status()

                    data = response.json()
                    translated_text = data.get("translatedText")

                if not translated_text:
                    raise TranslationError(
                        "The translation service returned an empty result."
                    )

                parts.append(translated_text)

        except TooManyRequests as exc:
            logger.error("Translation backend rate limit reached: %s", exc)

            raise TranslationError(
                "Too many requests. Please wait and try again."
            ) from exc

        except TranslationNotFound as exc:
            logger.error("Translation not found: %s", exc)

            raise TranslationError(
                "The text could not be translated."
            ) from exc

        except BackendRequestError as exc:
            logger.error("Translation backend request failed: %s", exc)

            raise TranslationError(
                "Translation failed. Please check your internet connection."
            ) from exc

        except requests.exceptions.Timeout as exc:
            logger.error("Translation request timed out: %s", exc)

            raise TranslationError(
                "Translation failed. Please check your internet connection."
            ) from exc

        except requests.exceptions.ConnectionError as exc:
            logger.error("Translation connection failed: %s", exc)

            if self.backend is not None:
                message = (
                    "Translation failed. Please check your internet connection."
                )
            else:
                message = (
                    "Could not connect to LibreTranslate. "
                    "Make sure its server is running."
                )

            raise TranslationError(message) from exc

        except requests.exceptions.RequestException as exc:
            logger.error("LibreTranslate request failed: %s", exc)

            response = getattr(exc, "response", None)

            if response is not None:
                detail = response.text
                logger.error(
                    "LibreTranslate response: %s",
                    detail,
                )
            else:
                detail = str(exc)

            raise TranslationError(
                f"LibreTranslate error: {detail}"
            ) from exc

        except ConnectionError as exc:
            logger.error("Translation backend connection failed: %s", exc)

            raise TranslationError(
                "Translation failed. Please check your internet connection."
            ) from exc

        except TranslatorAppError:
            raise

        except Exception as exc:
            logger.exception("Unexpected translation failure")

            raise TranslationError() from exc

        result = " ".join(parts).strip()

        logger.info(
            "Translated %d chars: %s -> %s",
            len(text),
            source_code,
            target_code,
        )

        return result
