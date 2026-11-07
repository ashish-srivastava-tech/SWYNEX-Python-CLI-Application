"""Custom exception hierarchy used across the application.

Every error the application raises on purpose derives from
ExpenseTrackerError, so the CLI layer can catch one base class and show a
clean message instead of a traceback.
"""


class ExpenseTrackerError(Exception):
    """Base class for all application-specific errors."""


class ValidationError(ExpenseTrackerError):
    """User input failed validation (bad amount, bad date, ...)."""


class StorageError(ExpenseTrackerError):
    """The data file could not be read, parsed or written."""


class ExpenseNotFoundError(ExpenseTrackerError):
    """No expense exists with the requested ID."""


class ExportError(ExpenseTrackerError):
    """The CSV export could not be completed."""
