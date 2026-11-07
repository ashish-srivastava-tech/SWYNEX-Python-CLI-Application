"""Input validation helpers.

Each function takes raw text (as typed by the user) and either returns a
clean, correctly-typed value or raises ValidationError with a message that
explains what is wrong.
"""

import datetime as dt
import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from .exceptions import ValidationError

MAX_AMOUNT = Decimal("10000000")  # 1 crore - guards against typos like 5000000000
MAX_CATEGORY_LEN = 30
MAX_DESCRIPTION_LEN = 100

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_CATEGORY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 &\-]*$")


def parse_amount(raw: str) -> Decimal:
    """Return a positive Decimal with at most 2 decimal places.

    Rejected: empty text, non-numbers, NaN/Infinity (Decimal accepts these!),
    zero, negatives, more than 2 decimal places, values above MAX_AMOUNT.
    """
    text = (raw or "").strip().replace(",", "")
    if not text:
        raise ValidationError("Amount cannot be empty.")
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValidationError(f"Amount '{raw}' is not a valid number.") from None
    if not value.is_finite():
        raise ValidationError(f"Amount '{raw}' is not a finite number.")
    if value <= 0:
        raise ValidationError("Amount must be greater than zero.")
    if value.as_tuple().exponent < -2:
        raise ValidationError("Amount can have at most 2 decimal places.")
    if value > MAX_AMOUNT:
        raise ValidationError(f"Amount cannot exceed {MAX_AMOUNT:,}.")
    return value.quantize(Decimal("0.01"))


def parse_date(raw: Optional[str], today: Optional[dt.date] = None) -> dt.date:
    """Parse YYYY-MM-DD. Empty/None means today. Future dates are rejected."""
    today = today or dt.date.today()
    text = (raw or "").strip()
    if not text:
        return today
    # strptime alone would accept '2026-1-5'; the regex enforces zero-padding.
    if not _DATE_RE.match(text):
        raise ValidationError(f"Date '{raw}' must be in YYYY-MM-DD format.")
    try:
        value = dt.datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"Date '{raw}' does not exist in the calendar.") from None
    if value > today:
        raise ValidationError("Date cannot be in the future.")
    return value


def parse_month(raw: str) -> str:
    """Validate a YYYY-MM month filter and return it unchanged."""
    text = (raw or "").strip()
    if not _MONTH_RE.match(text):
        raise ValidationError(f"Month '{raw}' must be in YYYY-MM format.")
    month = int(text[5:])
    if not 1 <= month <= 12:
        raise ValidationError(f"Month '{text[5:]}' must be between 01 and 12.")
    return text


def validate_category(raw: str) -> str:
    """Normalise a category: collapse spaces, Title Case, max 30 chars."""
    text = " ".join((raw or "").split())
    if not text:
        raise ValidationError("Category cannot be empty.")
    if len(text) > MAX_CATEGORY_LEN:
        raise ValidationError(f"Category cannot exceed {MAX_CATEGORY_LEN} characters.")
    if not _CATEGORY_RE.match(text):
        raise ValidationError(
            "Category may contain only letters, digits, spaces, '&' and '-', "
            "and must start with a letter or digit."
        )
    return text.title()


def validate_description(raw: Optional[str]) -> str:
    """Trim an optional description; reject control characters and long text."""
    text = " ".join((raw or "").split())
    if len(text) > MAX_DESCRIPTION_LEN:
        raise ValidationError(f"Description cannot exceed {MAX_DESCRIPTION_LEN} characters.")
    if any(ord(ch) < 32 for ch in text):
        raise ValidationError("Description contains invalid control characters.")
    return text


def parse_id(raw: str) -> int:
    """Parse a positive integer expense ID."""
    text = (raw or "").strip()
    if not text.isdigit() or int(text) <= 0:
        raise ValidationError(f"ID '{raw}' must be a positive whole number.")
    return int(text)
