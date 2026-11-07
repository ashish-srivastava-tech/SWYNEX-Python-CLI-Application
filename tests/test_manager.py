import csv
import datetime as dt
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from expense_tracker.exceptions import (
    ExpenseNotFoundError,
    ExportError,
    StorageError,
    ValidationError,
)
from expense_tracker.manager import ExpenseManager


class ManagerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "expenses.json"
        self.mgr = ExpenseManager(self.path)


class AddDeleteTests(ManagerTestCase):
    def test_add_persists_across_instances(self):
        self.mgr.add("250", "food", "2026-11-01", "Lunch")
        reloaded = ExpenseManager(self.path)
        items = reloaded.list_expenses()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].amount, Decimal("250.00"))
        self.assertEqual(items[0].category, "Food")

    def test_invalid_add_changes_nothing(self):
        with self.assertRaises(ValidationError):
            self.mgr.add("-1", "food")
        self.assertFalse(self.path.exists())
        self.assertEqual(self.mgr.list_expenses(), [])

    def test_ids_are_never_reused(self):
        a = self.mgr.add("10", "a")
        b = self.mgr.add("20", "b")
        self.mgr.delete(b.id)
        c = self.mgr.add("30", "c")
        self.assertEqual((a.id, b.id, c.id), (1, 2, 3))
        # ...and that survives a restart
        self.assertEqual(ExpenseManager(self.path).add("40", "d").id, 4)

    def test_delete_unknown_id(self):
        with self.assertRaises(ExpenseNotFoundError):
            self.mgr.delete(99)

    def test_delete_removes_only_target(self):
        a = self.mgr.add("10", "a")
        b = self.mgr.add("20", "b")
        self.mgr.delete(a.id)
        self.assertEqual([e.id for e in self.mgr.list_expenses()], [b.id])


class QueryTests(ManagerTestCase):
    def setUp(self):
        super().setUp()
        self.mgr.add("100", "food", "2026-10-30")
        self.mgr.add("50.50", "travel", "2026-11-02")
        self.mgr.add("200", "Food", "2026-11-05")

    def test_sorted_by_date(self):
        dates = [e.date for e in self.mgr.list_expenses()]
        self.assertEqual(dates, sorted(dates))

    def test_filters(self):
        self.assertEqual(len(self.mgr.list_expenses(category="FOOD")), 2)
        self.assertEqual(len(self.mgr.list_expenses(month="2026-11")), 2)
        self.assertEqual(len(self.mgr.list_expenses(category="food", month="2026-11")), 1)
        self.assertEqual(self.mgr.list_expenses(month="2025-01"), [])

    def test_summary_exact_decimal_math(self):
        totals, grand = self.mgr.summary()
        self.assertEqual(totals, {"Food": Decimal("300.00"), "Travel": Decimal("50.50")})
        self.assertEqual(grand, Decimal("350.50"))
        self.assertEqual(list(totals), ["Food", "Travel"])  # highest first

    def test_summary_empty_month(self):
        totals, grand = self.mgr.summary("2025-01")
        self.assertEqual((totals, grand), ({}, Decimal("0")))

    def test_bad_filter_values_rejected(self):
        with self.assertRaises(ValidationError):
            self.mgr.list_expenses(month="2026-13")
        with self.assertRaises(ValidationError):
            self.mgr.list_expenses(category="bad;name")


class StorageTests(ManagerTestCase):
    def test_corrupt_file_is_reported_and_left_untouched(self):
        self.path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(StorageError):
            ExpenseManager(self.path)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{not json")

    def test_wrong_structure_is_reported(self):
        self.path.write_text(json.dumps({"next_id": 1, "expenses": [{"id": 1}]}), encoding="utf-8")
        with self.assertRaises(StorageError):
            ExpenseManager(self.path)

    def test_empty_file_is_fresh_start(self):
        self.path.write_text("", encoding="utf-8")
        self.assertEqual(ExpenseManager(self.path).list_expenses(), [])

    def test_hand_edited_next_id_cannot_cause_duplicate_ids(self):
        self.mgr.add("10", "a")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data["next_id"] = 1
        self.path.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(ExpenseManager(self.path).add("20", "b").id, 2)

    def test_unwritable_location_raises_storage_error(self):
        blocker = self.dir / "file.txt"
        blocker.write_text("x", encoding="utf-8")
        bad = ExpenseManager(blocker / "sub" / "expenses.json")  # parent is a file
        with self.assertRaises(StorageError):
            bad.add("10", "a")
        self.assertEqual(bad.list_expenses(), [])  # memory not changed after failure


class ExportTests(ManagerTestCase):
    def test_export_and_formula_guard(self):
        self.mgr.add("10", "food", "2026-11-01", "=2+2")
        out = self.dir / "report.csv"
        self.assertEqual(self.mgr.export_csv(out), 1)
        with out.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(rows[0], ["id", "date", "category", "amount", "description"])
        self.assertEqual(rows[1][4], "'=2+2")
        self.assertEqual(rows[1][3], "10.00")

    def test_no_overwrite_without_force(self):
        out = self.dir / "report.csv"
        out.write_text("keep me", encoding="utf-8")
        with self.assertRaises(ExportError):
            self.mgr.export_csv(out)
        self.assertEqual(out.read_text(encoding="utf-8"), "keep me")
        self.mgr.export_csv(out, force=True)
        self.assertIn("id,date", out.read_text(encoding="utf-8"))

    def test_folder_destination_rejected(self):
        with self.assertRaises(ExportError):
            self.mgr.export_csv(self.dir)

    def test_month_filter(self):
        self.mgr.add("10", "a", "2026-10-01")
        self.mgr.add("20", "a", "2026-11-01")
        self.assertEqual(self.mgr.export_csv(self.dir / "nov.csv", month="2026-11"), 1)


if __name__ == "__main__":
    unittest.main()
