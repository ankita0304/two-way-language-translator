"""
core/history.py
---------------
Translation history: a small data model plus export helpers (CSV / JSON / TXT).

This file contains NO Streamlit code. The app keeps the list of entries in
`st.session_state`, and uses these functions to create and export them.
Keeping it UI-free makes it easy to unit-test.
"""

import csv
import io
import json
from dataclasses import asdict, dataclass
from datetime import datetime

# Keep memory bounded: Streamlit stores session data in server RAM.
MAX_HISTORY_ENTRIES = 200

# Column order used for CSV export.
FIELDS = ["timestamp", "mode", "speaker", "source_language", "target_language",
          "source_text", "translated_text"]


@dataclass
class HistoryEntry:
    """One translation, from any of the three modes."""
    timestamp: str
    mode: str               # "Text", "Voice" or "Conversation"
    source_language: str
    target_language: str
    source_text: str
    translated_text: str
    speaker: str = ""       # only used in Conversation mode ("Speaker A" / "Speaker B")


def make_entry(mode: str, source_language: str, target_language: str,
               source_text: str, translated_text: str, speaker: str = "") -> HistoryEntry:
    """Create an entry stamped with the current time."""
    return HistoryEntry(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        mode=mode,
        source_language=source_language,
        target_language=target_language,
        source_text=source_text,
        translated_text=translated_text,
        speaker=speaker,
    )


def add_entry(history: list[HistoryEntry], entry: HistoryEntry,
              max_entries: int = MAX_HISTORY_ENTRIES) -> None:
    """Append `entry`, dropping the oldest ones if the list grows too long."""
    history.append(entry)
    del history[:-max_entries]   # keeps only the last `max_entries` items


def _csv_safe(value: str) -> str:
    """Protect against CSV/formula injection.

    If a cell starts with = + - or @, Excel may treat it as a formula. Since
    translated text is outside our control, we prefix such cells with an
    apostrophe, which is the standard mitigation (recommended by OWASP).
    """
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def to_csv_bytes(history: list[HistoryEntry]) -> bytes:
    """CSV file contents. Encoded as UTF-8 *with BOM* so Excel shows Hindi,
    Kannada, etc. correctly instead of garbled characters."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS)
    writer.writeheader()
    for entry in history:
        row = {key: _csv_safe(str(value)) for key, value in asdict(entry).items()}
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8-sig")


def to_json_bytes(history: list[HistoryEntry]) -> bytes:
    """JSON file contents. ensure_ascii=False keeps Indian scripts readable."""
    data = [asdict(entry) for entry in history]
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def to_text_bytes(history: list[HistoryEntry]) -> bytes:
    """A human-readable transcript, good for conversation export."""
    if not history:
        return b""
    blocks = []
    for e in history:
        who = f"{e.speaker} - " if e.speaker else ""
        blocks.append(
            f"[{e.timestamp}] {who}{e.mode}: {e.source_language} -> {e.target_language}\n"
            f"  {e.source_text}\n"
            f"  => {e.translated_text}"
        )
    return ("\n\n".join(blocks) + "\n").encode("utf-8")
