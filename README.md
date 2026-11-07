# SWYNEX-Python-CLI-Application

**Expense Tracker** - a command-line application written in pure Python (standard library only) to record, view, summarise and export personal expenses.

Submitted as **Task 1** of the Python internship at **SWYNEX Technologies**.

---

## 1. Objectives

| # | Requirement from the task | How this project meets it |
|---|---|---|
| 1 | Python CLI application | Expense tracker with `argparse` sub-commands **and** an interactive menu |
| 2 | Use functions | Small single-purpose functions in every module (parsing, formatting, storage, commands) |
| 3 | Use modules | Separate package `expense_tracker/` - one module per responsibility |
| 4 | Validation | Every user input (amount, date, month, category, description, ID) is validated before use |
| 5 | Exception handling | Custom exception hierarchy; the CLI shows clean messages instead of tracebacks |
| 6 | Upload to GitHub | This repository |

## 2. Features

- **Add** an expense (amount, category, optional date and note)
- **List** expenses, filter by category and/or month
- **Delete** an expense by ID
- **Summary** - category-wise totals with percentage share (overall or for one month)
- **Export** to CSV (optionally one month; refuses to overwrite unless `--force`)
- **Interactive menu** when run without arguments
- **Persistent storage** in a JSON file, written atomically

## 3. Tools & Technologies

| Item | Detail |
|---|---|
| Language | Python 3 - tested on 3.11, 3.12 and 3.13 |
| Libraries | Standard library only: `argparse`, `json`, `csv`, `decimal`, `datetime`, `pathlib`, `re`, `tempfile`, `unittest` |
| Third-party packages | None - nothing to install |
| Storage | JSON file (`data/expenses.json`) |
| Testing | `unittest` (31 tests) |

## 4. Project Structure

```
SWYNEX-Python-CLI-Application/
├── main.py                    # entry point
├── expense_tracker/
│   ├── __init__.py            # package info / version
│   ├── cli.py                 # argparse commands, interactive menu, output formatting
│   ├── manager.py             # business logic: add, delete, list, summary, export
│   ├── validators.py          # input validation and normalisation
│   ├── storage.py             # JSON load / atomic save
│   ├── models.py              # Expense dataclass
│   └── exceptions.py          # custom exceptions
├── tests/
│   ├── test_validators.py
│   └── test_manager.py
├── .gitignore
└── README.md
```

**Layering:** `cli` -> `manager` -> (`validators`, `storage`, `models`). The CLI only handles input/output; all rules live in `manager` and `validators`, so they cannot be bypassed.

## 5. How to Run

```bash
git clone https://github.com/<your-username>/SWYNEX-Python-CLI-Application.git
cd SWYNEX-Python-CLI-Application
python main.py --help
```

(Use `python3` instead of `python` on Linux/macOS if needed.)

### Command reference

| Command | Example |
|---|---|
| Add | `python main.py add 250 food -d 2026-11-01 -n "Lunch at mess"` |
| Add (today, no note) | `python main.py add 60 travel` |
| List all | `python main.py list` |
| List filtered | `python main.py list -c food -m 2026-11` |
| Delete | `python main.py delete 3` |
| Summary (overall) | `python main.py summary` |
| Summary (one month) | `python main.py summary -m 2026-11` |
| Export CSV | `python main.py export report.csv` |
| Export (overwrite) | `python main.py export report.csv --force` |
| Interactive menu | `python main.py` |
| Version | `python main.py --version` |

### Sample session

```
$ python main.py add 250 food -d 2026-11-01 -n "Lunch at mess"
Added expense #1: Rs. 250.00 on 2026-11-01 [Food]

$ python main.py add 1200.50 "Study Material" -d 2026-11-03 -n "GATE books"
Added expense #2: Rs. 1,200.50 on 2026-11-03 [Study Material]

$ python main.py list
ID  Date        Category        Amount (Rs.)  Description
---------------------------------------------------------
 1  2026-11-01  Food                  250.00  Lunch at mess
 2  2026-11-03  Study Material      1,200.50  GATE books
---------------------------------------------------------
2 expense(s), total Rs. 1,450.50

$ python main.py summary
Study Material  1,200.50  (82.8%)
Food              250.00  (17.2%)
---------------------------------
TOTAL           1,450.50

$ python main.py add -50 food
Error: Amount must be greater than zero.
```

Exit codes: `0` success, `1` application error, `2` wrong command-line usage, `130` cancelled with Ctrl+C.

### Where is my data stored?

`data/expenses.json` inside the project folder (created on first add, ignored by Git).
Set the environment variable `EXPENSE_TRACKER_FILE` to use another location.

## 6. Validation Rules

| Field | Rules |
|---|---|
| Amount | Required; number only; `NaN`/`Infinity` rejected; must be > 0; max 2 decimal places; max 1,00,00,000; commas allowed (`1,200`) |
| Date | `YYYY-MM-DD` with zero-padding; must be a real calendar date (leap years handled); cannot be in the future; empty = today |
| Month filter | `YYYY-MM`, month 01-12 |
| Category | 1-30 chars; letters, digits, spaces, `&`, `-`; stored in Title Case (`food` and `FOOD` are the same category) |
| Description | Optional; max 100 chars; control characters rejected |
| ID | Positive whole number that exists |

## 7. Error Handling

All deliberate errors derive from `ExpenseTrackerError`:

| Exception | Raised when |
|---|---|
| `ValidationError` | Any input rule above is broken |
| `ExpenseNotFoundError` | Deleting an ID that does not exist |
| `StorageError` | Data file unreadable, corrupted, or not writable |
| `ExportError` | CSV target is a folder, already exists (without `--force`), or not writable |

`main()` catches the base class, prints `Error: <message>` to stderr and returns exit code 1. `Ctrl+C` / `Ctrl+D` are handled gracefully.

## 8. Design Decisions & Edge Cases

- **`Decimal`, not `float`** - money sums are exact (`0.1 + 0.2` is `0.30`, not `0.30000000000000004`).
- **Atomic writes** - data goes to a temp file, then `os.replace` swaps it in; a crash cannot leave a half-written file.
- **Failed save does not corrupt memory state** - the file is written first, in-memory state updated only on success.
- **Corrupted data file is never overwritten** - the app reports the problem and leaves the file untouched.
- **IDs are never reused** after delete, and a hand-edited `next_id` cannot create duplicate IDs.
- **CSV formula-injection guard** - a description or category starting with `=`, `+`, `-` or `@` is prefixed with `'` so Excel does not run it as a formula.
- **No accidental overwrite** on export without `--force`.
- Negative amounts like `-50` are parsed as the amount argument (not as an option) and then rejected by validation.

## 9. Running the Tests

```bash
python -m unittest -v
```

31 tests cover valid/invalid amounts, dates (including leap day), text fields, persistence across restarts, ID uniqueness, filters, exact decimal summaries, corrupted/empty/hand-edited data files, unwritable locations, and CSV export.

## 10. Limitations & Possible Improvements

- Single-user, single-process; no file locking if two copies run at the same time.
- Currency is fixed to rupees (`Rs.`) for display.
- Possible next steps: edit command, budgets per category, charts, SQLite storage.

## 11. Author

**Ashish Srivastava** - B.Tech CSE, BP Mandal College of Engineering, Madhepura
SWYNEX Technologies - Python Internship, Task 1
