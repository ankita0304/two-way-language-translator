"""Tests for core/translator.py. A fake backend replaces Google, so no internet is needed."""
import pytest
import requests
from deep_translator.exceptions import RequestError, TooManyRequests, TranslationNotFound

from core.translator import CHUNK_SIZE, Translator, split_text
from utils.exceptions import TranslationError, UnsupportedLanguageError, ValidationError


class FakeBackend:
    """Stands in for GoogleTranslator: tags the text with the target code."""
    calls = []

    def __init__(self, source, target):
        self.source, self.target = source, target

    def translate(self, text):
        FakeBackend.calls.append((self.source, self.target, text))
        return f"[{self.target}] {text}"


def make_failing_backend(exc):
    class Failing:
        def __init__(self, source, target): pass
        def translate(self, text): raise exc
    return Failing


@pytest.fixture(autouse=True)
def reset_calls():
    FakeBackend.calls = []


def test_basic_translation():
    t = Translator(backend=FakeBackend)
    assert t.translate("Hello", "English", "Hindi") == "[hi] Hello"
    assert FakeBackend.calls == [("en", "hi", "Hello")]


def test_auto_detect_source_passes_auto():
    Translator(backend=FakeBackend).translate("Bonjour", "Auto-detect", "English")
    assert FakeBackend.calls[0][0] == "auto"


def test_input_is_stripped():
    assert Translator(backend=FakeBackend).translate("  Hi  ", "English", "Hindi") == "[hi] Hi"


def test_empty_text_rejected():
    with pytest.raises(ValidationError):
        Translator(backend=FakeBackend).translate("   ", "English", "Hindi")


def test_same_language_rejected():
    with pytest.raises(ValidationError):
        Translator(backend=FakeBackend).translate("Hi", "English", "English")


def test_unknown_language_rejected():
    with pytest.raises(UnsupportedLanguageError):
        Translator(backend=FakeBackend).translate("Hi", "English", "Klingon")


def test_long_text_is_chunked_and_rejoined():
    sentence = "This is a sentence. "
    chunks = split_text(sentence * 600, limit=1000)
    assert all(len(c) <= 1000 for c in chunks)
    assert len(chunks) > 1
    # Nothing lost: joining chunks gives back the same words.
    assert " ".join(chunks).split() == (sentence * 600).split()


def test_translate_sends_long_text_in_several_requests():
    """4900 chars is valid input (< 5000) but above CHUNK_SIZE, so it needs 2 requests."""
    text = ("This is a sentence. " * 245).strip()          # ~4899 chars
    assert CHUNK_SIZE < len(text) < 5000
    result = Translator(backend=FakeBackend).translate(text, "English", "Hindi")
    assert len(FakeBackend.calls) == 2
    assert result.count("[hi]") == 2


def test_short_text_not_split():
    assert split_text("Hello world.") == ["Hello world."]


def test_single_huge_sentence_is_hard_cut():
    chunks = split_text("a" * 2500, limit=1000)
    assert [len(c) for c in chunks] == [1000, 1000, 500]


def test_hindi_danda_is_a_sentence_boundary():
    text = ("नमस्ते। " * 300).strip()
    chunks = split_text(text, limit=500)
    assert all(len(c) <= 500 for c in chunks)
    assert all(c.endswith("।") for c in chunks)   # cut cleanly at sentence ends


@pytest.mark.parametrize("exc, expected_fragment", [
    (TooManyRequests(), "Too many requests"),
    (RequestError(), "internet"),
    (ConnectionError("down"), "internet"),
    (requests.exceptions.ConnectionError("dns failure"), "internet"),   # real-world case
    (requests.exceptions.Timeout("slow"), "internet"),
    (TranslationNotFound("x"), "could not be translated"),
    (RuntimeError("boom"), "Translation failed"),
])
def test_library_errors_become_translation_error(exc, expected_fragment):
    t = Translator(backend=make_failing_backend(exc))
    with pytest.raises(TranslationError) as info:
        t.translate("Hello", "English", "Hindi")
    assert expected_fragment in info.value.user_message


def test_none_result_is_an_error():
    class ReturnsNone:
        def __init__(self, source, target): pass
        def translate(self, text): return None
    with pytest.raises(TranslationError):
        Translator(backend=ReturnsNone).translate("Hello", "English", "Hindi")


def test_chunk_size_below_service_limit():
    assert CHUNK_SIZE < 5000
