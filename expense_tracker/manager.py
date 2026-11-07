"""Business logic: add, delete, list, summarise and export expenses.

ExpenseManager accepts RAW user text and validates it itself, so no caller
(CLI, tests, a future GUI) can bypass validation.
"""

import csv
import datetime as dt
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from . import storage
from .exceptions import ExpenseNotFoundError, ExportError
from .models import Expense
from .validators import (
    parse_amount,
    parse_date,
    parse_month,
    validate_category,
    validate_description,
)

_CSV_HEADER = ["id", "date", "category", "amount", "description"]
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _csv_safe(text: str) -> str:
    """Neutralise spreadsheet formula injection (e.g. a description '=2+2')."""
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


class ExpenseManager:
    def __init__(self, path: Optional[Union[str, Path]] = None) -> None:
        self.path = Path(path) if path else storage.default_path()
        self._expenses, self._next_id = storage.load(self.path)

    # ---------------------------------------------------------------- create
    def add(
        self,
        amount: str,
        category: str,
        date: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Expense:
        expense = Expense(
            id=self._next_id,
            amount=parse_amount(amount),
            category=validate_category(category),
            date=parse_date(date),
            description=validate_description(description),
        )
        updated = self._expenses + [expense]
        # Save first: if writing fails, in-memory state stays consistent with disk.
        storage.save(self.path, updated, self._next_id + 1)
        self._expenses = updated
        self._next_id += 1
        return expense

    # ---------------------------------------------------------------- delete
    def delete(self, expense_id: int) -> Expense:
        for item in self._expenses:
            if item.id == expense_id:
                updated = [e for e in self._expenses if e.id != expense_id]
                storage.save(self.path, updated, self._next_id)
                self._expenses = updated
                return item
        raise ExpenseNotFoundError(f"No expense found with ID {expense_id}.")

    # ------------------------------------------------------------------ read
    def list_expenses(
        self, category: Optional[str] = None, month: Optional[str] = None
    ) -> List[Expense]:
        """Return expenses oldest-first, optionally filtered by category/month."""
        wanted_category = validate_category(category) if category else None
        wanted_month = parse_month(month) if month else None
        result = [
            e
            for e in self._expenses
            if (wanted_category is None or e.category == wanted_category)
            and (wanted_month is None or e.date.strftime("%Y-%m") == wanted_month)
        ]
        return sorted(result, key=lambda e: (e.date, e.id))

    def summary(self, month: Optional[str] = None) -> Tuple[Dict[str, Decimal], Decimal]:
        """Return ({category: total} sorted high-to-low, grand_total)."""
        totals: Dict[str, Decimal] = {}
        for item in self.list_expenses(month=month):
            totals[item.category] = totals.get(item.category, Decimal("0")) + item.amount
        ordered = dict(sorted(totals.items(), key=lambda kv: (-kv[1], kv[0])))
        return ordered, sum(ordered.values(), Decimal("0"))

    # ---------------------------------------------------------------- export
    def export_csv(
        self,
        destination: Union[str, Path],
        month: Optional[str] = None,
        force: bool = False,
    ) -> int:
        """Write expenses to a CSV file; return the number of rows exported."""
        dest = Path(destination)
        if dest.is_dir():
            raise ExportError(f"'{dest}' is a folder; give a file name such as report.csv.")
        if dest.exists() and not force:
            raise ExportError(f"'{dest}' already exists. Use --force to overwrite it.")
        rows = self.list_expenses(month=month)
        try:
            with dest.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(_CSV_HEADER)
                for e in rows:
                    writer.writerow(
                        [e.id, e.date.isoformat(), _csv_safe(e.category), e.amount, _csv_safe(e.description)]
                    )
        except OSError as exc:
            raise ExportError(f"Cannot write '{dest}': {exc}") from exc
        return len(rows)
