"""Tests for utils/validators.py"""
import pytest

from utils.exceptions import TranslatorAppError, ValidationError
from utils.validators import MAX_TRANSLATION_CHARS, validate_language_pair, validate_text


@pytest.mark.parametrize("bad", [None, "", "   ", "\n\t"])
def test_empty_text_rejected(bad):
    with pytest.raises(ValidationError):
        validate_text(bad)


def test_text_is_stripped():
    assert validate_text("  hello  ") == "hello"


def test_too_long_rejected():
    with pytest.raises(ValidationError):
        validate_text("a" * (MAX_TRANSLATION_CHARS + 1))


def test_exactly_max_allowed():
    assert len(validate_text("a" * MAX_TRANSLATION_CHARS)) == MAX_TRANSLATION_CHARS


def test_same_language_rejected():
    with pytest.raises(ValidationError):
        validate_language_pair("en", "en")


def test_auto_and_different_languages_allowed():
    validate_language_pair("auto", "en")
    validate_language_pair("en", "hi")


def test_validation_error_is_app_error():
    # The UI catches the base class, so subclasses must inherit from it.
    assert issubclass(ValidationError, TranslatorAppError)
