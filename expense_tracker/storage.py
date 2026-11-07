"""JSON persistence layer.

The data file looks like:
    {"next_id": 3, "expenses": [{"id": 1, "amount": "250.00", ...}, ...]}

Writes are atomic: data is written to a temporary file in the same folder
and then swapped in with os.replace, so a crash mid-write can never leave
a half-written (corrupt) data file behind.
"""

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import List, Tuple

from .exceptions import StorageError
from .models import Expense

ENV_VAR = "EXPENSE_TRACKER_FILE"


def default_path() -> Path:
    """Data file location: $EXPENSE_TRACKER_FILE, else <project>/data/expenses.json."""
    override = os.environ.get(ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parent.parent / "data" / "expenses.json"


def load(path: Path) -> Tuple[List[Expense], int]:
    """Return (expenses, next_id). A missing or empty file means a fresh start."""
    if not path.exists():
        return [], 1
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise StorageError(f"Cannot read data file '{path}': {exc}") from exc
    if not text.strip():
        return [], 1
    try:
        raw = json.loads(text)
        expenses = [Expense.from_dict(item) for item in raw["expenses"]]
        next_id = int(raw["next_id"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError, ArithmeticError) as exc:
        raise StorageError(
            f"Data file '{path}' is corrupted ({exc.__class__.__name__}). "
            "Fix or delete it; it has not been modified."
        ) from exc
    # Never hand out an ID that already exists, even if next_id was edited by hand.
    highest = max((e.id for e in expenses), default=0)
    return expenses, max(next_id, highest + 1)


def save(path: Path, expenses: List[Expense], next_id: int) -> None:
    """Atomically write all expenses to disk."""
    payload = {"next_id": next_id, "expenses": [e.to_dict() for e in expenses]}
    tmp_name = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        os.replace(tmp_name, path)
    except OSError as exc:
        if tmp_name:
            with contextlib.suppress(OSError):
                os.remove(tmp_name)
        raise StorageError(f"Cannot write data file '{path}': {exc}") from exc
