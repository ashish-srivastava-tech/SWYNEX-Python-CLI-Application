"""Command-line interface: argparse sub-commands plus an interactive menu.

    python main.py add 250 food -d 2026-11-01 -n "Lunch"
    python main.py list -m 2026-11
    python main.py                      # no arguments -> interactive menu
"""

import argparse
import sys
from decimal import Decimal
from typing import Callable, List, Optional, Sequence, TypeVar

from . import __version__
from .exceptions import ExpenseTrackerError, ValidationError
from .manager import ExpenseManager
from .models import Expense
from .validators import (
    parse_amount,
    parse_date,
    parse_id,
    parse_month,
    validate_category,
    validate_description,
)

T = TypeVar("T")


# --------------------------------------------------------------- formatting
def _money(value: Decimal) -> str:
    return f"{value:,.2f}"


def format_table(expenses: Sequence[Expense]) -> str:
    """Render expenses as an aligned text table with a total row."""
    if not expenses:
        return "No expenses found."
    rows = [
        (str(e.id), e.date.isoformat(), e.category, _money(e.amount), e.description)
        for e in expenses
    ]
    header = ("ID", "Date", "Category", "Amount (Rs.)", "Description")
    widths = [max(len(r[i]) for r in rows + [header]) for i in range(5)]

    def line(cells: Sequence[str]) -> str:
        parts = [
            cells[0].rjust(widths[0]),
            cells[1].ljust(widths[1]),
            cells[2].ljust(widths[2]),
            cells[3].rjust(widths[3]),
            cells[4],
        ]
        return "  ".join(parts).rstrip()

    rule = "-" * len(line(header))
    total = sum((e.amount for e in expenses), Decimal("0"))
    out = [line(header), rule] + [line(r) for r in rows] + [rule]
    out.append(f"{len(expenses)} expense(s), total Rs. {_money(total)}")
    return "\n".join(out)


def format_summary(totals: dict, grand_total: Decimal) -> str:
    if not totals:
        return "No expenses found."
    name_w = max(len(name) for name in totals)
    amount_w = max(len(_money(v)) for v in totals.values())
    lines = []
    for name, value in totals.items():
        share = (value / grand_total * 100) if grand_total else Decimal("0")
        lines.append(f"{name.ljust(name_w)}  {_money(value).rjust(amount_w)}  ({share:.1f}%)")
    lines.append("-" * len(lines[0]))
    lines.append(f"{'TOTAL'.ljust(name_w)}  {_money(grand_total).rjust(amount_w)}")
    return "\n".join(lines)


# ------------------------------------------------------------ command logic
def cmd_add(mgr: ExpenseManager, args: argparse.Namespace) -> None:
    e = mgr.add(args.amount, args.category, args.date, args.note)
    print(f"Added expense #{e.id}: Rs. {_money(e.amount)} on {e.date.isoformat()} [{e.category}]")


def cmd_list(mgr: ExpenseManager, args: argparse.Namespace) -> None:
    print(format_table(mgr.list_expenses(args.category, args.month)))


def cmd_delete(mgr: ExpenseManager, args: argparse.Namespace) -> None:
    e = mgr.delete(parse_id(args.id))
    print(f"Deleted expense #{e.id} (Rs. {_money(e.amount)}, {e.category}, {e.date.isoformat()}).")


def cmd_summary(mgr: ExpenseManager, args: argparse.Namespace) -> None:
    totals, grand = mgr.summary(args.month)
    print(format_summary(totals, grand))


def cmd_export(mgr: ExpenseManager, args: argparse.Namespace) -> None:
    count = mgr.export_csv(args.file, args.month, args.force)
    print(f"Exported {count} expense(s) to {args.file}")


