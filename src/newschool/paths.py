"""Deterministic asset-path resolution.

Verified behavior (``WorldEditor.cpp:102-127,177-183``):

* ``pack/Index`` lists pack pairs, **two lines per pack**: folder line
  followed by pack-name line; ``pack/root`` is registered as the root
  pack.
* ``SEARCH_FILE_FIRST`` mode switch: when set, loose files win over
  packed ones (``PropertyManager::Initialize(NULL)`` vs
  ``Initialize("pack/property")``).
* Environment lookup falls back to the legacy ``d:/ymir work`` tree
  (``MapManagerAccessor.cpp:1587``: ``"d:/ymir work/environment/"``).
  The fallback is kept for existing client workflows only and is always
  the *last* resort behind explicitly configured roots.

Security: absolute paths and ``..`` escapes are rejected with
:class:`PathSecurityError` instead of silently escaping the roots.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .errors import MissingAssetError, ParseError, PathSecurityError, ValidationError

#: Legacy client-workspace fallback (last resort only).
LEGACY_YMIR_WORK = Path("D:/ymir work")


def normalize_logical(path: str) -> str:
    """Normalize a logical asset path to ``a/b/c`` form.

    Rejects absolute paths (POSIX ``/x``, UNC, drive ``C:/x`` and
    ``C:\\x``) and ``..`` escapes. Backslashes become forward slashes;
    redundant separators collapse.
    """
    if not isinstance(path, str) or not path:
        raise PathSecurityError(f"empty asset path: {path!r}")
    probe = Path(path)
    if (
        probe.is_absolute()
        or path.startswith(("\\\\", "//", "/"))
        or (len(path) >= 2 and path[1] == ":" and path[0].isalpha())
    ):
        raise PathSecurityError(f"absolute asset path rejected: {path!r}")
    parts: list[str] = []
    for part in path.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise PathSecurityError(f"asset path escapes roots: {path!r}")
        parts.append(part)
    if not parts:
        raise PathSecurityError(f"empty asset path: {path!r}")
    return "/".join(parts)


def parse_index(text: str, source: str = "<memory>") -> list[tuple[str, str]]:
    """Parse a ``pack/Index`` file: two lines per pack (folder, name).

    A trailing incomplete pair raises :class:`ParseError` instead of
    being silently ignored.
    """
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln != ""]
    if len(lines) % 2:
        raise ParseError(source, f"pack Index has an incomplete trailing pair ({len(lines)} lines)")
    return [(lines[i], lines[i + 1]) for i in range(0, len(lines), 2)]


@dataclass
class PathResolver:
    """Ordered asset roots with loose-first precedence.

    ``roots[0]`` wins. When ``loose_first`` is set (legacy
    ``SEARCH_FILE_FIRST``), a loose file in any root shadows packed
    content; packed lookup itself is represented by *pack_roots*
    (extracted pack trees), also in precedence order.
    """

    roots: list[Path] = field(default_factory=list)
    pack_roots: list[Path] = field(default_factory=list)
    loose_first: bool = True
    ymir_fallback: Path | None = LEGACY_YMIR_WORK

    def _candidate_roots(self) -> list[Path]:
        ordered = list(self.roots)
        if self.loose_first:
            ordered.extend(self.pack_roots)
        else:
            ordered = list(self.pack_roots) + ordered
        if self.ymir_fallback is not None:
            ordered.append(self.ymir_fallback)
        return ordered

    def search_order(self) -> list[str]:
        return [str(p) for p in self._candidate_roots()]

    def resolve(self, logical_path: str) -> Path | None:
        """First existing filesystem hit, or None when simply absent.

        :raises PathSecurityError: when *logical_path* escapes the roots
            (absolute path or ``..``) — a security condition, never None.
        """
        rel = normalize_logical(logical_path)
        for root in self._candidate_roots():
            hit = root / rel
            if hit.is_file():
                return hit
        return None

    def require(self, logical_path: str) -> Path:
        """Like :meth:`resolve` but raises :class:`MissingAssetError`."""
        hit = self.resolve(logical_path)
        if hit is None:
            raise MissingAssetError(logical_path, self.search_order())
        return hit

    def missing_report(self, logical_paths: list[str]) -> list[MissingAssetError]:
        """Collect missing-asset diagnostics without raising."""
        missing: list[MissingAssetError] = []
        for logical in logical_paths:
            try:
                self.require(logical)
            except MissingAssetError as exc:
                missing.append(exc)
            except PathSecurityError:
                missing.append(MissingAssetError(logical, self.search_order()))
        return missing

    def map_directory(self, map_name: str) -> Path | None:
        """Locate a map folder ``<root>/<map_name>`` containing ``Setting.txt``."""
        if not isinstance(map_name, str) or not map_name:
            raise ValidationError(f"invalid map name: {map_name!r}")
        # Map names are single folder names — no separators, no drives.
        if (
            "/" in map_name
            or "\\" in map_name
            or map_name in (".", "..")
            or (len(map_name) >= 2 and map_name[1] == ":" and map_name[0].isalpha())
        ):
            raise PathSecurityError(f"map name escapes roots: {map_name!r}")
        for root in self._candidate_roots():
            candidate = root / map_name
            if (candidate / "Setting.txt").is_file():
                return candidate
        return None


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def dir_size_hint(path: Path) -> int:
    """Best-effort file count under *path* (diagnostics only)."""
    total = 0
    try:
        for _root, _dirs, files in os.walk(path):
            total += len(files)
    except OSError:
        pass
    return total
