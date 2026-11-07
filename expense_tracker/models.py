"""Data model for a single expense record."""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict


@dataclass(frozen=True)
class Expense:
    """An immutable expense record.

    The amount is a Decimal (never a float) so that sums such as
    0.10 + 0.20 are exact.
    """

    id: int
    amount: Decimal
    category: str
    date: dt.date
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to JSON-friendly primitives (amount kept as a string)."""
        return {
            "id": self.id,
            "amount": str(self.amount),
            "category": self.category,
            "date": self.date.isoformat(),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Expense":
        """Rebuild an Expense from stored data.

        Raises KeyError, TypeError, ValueError or decimal.InvalidOperation
        if the record is malformed; the storage layer converts these into
        a StorageError.
        """
        return cls(
            id=int(data["id"]),
            amount=Decimal(str(data["amount"])),
            category=str(data["category"]),
            date=dt.date.fromisoformat(str(data["date"])),
            description=str(data.get("description", "")),
        )
