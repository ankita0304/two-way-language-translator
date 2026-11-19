
"""
core/languages.py
-----------------
The single source of truth for every language supported by the app.
"""

from dataclasses import dataclass

from utils.exceptions import UnsupportedLanguageError

AUTO_DETECT = "auto"
AUTO_DETECT_LABEL = "Auto-detect"


@dataclass(frozen=True)
class Language:
    name: str
    native_name: str
    translate_code: str
    tts_code: str
    speech_locale: str


# Languages supported by the local LibreTranslate models.
_LANGUAGES: list[Language] = [
    Language("English", "English", "en", "en", "en-IN"),
    Language("Hindi", "हिन्दी", "hi", "hi", "hi-IN"),
    Language("Bengali", "বাংলা", "bn", "bn", "bn-IN"),
    Language("Urdu", "اردو", "ur", "ur", "ur-IN"),
    Language("Arabic", "العربية", "ar", "ar", "ar-SA"),
    Language("French", "Français", "fr", "fr", "fr-FR"),
    Language("German", "Deutsch", "de", "de", "de-DE"),
    Language("Spanish", "Español", "es", "es", "es-ES"),
    Language("Italian", "Italiano", "it", "it", "it-IT"),
    Language("Russian", "Русский", "ru", "ru", "ru-RU"),
    Language("Japanese", "日本語", "ja", "ja", "ja-JP"),
]

_BY_NAME: dict[str, Language] = {
    lang.name: lang for lang in _LANGUAGES
}


def get_all_languages() -> list[Language]:
    """Return every supported Language, in display order."""
    return list(_LANGUAGES)


def get_language_names(include_auto: bool = False) -> list[str]:
    """Return display names for dropdowns."""
    names = [lang.name for lang in _LANGUAGES]
    return [AUTO_DETECT_LABEL] + names if include_auto else names


def get_language(name: str) -> Language:
    """Look up a Language by its display name."""
    try:
        return _BY_NAME[name]
    except KeyError:
        raise UnsupportedLanguageError(
            f"'{name}' is not a supported language."
        ) from None


def get_translate_code(name: str) -> str:
    """Display name to translation code."""
    if name == AUTO_DETECT_LABEL:
        return AUTO_DETECT
    return get_language(name).translate_code


def get_tts_code(name: str) -> str:
    """Display name to gTTS language code."""
    return get_language(name).tts_code


def get_speech_locale(name: str) -> str:
    """Display name to SpeechRecognition locale."""
    return get_language(name).speech_locale
