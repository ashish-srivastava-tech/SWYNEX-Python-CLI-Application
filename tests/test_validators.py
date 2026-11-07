import datetime as dt
import unittest
from decimal import Decimal

from expense_tracker.exceptions import ValidationError
from expense_tracker.validators import (
    parse_amount,
    parse_date,
    parse_id,
    parse_month,
    validate_category,
    validate_description,
)


class AmountTests(unittest.TestCase):
    def test_valid_amounts(self):
        self.assertEqual(parse_amount("250"), Decimal("250.00"))
        self.assertEqual(parse_amount(" 99.5 "), Decimal("99.50"))
        self.assertEqual(parse_amount("1,200.75"), Decimal("1200.75"))

    def test_rejects_bad_amounts(self):
        for bad in ["", "   ", "abc", "0", "-5", "0.00", "1.234", "NaN", "Infinity", "-Infinity", "10000001"]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    parse_amount(bad)

    def test_upper_limit_is_inclusive(self):
        self.assertEqual(parse_amount("10000000"), Decimal("10000000.00"))


class DateTests(unittest.TestCase):
    TODAY = dt.date(2026, 11, 7)

    def test_empty_means_today(self):
        self.assertEqual(parse_date("", self.TODAY), self.TODAY)
        self.assertEqual(parse_date(None, self.TODAY), self.TODAY)

    def test_valid_date(self):
        self.assertEqual(parse_date("2026-11-01", self.TODAY), dt.date(2026, 11, 1))
        self.assertEqual(parse_date("2026-11-07", self.TODAY), self.TODAY)

    def test_leap_day(self):
        self.assertEqual(parse_date("2024-02-29", self.TODAY), dt.date(2024, 2, 29))
        with self.assertRaises(ValidationError):
            parse_date("2025-02-29", self.TODAY)

    def test_rejects_bad_dates(self):
        for bad in ["2026-1-5", "07-11-2026", "2026/11/01", "2026-13-01", "2026-02-30", "2026-11-08", "hello"]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    parse_date(bad, self.TODAY)


class TextTests(unittest.TestCase):
    def test_category_normalised(self):
        self.assertEqual(validate_category("  food   & drinks "), "Food & Drinks")
        self.assertEqual(validate_category("TRAVEL"), "Travel")

    def test_category_rejects(self):
        for bad in ["", "   ", "-food", "a" * 31, "food;rm", "café"]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    validate_category(bad)

    def test_description(self):
        self.assertEqual(validate_description(None), "")
        self.assertEqual(validate_description("  Lunch   at  mess "), "Lunch at mess")
        with self.assertRaises(ValidationError):
            validate_description("x" * 101)

    def test_month(self):
        self.assertEqual(parse_month("2026-11"), "2026-11")
        for bad in ["2026-13", "2026-00", "2026-1", "11-2026", ""]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    parse_month(bad)

    def test_id(self):
        self.assertEqual(parse_id(" 7 "), 7)
        for bad in ["0", "-1", "1.5", "abc", ""]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    parse_id(bad)


if __name__ == "__main__":
    unittest.main()
