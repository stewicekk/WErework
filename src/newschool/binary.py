"""Raw terrain/area binary serializers.

Byte layouts verified against the reference save side
(``DataCtrl/MapAccessorTerrain.cpp``, ``DataCtrl/MapManagerAccessor.cpp``):

* ``height.raw`` — raw little-endian WORD array, no header; new maps are
  filled with ``0x7FFF`` (``MapAccessorTerrain.cpp:1073-1098``).
* ``tile.raw`` — raw BYTE array, no header (``:1108-1142``).
* ``attr.atr`` — ``WORD mapver=2634`` + ``WORD w`` + ``WORD h`` + bytes
  (``:1159-1168``).
* ``water.wtr`` — ``WORD mapver=5426`` + ``WORD w`` + ``WORD h`` +
  ``BYTE numWater`` + water map bytes + ``long[numWater]`` heights
  (``:1316-1330``). ``long`` is 4 bytes on the Win32 target, so heights
  are (de)serialized explicitly as little-endian int32.
* collision output header — ``MAKEFOURCC('M','2','C','D')`` + terrain
  counts (``MapManagerAccessor.cpp:891``).

Array dimensions (``HEIGHTMAP_RAW_XSIZE`` etc.) live in the absent
GameLib sources and are therefore *parameters*, never hard-coded
constants — callers pass the element count they operate on.
"""

from __future__ import annotations

import struct

from .errors import ParseError, ValidationError

ATTR_MAPVER = 2634
WATER_MAPVER = 5426
HEIGHT_NEW_FILL = 0x7FFF

_UINT16 = struct.Struct("<H")
_INT32 = struct.Struct("<i")


# -- height.raw -------------------------------------------------------
def dump_height(values: list[int] | tuple[int, ...] | bytes | bytearray) -> bytes:
    """Serialize height samples to ``height.raw`` payload (raw WORDs)."""
    if isinstance(values, (bytes, bytearray)):
        raw = bytes(values)
        if len(raw) % 2:
            raise ValidationError(f"height.raw: odd byte length {len(raw)}")
        return raw
    for v in values:
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 0xFFFF:
            raise ValidationError(f"height.raw: sample {v!r} out of WORD range 0..65535")
    return b"".join(_UINT16.pack(v) for v in values)


def load_height(data: bytes, count: int, source: str = "<memory>") -> list[int]:
    """Parse ``height.raw`` payload; exact-length match required."""
    if len(data) != count * 2:
        raise ParseError(source, f"height.raw: byte length {len(data)} != {count} * 2")
    return list(struct.unpack(f"<{count}H", data)) if count else []


def new_height(count: int) -> list[int]:
    """Height samples for a new map (legacy fill ``0x7FFF``)."""
    if count < 0:
        raise ValidationError(f"height fill: negative count {count}")
    return [HEIGHT_NEW_FILL] * count


# -- tile.raw ---------------------------------------------------------
def dump_tile(values: list[int] | tuple[int, ...] | bytes | bytearray) -> bytes:
    """Serialize texture indices to ``tile.raw`` payload (raw BYTEs)."""
    if isinstance(values, (bytes, bytearray)):
        return bytes(values)
    for v in values:
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 0xFF:
            raise ValidationError(f"tile.raw: index {v!r} out of BYTE range 0..255")
    return bytes(values)


def load_tile(data: bytes, count: int, source: str = "<memory>") -> bytes:
    """Parse ``tile.raw`` payload; exact-length match required."""
    if len(data) != count:
        raise ParseError(source, f"tile.raw: byte length {len(data)} != {count}")
    return bytes(data)


# -- attr.atr ---------------------------------------------------------
def dump_attr(width: int, height: int, values: bytes | bytearray | list[int]) -> bytes:
    """Serialize to ``attr.atr`` payload (mapver + dims + bytes)."""
    if isinstance(values, list):
        for v in values:
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 0xFF:
                raise ValidationError(f"attr.atr: sample {v!r} out of BYTE range 0..255")
    raw = bytes(values)
    for name, dim in (("width", width), ("height", height)):
        if isinstance(dim, bool) or not isinstance(dim, int) or dim < 0 or dim > 0xFFFF:
            raise ValidationError(f"attr.atr: {name} {dim!r} out of WORD range")
    if len(raw) != width * height:
        raise ValidationError(
            f"attr.atr: payload length {len(raw)} != {width} * {height}"
        )
    return _UINT16.pack(ATTR_MAPVER) + _UINT16.pack(width) + _UINT16.pack(height) + raw