# ------------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="expense-tracker",
        description="Track personal expenses from the command line. "
        "Run with no arguments for an interactive menu.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p = sub.add_parser("add", help="add a new expense")
    p.add_argument("amount", help="amount in rupees, e.g. 250 or 99.50")
    p.add_argument("category", help="category, e.g. food, travel (quote if it has spaces)")
    p.add_argument("-d", "--date", help="YYYY-MM-DD (default: today)")
    p.add_argument("-n", "--note", help="optional description (max 100 chars)")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list", help="list expenses")
    p.add_argument("-c", "--category", help="show only this category")
    p.add_argument("-m", "--month", help="show only this month (YYYY-MM)")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("delete", help="delete an expense by ID")
    p.add_argument("id", help="expense ID shown by 'list'")
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("summary", help="category-wise totals")
    p.add_argument("-m", "--month", help="limit to this month (YYYY-MM)")
    p.set_defaults(func=cmd_summary)

    p = sub.add_parser("export", help="export expenses to a CSV file")
    p.add_argument("file", help="destination file, e.g. report.csv")
    p.add_argument("-m", "--month", help="export only this month (YYYY-MM)")
    p.add_argument("--force", action="store_true", help="overwrite the file if it exists")
    p.set_defaults(func=cmd_export)

    return parser


# ----------------------------------------------------------- interactive UI
MENU = """
==== Expense Tracker ====
 1. Add expense
 2. List expenses
 3. Delete expense
 4. Monthly / overall summary
 5. Export to CSV
 0. Exit
"""


def _ask(prompt: str, check: Callable[[str], T]) -> T:
    """Keep asking until `check` accepts the answer (it raises ValidationError if not)."""
    while True:
        answer = input(prompt)
        try:
            return check(answer)
        except ValidationError as exc:
            print(f"  ! {exc}")


def _optional(value: str) -> Optional[str]:
    return value.strip() or None


def _menu_action(mgr: ExpenseManager, choice: str) -> None:
    if choice == "1":
        # Each field is validated as soon as it is typed and re-asked on error.
        amount = _ask("Amount (Rs.): ", parse_amount)
        category = _ask("Category: ", validate_category)
        date = _ask("Date YYYY-MM-DD (Enter = today): ", parse_date)
        note = _ask("Note (optional): ", validate_description)
        e = mgr.add(str(amount), category, date.isoformat(), note)
        print(f"Added expense #{e.id}.")
    elif choice == "2":
        category = _optional(input("Filter by category (Enter = all): "))
        month = _optional(input("Filter by month YYYY-MM (Enter = all): "))
        print(format_table(mgr.list_expenses(category, month)))
    elif choice == "3":
        expense_id = _ask("Expense ID to delete: ", parse_id)
        e = mgr.delete(expense_id)
        print(f"Deleted expense #{e.id}.")
    elif choice == "4":
        month = _optional(input("Month YYYY-MM (Enter = overall): "))
        if month:
            month = parse_month(month)
        print(format_summary(*mgr.summary(month)))
    elif choice == "5":
        file = input("CSV file name (e.g. report.csv): ").strip()
        count = mgr.export_csv(file, force=input("Overwrite if exists? (y/N): ").strip().lower() == "y")
        print(f"Exported {count} expense(s) to {file}")
    else:
        print("Invalid choice. Enter a number from the menu.")


def run_menu(mgr: ExpenseManager) -> int:
    """Interactive loop. A bad input shows an error and returns to the menu."""
    try:
        while True:
            print(MENU)
            choice = input("Choose an option: ").strip()
            if choice == "0":
                print("Goodbye!")
                return 0
            try:
                _menu_action(mgr, choice)
            except ExpenseTrackerError as exc:
                print(f"Error: {exc}")
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        return 0


# --------------------------------------------------------------------- main
def main(argv: Optional[List[str]] = None) -> int:
    """Entry point. Returns a process exit code (0 ok, 1 error, 2 bad usage)."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        manager = ExpenseManager()
        if not getattr(args, "func", None):
            return run_menu(manager)
        args.func(manager, args)
        return 0
    except ExpenseTrackerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
