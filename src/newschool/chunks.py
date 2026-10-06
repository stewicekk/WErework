"""Map chunk addressing.

Verified against the reference implementation
(``DataCtrl/MapAccessorOutdoor.cpp:780-781,1269-1271``):

* per-chunk folder name is ``"%06u" % (X * 1000 + Y)``
* terrain brush iteration runs ``usX/usY < terrainCountX/Y``
  (``MapAccessorOutdoor.cpp:875,891``)
* atlas stitching iterates the same grid
  (``MapManagerAccessor.cpp:1405-1407``)

``X`` and ``Y`` are each bounded to ``0..999`` so the folder id always
fits the six-digit field; anything else is rejected instead of silently
producing ambiguous folder names.
"""

from __future__ import annotations

from .errors import ValidationError

MAX_COORD = 999
FOLDER_WIDTH = 6


def _check_coord(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"chunk coordinate {name} must be an integer, got {value!r}")
    if not 0 <= value <= MAX_COORD:
        raise ValidationError(
            f"chunk coordinate {name}={value} out of range 0..{MAX_COORD} "
            "(folder id X*1000+Y must fit six digits)"
        )
    return value


def chunk_id(x: int, y: int) -> int:
    """Folder id for chunk ``(x, y)``: ``X * 1000 + Y``."""
    _check_coord("x", x)
    _check_coord("y", y)
    return x * 1000 + y


def chunk_folder(x: int, y: int) -> str:
    """Six-digit folder name for chunk ``(x, y)`` (e.g. ``"001002"``)."""
    return f"{chunk_id(x, y):0{FOLDER_WIDTH}d}"


def parse_chunk_folder(name: str) -> tuple[int, int]:
    """Inverse of :func:`chunk_folder`: ``"001002"`` -> ``(1, 2)``.

    Rejects anything that is not exactly six ASCII digits or that does
    not round-trip (defensive against hand-edited trees).
    """
    if not isinstance(name, str) or len(name) != FOLDER_WIDTH or not name.isascii() or not name.isdigit():
        raise ValidationError(f"invalid chunk folder name {name!r}: expected six digits")
    ident = int(name)
    x, y = divmod(ident, 1000)
    if chunk_folder(x, y) != name:
        raise ValidationError(f"chunk folder name {name!r} does not round-trip")
    return x, y


def iter_chunks(count_x: int, count_y: int):
    """Yield ``(x, y)`` for a ``count_x`` x ``count_y`` map grid."""
    for name, count in (("count_x", count_x), ("count_y", count_y)):
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValidationError(f"chunk {name} must be an integer, got {count!r}")
    if count_x < 1 or count_y < 1:
        raise ValidationError(f"chunk counts must be >= 1, got {count_x}x{count_y}")
    if count_x > MAX_COORD + 1 or count_y > MAX_COORD + 1:
        raise ValidationError(f"chunk counts out of range: {count_x}x{count_y}")
    for y in range(count_y):
        for x in range(count_x):
            yield x, y
