"""
utils/exceptions.py
-------------------
Custom exception classes for the project.

WHY custom exceptions?
    Libraries like deep-translator, gTTS and SpeechRecognition each raise their
    OWN error types. If the UI had to know about all of them, it would be tightly
    coupled to those libraries. Instead, each core module catches the library
    errors and re-raises ONE of the classes below. The UI only needs to catch
    `TranslatorAppError` to show a friendly message.

    (Interview tip: this is called "exception translation" or "wrapping" and
    keeps layers loosely coupled.)
"""


class TranslatorAppError(Exception):
    """Base class for every error raised by this application.

    `user_message` is a short, friendly text that is safe to show in the UI.
    """

    default_message = "Something went wrong. Please try again."

    def __init__(self, user_message: str | None = None):
        self.user_message = user_message or self.default_message
        super().__init__(self.user_message)


class ValidationError(TranslatorAppError):
    """The user's input is invalid (empty text, too long, etc.)."""

    default_message = "The input is not valid."


class UnsupportedLanguageError(TranslatorAppError):
    """A language name/code is not in our language registry."""

    default_message = "This language is not supported."


class TranslationError(TranslatorAppError):
    """Translation failed (network issue, rate limit, bad response...)."""

    default_message = "Translation failed. Please check your internet connection and try again."


class SpeechRecognitionError(TranslatorAppError):
    """Speech could not be converted to text."""

    default_message = "Could not convert your speech to text."


class TTSError(TranslatorAppError):
    """Text-to-speech audio generation failed."""

    default_message = "Could not generate audio for this text."
