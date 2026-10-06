"""Command/transaction layer: every mutation is reversible.

Replaces the reference snapshot undo (raw area pointers, use-after-free
on restore — see docs/audit/AUDIT_CONSOLIDATED.md risks R2/R3) with an
owned command stack:

* :class:`Command` — a validated, reversible mutation with a name.
* :class:`FnCommand` — wraps a do/undo closure pair (state owned by
  the command, never borrowed raw pointers).
* :class:`CompositeCommand` — grouped operations undone/redone as one.
* :class:`UndoStack` — bounded stack with deterministic redo and
  explicit grouping; integrates with :class:`WorldDocument` dirty state.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .errors import ValidationError

DEFAULT_STACK_LIMIT = 200


class Command:
    """A named, reversible mutation. Subclass and implement do/undo."""

    name: str = "command"

    def validate(self) -> None:
        """Raise :class:`ValidationError` when the command cannot run."""

    def do(self) -> None:
        raise NotImplementedError

    def undo(self) -> None:
        raise NotImplementedError


class FnCommand(Command):
    """Command from a closure pair; owns its before/after state."""

    def __init__(self, name: str, do_fn: Callable[[], None],
                 undo_fn: Callable[[], None],
                 validate_fn: Callable[[], None] | None = None):
        self.name = name
        self._do = do_fn
        self._undo = undo_fn
        self._validate = validate_fn

    def validate(self) -> None:
        if self._validate is not None:
            self._validate()

    def do(self) -> None:
        self._do()

    def undo(self) -> None:
        self._undo()


class CompositeCommand(Command):
    """An ordered group of commands applied/undone as a single unit."""

    def __init__(self, name: str, commands: list[Command] | None = None):
        self.name = name
        self.commands: list[Command] = list(commands) if commands else []

    def add(self, command: Command) -> None:
        self.commands.append(command)

    def validate(self) -> None:
        if not self.commands:
            raise ValidationError(f"composite command {self.name!r} is empty")
        for cmd in self.commands:
            cmd.validate()

    def do(self) -> None:
        done: list[Command] = []
        try:
            for cmd in self.commands:
                cmd.do()
                done.append(cmd)
        except Exception:
            for cmd in reversed(done):
                try:
                    cmd.undo()
                except Exception:
                    pass
            raise

    def undo(self) -> None:
        done: list[Command] = []
        try:
            for cmd in reversed(self.commands):
                cmd.undo()
                done.append(cmd)
        except Exception:
            for cmd in reversed(done):
                try:
                    cmd.do()
                except Exception:
                    pass
            raise


class UndoStack:
    """Bounded undo/redo stack with grouping support."""

    def __init__(self, limit: int = DEFAULT_STACK_LIMIT):
        if limit < 1:
            raise ValidationError(f"undo stack limit must be >= 1, got {limit}")
        self._limit = limit
        self._undo: list[Command] = []
        self._redo: list[Command] = []
        self._group: CompositeCommand | None = None
        self._group_depth = 0

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_depth(self) -> int:
        return len(self._undo)

    @property
    def redo_depth(self) -> int:
        return len(self._redo)

    def history(self) -> list[str]:
        """Oldest-first command names (for history panels/diagnostics)."""
        return [cmd.name for cmd in self._undo]

    def execute(self, command: Command):
        """Validate, run and record *command*; clears the redo branch."""
        command.validate()
        if self._group is not None:
            command.do()
            self._group.add(command)
            return None
        command.do()
        self._undo.append(command)
        del self._redo[:]
        while len(self._undo) > self._limit:
            del self._undo[0]
        return None

    def begin_group(self, name: str) -> None:
        if self._group_depth == 0:
            self._group = CompositeCommand(name)
        self._group_depth += 1

    def abort_group(self) -> None:
        """Discard the open group (e.g. after a failed member).

        Commands already executed inside the group are NOT rolled back by
        this call — use a CompositeCommand boundary when the grouped
        work must be atomic.
        """
        if self._group_depth == 0:
            raise ValidationError("abort_group without begin_group")
        self._group = None
        self._group_depth = 0

    def end_group(self) -> None:
        if self._group_depth == 0:
            raise ValidationError("end_group without begin_group")
        self._group_depth -= 1
        if self._group_depth == 0:
            assert self._group is not None
            group, self._group = self._group, None
            if group.commands:
                self._undo.append(group)
                del self._redo[:]
                while len(self._undo) > self._limit:
                    del self._undo[0]

    def undo(self) -> str:
        if not self._undo:
            raise ValidationError("nothing to undo")
        cmd = self._undo[-1]
        cmd.undo()  # only transferred after success: failed undo keeps the stack intact
        self._undo.pop()
        self._redo.append(cmd)
        return cmd.name

    def redo(self) -> str:
        if not self._redo:
            raise ValidationError("nothing to redo")
        cmd = self._redo[-1]
        cmd.validate()
        cmd.do()  # only transferred after success
        self._redo.pop()
        self._undo.append(cmd)
        return cmd.name

    def clear(self) -> None:
        del self._undo[:]
        del self._redo[:]
        self._group = None
        self._group_depth = 0


# -- document-level concrete commands -------------------------------------

@dataclass
class MoveObjectCommand(Command):
    """Translate one area object; validates finiteness + chunk bounds.

    The target is resolved through *lookup* on every do/undo — never a
    borrowed direct reference — so undo after the object was deleted or
    the chunk replaced fails loudly instead of corrupting memory.
    """

    name: str = "move object"
    lookup: Callable[[], object] | None = None
    dx: float = 0.0
    dy: float = 0.0
    dz: float = 0.0
    _before: tuple[float, float, float] = field(default=(0.0, 0.0, 0.0), repr=False)

    def _resolve(self):
        from .mapfiles import ObjectInstance  # local import: no cycle at runtime

        if self.lookup is None:
            raise ValidationError("MoveObjectCommand has no target lookup")
        target = self.lookup()
        if not isinstance(target, ObjectInstance):
            raise ValidationError(
                "MoveObjectCommand target no longer exists (deleted or replaced?)"
            )
        return target

    def _check_delta(self) -> None:
        import math

        for comp, v in (("dx", self.dx), ("dy", self.dy), ("dz", self.dz)):
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise ValidationError(f"MoveObjectCommand.{comp}: expected number, got {v!r}")
            if not math.isfinite(v):
                raise ValidationError(f"MoveObjectCommand.{comp}: non-finite {v!r}")

    def validate(self) -> None:
        self._check_delta()
        target = self._resolve()
        for v in (target.x + self.dx, target.y + self.dy, target.z + self.dz):
            import math

            if not math.isfinite(v):
                raise ValidationError(f"MoveObjectCommand: resulting position {v!r} non-finite")

    def do(self) -> None:
        self.validate()
        target = self._resolve()
        self._before = (target.x, target.y, target.z)
        target.x += self.dx
        target.y += self.dy
        target.z += self.dz
        target.validate()

    def undo(self) -> None:
        target = self._resolve()
        target.x, target.y, target.z = self._before
        target.validate()


def object_lookup(document, chunk_key: tuple[int, int], index: int) -> Callable[[], object]:
    """Build a chunk/index target lookup for object commands."""
    def _lookup():
        try:
            return document.chunks[chunk_key].objects[index]
        except (KeyError, IndexError):
            return None

    return _lookup
