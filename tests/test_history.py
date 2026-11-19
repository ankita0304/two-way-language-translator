"""Tests for core/history.py"""
import csv
import io
import json

from core.history import (MAX_HISTORY_ENTRIES, add_entry, make_entry,
                          to_csv_bytes, to_json_bytes, to_text_bytes)


def sample(n=1, text="Hello", translated="ನಮಸ್ಕಾರ"):
    return make_entry("Text", "English", "Kannada", f"{text} {n}", translated)


def test_make_entry_fields():
    e = make_entry("Conversation", "English", "Hindi", "Hi", "नमस्ते", speaker="Speaker A")
    assert e.mode == "Conversation" and e.speaker == "Speaker A"
    assert len(e.timestamp) == 19   # "YYYY-MM-DD HH:MM:SS"


def test_history_is_capped():
    history = []
    for i in range(MAX_HISTORY_ENTRIES + 25):
        add_entry(history, sample(i))
    assert len(history) == MAX_HISTORY_ENTRIES
    assert history[-1].source_text.endswith(str(MAX_HISTORY_ENTRIES + 24))  # newest kept
    assert history[0].source_text.endswith("25")                              # oldest dropped


def test_csv_roundtrip_keeps_unicode():
    raw = to_csv_bytes([sample()])
    assert raw.startswith(b"\xef\xbb\xbf")                      # UTF-8 BOM for Excel
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    assert rows[0]["translated_text"] == "ನಮಸ್ಕಾರ"
    assert rows[0]["source_language"] == "English"


def test_csv_blocks_formula_injection():
    raw = to_csv_bytes([sample(translated="=HYPERLINK(\"http://evil\")")])
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    assert rows[0]["translated_text"].startswith("'=")


def test_csv_handles_commas_quotes_newlines():
    tricky = 'He said, "hi"\nsecond line'
    raw = to_csv_bytes([sample(translated=tricky)])
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    assert rows[0]["translated_text"] == tricky


def test_json_is_valid_and_readable():
    raw = to_json_bytes([sample()])
    assert "ನಮಸ್ಕಾರ" in raw.decode("utf-8")           # not escaped as \uXXXX
    assert json.loads(raw)[0]["target_language"] == "Kannada"


def test_text_export():
    e = make_entry("Conversation", "English", "Hindi", "Hi", "नमस्ते", speaker="Speaker A")
    text = to_text_bytes([e]).decode("utf-8")
    assert "Speaker A" in text and "Hi" in text and "नमस्ते" in text
    assert to_text_bytes([]) == b""


def test_empty_history_exports_do_not_crash():
    assert to_csv_bytes([]).decode("utf-8-sig").startswith("timestamp,")
    assert json.loads(to_json_bytes([])) == []
