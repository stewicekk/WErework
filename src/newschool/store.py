"""Transactional file store: temp -> validate -> replace + backup.

This is the direct answer to the reference failure mode where every
saver does ``fopen(path, "w"/"wb")`` in place — a mid-save failure
leaves a half-written map with no rollback (see
docs/audit/AUDIT_CONSOLIDATED.md risk R1):

* payloads are written to a temporary sibling file first;
* the payload is re-read and validated *before* it replaces anything;
* the previous file (if any) is preserved as a ``.bak`` backup;
* replacement uses :func:`os.replace` (atomic on both Windows and POSIX).

On any failure the previous content is guaranteed intact and a
:class:`TransactionError` explains what happened.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from .errors import TransactionError

Validator = Callable[[bytes], None]


def atomic_write_bytes(
    path: str | Path,
    data: bytes,
    validate: Validator | None = None,
    backup: bool = True,
    backup_suffix: str = ".bak",
) -> Path | None:
    """Write *data* to *path* transactionally.

    Returns the backup path when a previous file was preserved, else None.
    """
    target = Path(path)
    if not isinstance(data, (bytes, bytearray)):
        raise TransactionError(f"{target}: payload must be bytes, got {type(data).__name__}")
    payload = bytes(data)
    if validate is not None:
        try:
            validate(payload)
        except Exception as exc:
            raise TransactionError(f"{target}: payload failed pre-write validation: {exc}") from exc
    parent = target.parent
    if str(parent) and not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise TransactionError(f"{target}: cannot create directory {parent}: {exc}") from exc
    tmp_path: str | None = None
    try:
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(parent) if str(parent) else ".",
                prefix=target.name + ".",
                suffix=".tmp",
            )
        except OSError as exc:
            raise TransactionError(f"{target}: cannot create temp file: {exc}") from exc
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
        except OSError as exc:
            raise TransactionError(f"{target}: temp write failed: {exc}") from exc
        if validate is not None:
            try:
                with open(tmp_path, "rb") as fh:
                    validate(fh.read())
            except Exception as exc:
                raise TransactionError(
                    f"{target}: temp payload failed re-read validation: {exc}"
                ) from exc
        backup_path: Path | None = None
        if backup and target.exists():
            backup_path = target.with_name(target.name + backup_suffix)
            try:
                # Copy, never move: the original stays in place until the
                # final atomic replace succeeds, so a failed replace can
                # never leave the target missing.
                import shutil

                if backup_path.exists():
                    os.remove(backup_path)
                shutil.copy2(target, backup_path)
            except OSError as exc:
                raise TransactionError(f"{target}: backup failed: {exc}") from exc
        try:
            os.replace(tmp_path, target)
        except OSError as exc:
            raise TransactionError(f"{target}: atomic replace failed: {exc}") from exc
        tmp_path = None
        return backup_path
    finally:
        if tmp_path is not None:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def atomic_write_text(
    path: str | Path,
    text: str,
    validate: Validator | None = None,
    backup: bool = True,
    newline: str = "\r\n",
) -> Path | None:
    """Text variant: *text* uses ``\\n`` internally, stored with *newline*."""
    data = text.replace("\r\n", "\n").replace("\n", newline).encode("utf-8")
    return atomic_write_bytes(path, data, validate=validate, backup=backup)


def read_bytes(path: str | Path, what: str = "file") -> bytes:
    """Read a file or raise :class:`TransactionError` (never None/stale)."""
    target = Path(path)
    try:
        with open(target, "rb") as fh:
            return fh.read()
    except OSError as exc:
        raise TransactionError(f"{target}: cannot read {what}: {exc}") from exc