def load_attr(data: bytes, source: str = "<memory>") -> tuple[int, int, bytes]:
    """Parse ``attr.atr`` payload; rejects wrong magic and truncation."""
    if len(data) < 6:
        raise ParseError(source, f"attr.atr: truncated header ({len(data)} bytes)")
    (mapver, width, height) = struct.unpack("<HHH", data[:6])
    if mapver != ATTR_MAPVER:
        raise ParseError(source, f"attr.atr: bad magic {mapver}, expected {ATTR_MAPVER}")
    body = data[6:]
    if len(body) != width * height:
        raise ParseError(
            source, f"attr.atr: body length {len(body)} != {width} * {height}"
        )
    return width, height, bytes(body)


# -- water.wtr --------------------------------------------------------
def dump_water(width: int, height: int, watermap: bytes | bytearray | list[int],
               heights: list[int] | tuple[int, ...]) -> bytes:
    """Serialize to ``water.wtr`` payload.

    ``heights`` entries are Win32-``long`` compatible signed 32-bit
    values (``0xFF`` marks an empty water cell, ``-1`` a free height
    slot — both preserved as plain data here).
    """
    if isinstance(watermap, list):
        for v in watermap:
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 0xFF:
                raise ValidationError(f"water.wtr: watermap sample {v!r} out of BYTE range")
    raw = bytes(watermap)
    for name, dim in (("width", width), ("height", height)):
        if isinstance(dim, bool) or not isinstance(dim, int) or dim < 0 or dim > 0xFFFF:
            raise ValidationError(f"water.wtr: {name} {dim!r} out of WORD range")
    if len(raw) != width * height:
        raise ValidationError(
            f"water.wtr: watermap length {len(raw)} != {width} * {height}"
        )
    if len(heights) > 0xFF:
        raise ValidationError(f"water.wtr: {len(heights)} heights exceed BYTE count")
    for h in heights:
        if isinstance(h, bool) or not isinstance(h, int) or not -(2**31) <= h <= 2**31 - 1:
            raise ValidationError(f"water.wtr: height {h!r} out of int32 range")
    out = _UINT16.pack(WATER_MAPVER) + _UINT16.pack(width) + _UINT16.pack(height)
    out += bytes([len(heights)]) + raw
    for h in heights:
        out += _INT32.pack(h)
    return out


def load_water(data: bytes, source: str = "<memory>") -> tuple[int, int, bytes, list[int]]:
    """Parse ``water.wtr`` payload; rejects wrong magic and truncation."""
    if len(data) < 7:
        raise ParseError(source, f"water.wtr: truncated header ({len(data)} bytes)")
    (mapver, width, height, num) = struct.unpack("<HHHB", data[:7])
    if mapver != WATER_MAPVER:
        raise ParseError(source, f"water.wtr: bad magic {mapver}, expected {WATER_MAPVER}")
    rest = data[7:]
    want = width * height + num * 4
    if len(rest) != want:
        raise ParseError(
            source,
            f"water.wtr: body length {len(rest)} != {width}*{height} + {num}*4",
        )
    watermap = bytes(rest[: width * height])
    heights = list(struct.unpack(f"<{num}i", rest[width * height :])) if num else []
    return width, height, watermap, heights


# -- collision output header ------------------------------------------
def dump_collision_header(terrain_count_x: int, terrain_count_y: int) -> bytes:
    """Collision-output header (``M2CD`` + terrain counts).

    Mirrors ``MapManagerAccessor.cpp:891``. Per-object records require
    the property tree (absent GameLib) and are a later slice.
    """
    for name, v in (("terrain_count_x", terrain_count_x), ("terrain_count_y", terrain_count_y)):
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 0x7FFF:
            raise ValidationError(f"collision header: {name} {v!r} out of int16 range")
    return b"M2CD" + struct.pack("<hh", terrain_count_x, terrain_count_y)
