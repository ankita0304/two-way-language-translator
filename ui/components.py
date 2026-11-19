"""
ui/components.py
----------------
Reusable Streamlit building blocks (header, language selector, result card,
chat bubble...). This file knows how to DRAW things, but it never calls
translation / speech services - that wiring lives in app.py.

SECURITY NOTE:
    We render some HTML with `unsafe_allow_html=True` for nicer styling. The text
    inside that HTML comes from users and from Google, so we ALWAYS pass it
    through `html.escape()` first. Otherwise someone could type <script> and
    run code in the page (an "XSS" attack).
"""

import html
from pathlib import Path

import streamlit as st

from core.languages import (
    AUTO_DETECT_LABEL,
    get_all_languages,
    get_language,
    get_language_names,
)

CSS_PATH = Path(__file__).parent / "styles.css"


def load_css(path: Path = CSS_PATH) -> None:
    """Read styles.css and inject it into the page (called once from app.py)."""
    st.markdown(f"<style>{path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def render_header() -> None:
    st.markdown(
        '<h1 class="app-title">Two-Way Language Translator</h1>'
        '<p class="app-subtitle">Type or speak in one language and hear it in another. '
        f"Supports {len(get_all_languages())} languages including Hindi, Kannada, Telugu, Tamil, "
        "Malayalam, Marathi and Bengali.</p>",
        unsafe_allow_html=True,
    )


def language_selector(on_swap) -> tuple[str, str]:
    """Draw  [From ▾]  [⇄]  [To ▾]  and return (source, target) display names.

    The selected values live in st.session_state under the keys 'src_lang' and
    'tgt_lang'. `on_swap` is the callback run when the swap button is clicked.
    """
    col_from, col_swap, col_to = st.columns([5, 1.2, 5], vertical_alignment="bottom")

    with col_from:
        source = st.selectbox("From", get_language_names(include_auto=True), key="src_lang")
    with col_swap:
        st.button(
            "⇄",
            key="swap_btn",
            on_click=on_swap,
            help="Swap languages",
            disabled=(source == AUTO_DETECT_LABEL),  # can't swap an 'auto-detect' source
            width="stretch",
        )
    with col_to:
        target = st.selectbox("To", get_language_names(), key="tgt_lang")

    return source, target


def _language_label(name: str) -> str:
    """'Kannada' -> 'ಕನ್ನಡ' + 'Kannada' (native script first)."""
    native = get_language(name).native_name
    safe_name = html.escape(name)
    if native == name:
        return f"{safe_name}"
    return f'{html.escape(native)}<span>{safe_name}</span>'


def _safe_multiline(text: str) -> str:
    """Escape HTML and keep line breaks. Single line on purpose (see markdown note below)."""
    return html.escape(text).replace("\n", "<br>")


def render_result(result: dict) -> None:
    """Show a translation result: card + audio player + copy box.

    `result` is a dict with keys: translated, target, audio (bytes | None),
    audio_warning (str | None), and optionally 'heard' (voice mode).
    """
    # NOTE: the HTML is built on ONE line. Markdown treats indented / blank-line
    # separated text as code blocks, which would break our card.
    st.markdown(
        '<div class="result-card">'
        f'<div class="result-lang">{_language_label(result["target"])}</div>'
        f'<div class="result-text" dir="auto">{_safe_multiline(result["translated"])}</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    if result.get("audio"):
        st.audio(result["audio"], format="audio/mpeg")
    elif result.get("audio_warning"):
        st.warning(f"Translation succeeded, but audio is unavailable: {result['audio_warning']}")

    # st.code has a built-in copy-to-clipboard button.
    with st.expander("Copy text"):
        st.code(result["translated"], language=None, wrap_lines=True)


def render_heard(text: str, language: str) -> None:
    """Voice mode: show what the speech recogniser heard."""
    st.markdown(
        f'<p class="heard-text"><span class="heard-label">Heard ({html.escape(language)}):</span> '
        f'<span dir="auto">{html.escape(text)}</span></p>',
        unsafe_allow_html=True,
    )


def render_conversation_turn(turn: dict) -> None:
    """One chat bubble. Speaker A sits on the left, Speaker B on the right."""
    side = "left" if turn["speaker"] == "Speaker A" else "right"
    st.markdown(
        f'<div class="bubble-row {side}"><div class="bubble">'
        f'<div class="bubble-meta">{html.escape(turn["speaker"])} · {html.escape(turn["source_lang"])}</div>'
        f'<div class="bubble-src" dir="auto">{_safe_multiline(turn["source_text"])}</div>'
        f'<div class="bubble-out" dir="auto">{_safe_multiline(turn["translated"])}'
        "</div></div></div>",
        unsafe_allow_html=True,
    )
    if turn.get("audio"):
        st.audio(turn["audio"], format="audio/mpeg")
    elif turn.get("audio_warning"):
        st.caption(f"Audio unavailable: {turn['audio_warning']}")
