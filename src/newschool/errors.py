"""Structured error hierarchy for the NewSchool editor core.

Every failure carries an actionable message: what was being done, where
(file + line where applicable) and what the user can do about it.
The core never fails silently — callers get typed exceptions, never
stale state.
"""

from __future__ import annotations


class NewschoolError(Exception):
    """Base class for all editor-core errors."""


class ParseError(NewschoolError):
    """A file could not be parsed.

    Raised instead of returning partial/stale data. ``line_no`` is 1-based
    when the failure is attributable to a single line, else None.
    """

    def __init__(self, source: str, detail: str, line_no: int | None = None):
        self.source = source
        self.detail = detail
        self.line_no = line_no
        where = f"{source}:{line_no}" if line_no is not None else source
        super().__init__(f"parse failed [{where}]: {detail}")


class ValidationError(NewschoolError):
    """A value failed domain validation (range, finiteness, shape)."""


class TransactionError(NewschoolError):
    """An atomic save/transaction could not be completed safely.

    The previous file content is guaranteed intact when this is raised:
    replacement only ever happens after the temporary payload validated.
    """


class RecoveryError(NewschoolError):
    """Autosave/recovery data is missing or unusable."""


class PathSecurityError(NewschoolError):
    """A path escapes the configured roots (absolute path or ``..``)."""


class MissingAssetError(NewschoolError):
    """A referenced asset was not found in any configured root.

    This is a *diagnostic* condition, not a crash: callers report it
    through the missing-asset list and keep the stale-free state.
    """

    def __init__(self, logical_path: str, searched: list[str]):
        self.logical_path = logical_path
        self.searched = list(searched)
        super().__init__(
            f"missing asset '{logical_path}' "
            f"(searched: {', '.join(searched) if searched else 'no roots configured'})"
        )
