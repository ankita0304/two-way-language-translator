"""Tests for core/languages.py. Run with:  pytest tests/ -v"""
import pytest
from deep_translator import GoogleTranslator
from gtts.lang import tts_langs

from core.languages import (
    AUTO_DETECT, AUTO_DETECT_LABEL, get_all_languages, get_language,
    get_language_names, get_speech_locale, get_translate_code, get_tts_code,
)
from utils.exceptions import UnsupportedLanguageError

REQUIRED = [
    "English",
    "Hindi",
    "Bengali",
    "Urdu",
    "Arabic",
    "French",
    "German",
    "Spanish",
    "Italian",
    "Russian",
    "Japanese",
]


def test_required_languages_present():
    names = get_language_names()
    for lang in REQUIRED:
        assert lang in names


def test_names_are_unique():
    names = get_language_names()
    assert len(names) == len(set(names))


def test_auto_detect_only_in_source_list():
    assert get_language_names(include_auto=True)[0] == AUTO_DETECT_LABEL
    assert AUTO_DETECT_LABEL not in get_language_names()
    assert get_translate_code(AUTO_DETECT_LABEL) == AUTO_DETECT

def test_code_lookups():
    assert get_translate_code("Hindi") == "hi"
    assert get_translate_code("Bengali") == "bn"
    assert get_tts_code("Japanese") == "ja"
    assert get_speech_locale("Arabic") == "ar-SA"


def test_unknown_language_raises():
    with pytest.raises(UnsupportedLanguageError):
        get_language("Klingon")


@pytest.mark.parametrize("lang", get_all_languages(), ids=lambda l: l.name)
def test_codes_are_accepted_by_the_libraries(lang):
    """Guards against typos: every code must exist in the libraries' own tables.
    Both tables are bundled locally, so this test needs no internet."""
    translate_codes = set(GoogleTranslator().get_supported_languages(as_dict=True).values())
    assert lang.translate_code in translate_codes
    assert lang.tts_code in tts_langs()


@pytest.mark.parametrize("lang", get_all_languages(), ids=lambda l: l.name)
def test_speech_locale_format(lang):
    # BCP-47 style: language-REGION, e.g. "kn-IN"
    assert "-" in lang.speech_locale
