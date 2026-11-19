"""
utils/validators.py
-------------------
Small input checks that run BEFORE we call any external service.
Failing fast here saves a network call and gives the user a clear message.
"""

from utils.exceptions import ValidationError

# Google Translate's free web endpoint rejects very long requests.
# deep-translator documents a limit of 5000 characters per request.
MAX_TRANSLATION_CHARS = 5000


def validate_text(text: str | None, max_chars: int = MAX_TRANSLATION_CHARS) -> str:
    """Check that `text` is non-empty and not too long.

    Returns the cleaned (stripped) text so callers can use it directly.
    Raises ValidationError with a friendly message otherwise.
    """
    if text is None or not text.strip():
        raise ValidationError("Please enter some text first.")

    cleaned = text.strip()

    if len(cleaned) > max_chars:
        raise ValidationError(
            f"Text is too long ({len(cleaned)} characters). "
            f"The limit is {max_chars} characters."
        )
    return cleaned


def validate_language_pair(source: str, target: str) -> None:
    """Make sure source and target are different (auto-detect is always allowed)."""
    if source != "auto" and source == target:
        raise ValidationError(
            "Source and target languages are the same. Please pick two different languages."
        )
