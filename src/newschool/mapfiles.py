"""Canonical map-file models + byte-exact serializers.

Every template below is verified against the reference save side:

* ``Setting.txt`` — ``MapAccessorOutdoor.cpp:107-152``
* ``MapProperty.txt`` — ``MapAccessorOutdoor.cpp:71-86``
* ``AreaProperty.txt`` — ``MapAccessorTerrain.cpp:1053-1060``
* ``AreaData.txt`` / ``AreaAmbienceData.txt`` — ``MapAccessorArea.cpp:689-819``
* ``regen.txt`` + ``MonsterArrange.txt`` — intended (currently dead-code)
  format, ``MapAccessorOutdoor.cpp:1714-1774``. The legacy build never
  writes these (``SaveMonsterAreaInfo`` returns ``true`` immediately);
  this module implements the verified intended layout as an explicit
  NEW capability — never claimed as legacy parity.
* ``AtlasInfo.txt`` — ``name x y w h id``,
  ``MapManagerAccessor.cpp:128-143``
* environment script — header + all groups/keys,
  ``MapManagerEnvironment.cpp:339-463``

Writer policy (see docs/audit/MIGRATION_POLICY.md):

* Writers reproduce the legacy templates **byte-for-byte** (same keys,
  order, blank lines, ``%f``/``%u`` formatting). This guarantee covers
  Setting/MapProperty/AreaProperty/AreaData/Ambience/regen/AtlasInfo.
  The environment writer additionally reproduces group/key order and
  blank placement, but its *indentation bytes* follow a documented
  new-file policy (one tab per level): the reference indent helper
  (``PrintfTabs``) lives in the absent library sources, so indent bytes
  are the one non-guaranteed element there.
* Unknown keys/lines/groups are never dropped: they are preserved in
  the model and re-emitted after the canonical block in original
  relative order.
* All floats are finite-checked; all integers range-checked. Failures
  raise :class:`ValidationError` / :class:`ParseError` with file + line.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .errors import ParseError, ValidationError
from .scripttext import CRLF, ScriptDocument, ScriptLine

# --------------------------------------------------------------------------
# shared value helpers
# --------------------------------------------------------------------------

_UINT32_MAX = 0xFFFFFFFF
_BYTE_MAX = 0xFF


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name}: expected a number, got {value!r}")
    value = float(value)
    if not math.isfinite(value):
        raise ValidationError(f"{name}: non-finite value {value!r} rejected")
    return value


def _uint(name: str, value: int, bits: int = 32) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{name}: expected an integer, got {value!r}")
    if not 0 <= value <= (1 << bits) - 1:
        raise ValidationError(f"{name}: {value} out of uint{bits} range")
    return value


def _int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{name}: expected an integer, got {value!r}")
    return value


def _clean_path(name: str, value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{name}: expected a non-empty path, got {value!r}")
    if "\n" in value or "\r" in value:
        raise ValidationError(f"{name}: path contains a line break: {value!r}")
    return value


def _parse_int(source: str, token: str, name: str, line_no: int | None = None) -> int:
    try:
        return int(token)
    except ValueError:
        raise ParseError(source, f"{name}: expected integer, got {token!r}", line_no) from None


def _parse_float(source: str, token: str, name: str, line_no: int | None = None) -> float:
    try:
        value = float(token)
    except ValueError:
        raise ParseError(source, f"{name}: expected float, got {token!r}", line_no) from None
    if not math.isfinite(value):
        raise ParseError(source, f"{name}: non-finite value {token!r}", line_no)
    return value


def _c_float(value: float) -> str:
    """Legacy ``%f`` formatting (six decimals, C-printf compatible)."""
    return "%f" % _finite("float", value)


def _c_float4(value: float) -> str:
    return "%.4f" % _finite("float", value)


def _unquote(source: str, token: str, name: str) -> str:
    if len(token) >= 2 and token.startswith('"') and token.endswith('"'):
        return token[1:-1]
    raise ParseError(source, f"{name}: expected quoted string, got {token!r}")


# --------------------------------------------------------------------------
# Setting.txt
# --------------------------------------------------------------------------

SETTING_MAGIC = ("ScriptType", ["MapSetting"])

SETTING_KNOWN_KEYS = {
    "ScriptType", "CellScale", "HeightScale", "ViewRadius",
    "MapSize", "BasePosition", "TextureSet", "Environment",
}


@dataclass
class MapSetting:
    cell_scale: int
    height_scale: float
    view_radius: int
    map_size_x: int
    map_size_y: int
    base_x: int
    base_y: int
    texture_set: str
    environment: str
    unknown: list[ScriptLine] = field(default_factory=list)

    def validate(self) -> None:
        _uint("CellScale", self.cell_scale)
        if self.cell_scale == 0:
            raise ValidationError("CellScale must be > 0")
        _finite("HeightScale", self.height_scale)
        _uint("ViewRadius", self.view_radius)
        if self.view_radius == 0:
            raise ValidationError("ViewRadius must be > 0")
        for name, dim in (("MapSizeX", self.map_size_x), ("MapSizeY", self.map_size_y)):
            _uint(name, dim)
            if not 1 <= dim <= 64:
                raise ValidationError(f"{name}={dim}: editor sanity bound is 1..64")
        _uint("BasePositionX", self.base_x)
        _uint("BasePositionY", self.base_y)
        _clean_path("TextureSet", self.texture_set)
        _clean_path("Environment", self.environment)


def parse_setting(doc: ScriptDocument) -> MapSetting:
    magic = doc.get_first("ScriptType")
    if magic != ["MapSetting"]:
        raise ParseError(doc.source, f"Setting.txt: bad magic {magic!r}, expected ['MapSetting']")
    cell = _parse_int(doc.source, _require_values(doc, "CellScale", 1)[0], "CellScale")
    height = _parse_float(doc.source, _require_values(doc, "HeightScale", 1)[0], "HeightScale")
    view = _parse_int(doc.source, _require_values(doc, "ViewRadius", 1)[0], "ViewRadius")
    size = _require_values(doc, "MapSize", 2)
    base = _require_values(doc, "BasePosition", 2)
    setting = MapSetting(
        cell_scale=cell,
        height_scale=height,
        view_radius=view,
        map_size_x=_parse_int(doc.source, size[0], "MapSizeX"),
        map_size_y=_parse_int(doc.source, size[1], "MapSizeY"),
        base_x=_parse_int(doc.source, base[0], "BasePositionX"),
        base_y=_parse_int(doc.source, base[1], "BasePositionY"),
        texture_set=_require_values(doc, "TextureSet", 1)[0],
        environment=_require_values(doc, "Environment", 1)[0],
        unknown=doc.unknown_lines(SETTING_KNOWN_KEYS),
    )
    setting.validate()
    return setting


def write_setting(setting: MapSetting, newline: bytes = CRLF) -> bytes:
    setting.validate()
    nl = newline.decode("ascii")
    out = [
        "ScriptType\tMapSetting",
        "",
        f"CellScale\t{setting.cell_scale}",
        f"HeightScale\t{_c_float(setting.height_scale)}",
        "",
        f"ViewRadius\t{setting.view_radius}",
        "",
        f"MapSize\t{setting.map_size_x}\t{setting.map_size_y}",
        f"BasePosition\t{setting.base_x}\t{setting.base_y}",
        f"TextureSet\t{setting.texture_set}",
        f"Environment\t{setting.environment}",
        "",
    ]
    for line in setting.unknown:
        out.append(line.text)
    return (nl.join(out) + nl).encode("utf-8")


# --------------------------------------------------------------------------
# MapProperty.txt
# --------------------------------------------------------------------------

MAP_TYPES = ("Indoor", "Outdoor", "Invalid")


@dataclass
class MapProperty:
    map_type: str
    unknown: list[ScriptLine] = field(default_factory=list)

    def validate(self) -> None:
        if self.map_type not in MAP_TYPES:
            raise ValidationError(f"MapType {self.map_type!r}: expected one of {MAP_TYPES}")


def parse_map_property(doc: ScriptDocument) -> MapProperty:
    magic = doc.get_first("ScriptType")
    if magic != ["MapProperty"]:
        raise ParseError(doc.source, f"MapProperty.txt: bad magic {magic!r}")
    raw = doc.require_first("MapType")
    if len(raw) != 1:
        raise ParseError(doc.source, f"MapProperty.txt: MapType needs 1 value, got {raw!r}")
    prop = MapProperty(map_type=raw[0], unknown=doc.unknown_lines({"ScriptType", "MapType"}))
    prop.validate()
    return prop


def write_map_property(prop: MapProperty, newline: bytes = CRLF) -> bytes:
    prop.validate()
    nl = newline.decode("ascii")
    out = ["ScriptType MapProperty", "", f'MapType "{prop.map_type}"', ""]
    for line in prop.unknown:
        out.append(line.text)
    return (nl.join(out) + nl).encode("utf-8")


# --------------------------------------------------------------------------
# AreaProperty.txt
# --------------------------------------------------------------------------

@dataclass
class AreaProperty:
    area_name: str
    num_water: int
    unknown: list[ScriptLine] = field(default_factory=list)

    def validate(self) -> None:
        if not isinstance(self.area_name, str):
            raise ValidationError(f"AreaName: expected string, got {self.area_name!r}")
        if '"' in self.area_name or "\n" in self.area_name or "\r" in self.area_name:
            raise ValidationError("AreaName must not contain quotes or line breaks")
        _uint("NumWater", self.num_water, 8)


def parse_area_property(doc: ScriptDocument) -> AreaProperty:
    magic = doc.get_first("ScriptType")
    if magic != ["AreaProperty"]:
        raise ParseError(doc.source, f"AreaProperty.txt: bad magic {magic!r}")
    name_tok = _require_values(doc, "AreaName", 1)
    prop = AreaProperty(
        area_name=name_tok[0],
        num_water=_parse_int(doc.source, _require_values(doc, "NumWater", 1)[0], "NumWater"),
        unknown=doc.unknown_lines({"ScriptType", "AreaName", "NumWater"}),
    )
    prop.validate()
    return prop


def write_area_property(prop: AreaProperty, newline: bytes = CRLF) -> bytes:
    prop.validate()
    nl = newline.decode("ascii")
    out = [
        "ScriptType AreaProperty",
        "",
        f'AreaName "{prop.area_name}"',
        "",
        f"NumWater {prop.num_water}",
        "",
    ]
    for line in prop.unknown:
        out.append(line.text)
    return (nl.join(out) + nl).encode("utf-8")


# --------------------------------------------------------------------------
# AreaData.txt / AreaAmbienceData.txt
# --------------------------------------------------------------------------

# Editor-side safety bound for portal lists. The reference capacity
# (PORTAL_ID_MAX_NUM) lives in the absent headers, so no legacy value is
# assumed; this bound only guards the editor against absurd input.
MAX_PORTALS_SAFETY = 32


@dataclass
class ObjectInstance:
    x: float
    y: float
    z: float
    crc: int
    yaw: float
    pitch: float
    roll: float
    height_bias: float
    portals: list[int] = field(default_factory=list)

    def validate(self) -> None:
        _finite("Position.x", self.x)
        _finite("Position.y", self.y)
        _finite("Position.z", self.z)
        _uint("CRC", self.crc)
        _finite("Yaw", self.yaw)
        _finite("Pitch", self.pitch)
        _finite("Roll", self.roll)
        _finite("HeightBias", self.height_bias)
        if len(self.portals) > MAX_PORTALS_SAFETY:
            raise ValidationError(f"portal list length {len(self.portals)} exceeds safety bound")
        for p in self.portals:
            _uint("PortalID", p, 8)
            if p == 0:
                raise ValidationError("portal id 0 is the legacy terminator and cannot be stored")

    def normalized_portals(self) -> list[int]:
        """Legacy write normalization: first-seen order, duplicates dropped
        (reference: MapAccessorArea.cpp:727-746 — dedupe set, stop at 0)."""
        seen: list[int] = []
        for p in self.portals:
            self.validate_portal(p)
            if p not in seen:
                seen.append(p)
        return seen

    @staticmethod
    def validate_portal(p: int) -> None:
        _uint("PortalID", p, 8)
        if p == 0:
            raise ValidationError("portal id 0 is the legacy terminator and cannot be stored")


@dataclass
class AmbienceInstance:
    x: float
    y: float
    z: float
    crc: int
    range: int
    max_volume_pct: float

    def validate(self) -> None:
        _finite("Position.x", self.x)
        _finite("Position.y", self.y)
        _finite("Position.z", self.z)
        _uint("CRC", self.crc)
        _uint("Range", self.range)
        _finite("MaxVolumeAreaPercentage", self.max_volume_pct)


def _parse_pos(source: str, parts: list[str], what: str) -> tuple[float, float, float]:
    if len(parts) != 3:
        raise ParseError(source, f"{what}: expected 3 position values, got {parts!r}")
    return (
        _parse_float(source, parts[0], f"{what}.x"),
        _parse_float(source, parts[1], f"{what}.y"),
        _parse_float(source, parts[2], f"{what}.z"),
    )


def _write_object_block(obj: ObjectInstance, index: int) -> list[str]:
    obj.validate()
    block = [
        f"Start Object{index:03d}",
        f"    {_c_float(obj.x)} {_c_float(obj.y)} {_c_float(obj.z)}",
        f"    {obj.crc}",
        f"    {_c_float(obj.yaw)}#{_c_float(obj.pitch)}#{_c_float(obj.roll)}",
        f"    {_c_float(obj.height_bias)}",
    ]
    portals = obj.normalized_portals()
    if portals:
        block.append("   " + "".join(f" {p}" for p in portals))
    block.append("End Object")
    return block


def _write_ambience_block(obj: AmbienceInstance, index: int) -> list[str]:
    obj.validate()
    return [
        f"Start Object{index:03d}",
        f"    {_c_float(obj.x)} {_c_float(obj.y)} {_c_float(obj.z)}",
        f"    {obj.crc}",
        f"    {obj.range}",
        f"    {_c_float(obj.max_volume_pct)}",
        "End Object",
    ]


def write_area_data(objects: list[ObjectInstance], newline: bytes = CRLF) -> bytes:
    nl = newline.decode("ascii")
    out = ["AreaDataFile", ""]
    for i, obj in enumerate(objects):
        out.extend(_write_object_block(obj, i))
    out += ["", f"ObjectCount {len(objects)}"]
    return (nl.join(out) + nl).encode("utf-8")


def write_area_ambience(objects: list[AmbienceInstance], newline: bytes = CRLF) -> bytes:
    nl = newline.decode("ascii")
    out = ["AreaAmbienceDataFile", ""]
    for i, obj in enumerate(objects):
        out.extend(_write_ambience_block(obj, i))
    out += ["", f"ObjectCount {len(objects)}"]
    return (nl.join(out) + nl).encode("utf-8")


def _body_lines(doc: ScriptDocument) -> list[ScriptLine]:
    return [line for line in doc.lines if line.kind in ("kv", "indented")]


def parse_area_data(doc: ScriptDocument) -> list[ObjectInstance]:
    first = doc.lines[0].text if doc.lines else ""
    if first != "AreaDataFile":
        raise ParseError(doc.source, f"AreaData.txt: bad magic {first!r}, expected 'AreaDataFile'")
    lines = _body_lines(doc)
    if not lines or lines[0].text != "AreaDataFile":
        raise ParseError(doc.source, "AreaData.txt: magic record missing")
    idx = 1
    objects: list[ObjectInstance] = []
    while idx < len(lines):
        text = lines[idx].text
        if text.startswith("ObjectCount"):
            parts = text.split()
            if len(parts) != 2:
                raise ParseError(doc.source, f"AreaData.txt: malformed {text!r}")
            want = _parse_int(doc.source, parts[1], "ObjectCount")
            if want != len(objects):
                raise ParseError(
                    doc.source,
                    f"AreaData.txt: ObjectCount {want} != parsed {len(objects)}",
                )
            idx += 1
            if idx != len(lines):
                raise ParseError(doc.source, "AreaData.txt: trailing records after ObjectCount")
            break
        if text != f"Start Object{len(objects):03d}":
            raise ParseError(
                doc.source,
                f"AreaData.txt: expected 'Start Object{len(objects):03d}', got {text!r}",
            )
        try:
            pos_line = lines[idx + 1].text.split()
            crc_line = lines[idx + 2].text.split()
            rot_line = lines[idx + 3].text.split()
            bias_line = lines[idx + 4].text.split()
        except IndexError:
            raise ParseError(doc.source, "AreaData.txt: truncated object block") from None
        x, y, z = _parse_pos(doc.source, pos_line, "Position")
        if len(crc_line) != 1:
            raise ParseError(doc.source, f"AreaData.txt: malformed CRC line {crc_line!r}")
        crc = _parse_int(doc.source, crc_line[0], "CRC")
        if len(rot_line) != 1 or rot_line[0].count("#") != 2:
            raise ParseError(doc.source, f"AreaData.txt: malformed rotation line {rot_line!r}")
        yaw_s, pitch_s, roll_s = rot_line[0].split("#")
        yaw = _parse_float(doc.source, yaw_s, "Yaw")
        pitch = _parse_float(doc.source, pitch_s, "Pitch")
        roll = _parse_float(doc.source, roll_s, "Roll")
        if len(bias_line) != 1:
            raise ParseError(doc.source, f"AreaData.txt: malformed height-bias line {bias_line!r}")
        bias = _parse_float(doc.source, bias_line[0], "HeightBias")
        idx += 5
        portals: list[int] = []
        if idx < len(lines) and lines[idx].text not in ("End Object",) and not lines[idx].text.startswith("Start Object") and not lines[idx].text.startswith("ObjectCount"):
            for tok in lines[idx].text.split():
                portals.append(_parse_int(doc.source, tok, "PortalID"))
            # The reference writer stops at the first 0 byte and therefore
            # can never emit a 0 portal id (MapAccessorArea.cpp:733-738);
            # a 0 here means the file did not come from that writer.
            if 0 in portals:
                raise ParseError(
                    doc.source,
                    f"AreaData.txt: portal id 0 is the legacy terminator and "
                    f"cannot appear in data: {portals!r}",
                )
            idx += 1
        if idx >= len(lines) or lines[idx].text != "End Object":
            got = lines[idx].text if idx < len(lines) else "<eof>"
            raise ParseError(doc.source, f"AreaData.txt: expected 'End Object', got {got!r}")
        idx += 1
        obj = ObjectInstance(x=x, y=y, z=z, crc=crc, yaw=yaw, pitch=pitch,
                             roll=roll, height_bias=bias, portals=portals)
        obj.validate()
        objects.append(obj)
    else:
        raise ParseError(doc.source, "AreaData.txt: missing ObjectCount trailer")
    return objects


def parse_area_ambience(doc: ScriptDocument) -> list[AmbienceInstance]:
    first = doc.lines[0].text if doc.lines else ""
    if first != "AreaAmbienceDataFile":
        raise ParseError(doc.source, f"AreaAmbienceData.txt: bad magic {first!r}")
    lines = _body_lines(doc)
    idx = 1
    objects: list[AmbienceInstance] = []
    while idx < len(lines):
        text = lines[idx].text
        if text.startswith("ObjectCount"):
            parts = text.split()
            if len(parts) != 2:
                raise ParseError(doc.source, f"AreaAmbienceData.txt: malformed {text!r}")
            want = _parse_int(doc.source, parts[1], "ObjectCount")
            if want != len(objects):
                raise ParseError(
                    doc.source,
                    f"AreaAmbienceData.txt: ObjectCount {want} != parsed {len(objects)}",
                )
            idx += 1
            if idx != len(lines):
                raise ParseError(doc.source, "AreaAmbienceData.txt: trailing records after ObjectCount")
            break
        if text != f"Start Object{len(objects):03d}":
            raise ParseError(
                doc.source,
                f"AreaAmbienceData.txt: expected 'Start Object{len(objects):03d}', got {text!r}",
            )
        try:
            pos_line = lines[idx + 1].text.split()
            crc_line = lines[idx + 2].text.split()
            range_line = lines[idx + 3].text.split()
            pct_line = lines[idx + 4].text.split()
            end_line = lines[idx + 5].text
        except IndexError:
            raise ParseError(doc.source, "AreaAmbienceData.txt: truncated object block") from None
        x, y, z = _parse_pos(doc.source, pos_line, "Position")
        if len(crc_line) != 1 or len(range_line) != 1 or len(pct_line) != 1:
            raise ParseError(doc.source, "AreaAmbienceData.txt: malformed ambience block")
        if end_line != "End Object":
            raise ParseError(doc.source, f"AreaAmbienceData.txt: expected 'End Object', got {end_line!r}")
        obj = AmbienceInstance(
            x=x, y=y, z=z,
            crc=_parse_int(doc.source, crc_line[0], "CRC"),
            range=_parse_int(doc.source, range_line[0], "Range"),
            max_volume_pct=_parse_float(doc.source, pct_line[0], "MaxVolumeAreaPercentage"),
        )
        obj.validate()
        objects.append(obj)
        idx += 6
    else:
        raise ParseError(doc.source, "AreaAmbienceData.txt: missing ObjectCount trailer")
    return objects


# --------------------------------------------------------------------------
# regen.txt + MonsterArrange.txt (NEW capability — see module docstring)
# --------------------------------------------------------------------------

REGEN_HEADER = "//type\tcx\tcy\tsx\tsy\tz\tdir\ttime\tpercent\tcount\tvnum"
REGEN_RULER = "//" + "-" * 83
REGEN_TYPES = ("m", "g")


@dataclass
class RegenEntry:
    kind: str  # "m" (monster) or "g" (group)
    cx: int
    cy: int
    sx: int
    sy: int
    z: int = 0
    direction: int = 0
    time_min: int = 1
    percent: int = 100
    count: int = 1
    vnum: int = 0

    def validate(self) -> None:
        if self.kind not in REGEN_TYPES:
            raise ValidationError(f"regen kind {self.kind!r}: expected one of {REGEN_TYPES}")
        for name in ("cx", "cy", "sx", "sy", "z", "direction", "time_min", "percent", "vnum"):
            _int(f"regen.{name}", getattr(self, name))
        _uint("regen.count", self.count)
        _uint("regen.vnum", self.vnum)
        if self.time_min < 0 or self.percent < 0:
            raise ValidationError("regen time/percent must be >= 0")


def write_regen(entries: list[RegenEntry], newline: bytes = CRLF) -> bytes:
    nl = newline.decode("ascii")
    out = [REGEN_HEADER, REGEN_RULER]
    for e in entries:
        e.validate()
        out.append(
            f"{e.kind}\t{e.cx}\t{e.cy}\t{e.sx}\t{e.sy}\t{e.z}\t{e.direction}\t"
            f"{e.time_min}m\t{e.percent}\t{e.count}\t{e.vnum}"
        )
    return (nl.join(out) + nl).encode("utf-8")


def parse_regen(doc: ScriptDocument) -> list[RegenEntry]:
    entries: list[RegenEntry] = []
    for line in doc.lines:
        if line.kind in ("blank", "comment"):
            continue
        parts = line.text.split()
        if len(parts) != 11:
            raise ParseError(
                doc.source,
                f"regen.txt: expected 11 columns, got {len(parts)}: {line.text!r}",
                line.number,
            )
        kind = parts[0]
        cols = parts[1:]  # cx cy sx sy z dir time percent count vnum
        time_tok = cols[6]
        if not time_tok.endswith("m"):
            raise ParseError(
                doc.source,
                f"regen.txt: time column needs '<int>m' form, got {time_tok!r}",
                line.number,
            )
        nums = [
            _parse_int(doc.source, (tok[:-1] if idx == 6 else tok), "regen", line.number)
            for idx, tok in enumerate(cols)
        ]
        entry = RegenEntry(kind=kind, cx=nums[0], cy=nums[1], sx=nums[2], sy=nums[3],
                           z=nums[4], direction=nums[5], time_min=nums[6],
                           percent=nums[7], count=nums[8], vnum=nums[9])
        entry.validate()
        entries.append(entry)
    return entries


def write_monster_arrange(vnums: list[int], newline: bytes = CRLF) -> bytes:
    for v in vnums:
        _uint("MonsterArrange vnum", v)
    uniq = sorted(set(vnums))
    nl = newline.decode("ascii")
    return (nl.join(str(v) for v in uniq) + nl).encode("utf-8")


def parse_monster_arrange(doc: ScriptDocument) -> list[int]:
    out: list[int] = []
    for line in doc.lines:
        if line.kind in ("blank", "comment"):
            continue
        parts = line.text.split()
        if len(parts) != 1:
            raise ParseError(doc.source, f"MonsterArrange.txt: malformed {line.text!r}", line.number)
        out.append(_parse_int(doc.source, parts[0], "vnum"))
    for v in out:
        _uint("MonsterArrange vnum", v)
    return out


# --------------------------------------------------------------------------
# AtlasInfo.txt
# --------------------------------------------------------------------------

@dataclass
class AtlasEntry:
    name: str
    x: int
    y: int
    w: int
    h: int
    map_id: int

    def validate(self) -> None:
        _clean_path("AtlasInfo.name", self.name)
        for attr in ("x", "y", "w", "h", "map_id"):
            _int(f"AtlasInfo.{attr}", getattr(self, attr))


def parse_atlas_info(doc: ScriptDocument) -> list[AtlasEntry]:
    entries: list[AtlasEntry] = []
    for line in doc.lines:
        if line.kind in ("blank", "comment"):
            continue
        parts = line.text.split()
        if len(parts) != 6:
            raise ParseError(doc.source, f"AtlasInfo.txt: expected 6 columns, got {parts!r}", line.number)
        entry = AtlasEntry(
            name=parts[0],
            x=_parse_int(doc.source, parts[1], "x"),
            y=_parse_int(doc.source, parts[2], "y"),
            w=_parse_int(doc.source, parts[3], "w"),
            h=_parse_int(doc.source, parts[4], "h"),
            map_id=_parse_int(doc.source, parts[5], "id"),
        )
        entry.validate()
        entries.append(entry)
    return entries


def write_atlas_info(entries: list[AtlasEntry], newline: bytes = CRLF) -> bytes:
    nl = newline.decode("ascii")
    out = []
    for e in entries:
        e.validate()
        out.append(f"{e.name} {e.x} {e.y} {e.w} {e.h} {e.map_id}")
    return ((nl.join(out) + nl) if out else "").encode("utf-8")


# --------------------------------------------------------------------------
# environment script (full verified vocabulary)
# --------------------------------------------------------------------------

# NOTE on the magic: the reference writes "EnvrionmentData" (transposed i/o).
# It is reproduced byte-for-byte for compatibility; the reader also accepts
# the correctly spelled variant.
ENV_MAGIC_WRITTEN = "EnvrionmentData"
ENV_MAGIC_TOLERATED = "EnvironmentData"
ENV_VERSION = 1.0


@dataclass
class Rgba:
    r: float
    g: float
    b: float
    a: float

    def validate(self, name: str = "color") -> None:
        for comp, v in (("r", self.r), ("g", self.g), ("b", self.b), ("a", self.a)):
            _finite(f"{name}.{comp}", v)

    def values(self) -> list[str]:
        return [_c_float(self.r), _c_float(self.g), _c_float(self.b), _c_float(self.a)]


def _parse_rgba(source: str, parts: list[str], name: str) -> Rgba:
    if len(parts) != 4:
        raise ParseError(source, f"environment: {name} needs 4 values, got {parts!r}")
    color = Rgba(*(_parse_float(source, p, f"{name}") for p in parts))
    color.validate(name)
    return color


def _parse_vec3(source: str, parts: list[str], name: str) -> tuple[float, float, float]:
    if len(parts) != 3:
        raise ParseError(source, f"environment: {name} needs 3 values, got {parts!r}")
    return (
        _parse_float(source, parts[0], f"{name}.x"),
        _parse_float(source, parts[1], f"{name}.y"),
        _parse_float(source, parts[2], f"{name}.z"),
    )


@dataclass
class EnvironmentData:
    script_version: float = ENV_VERSION
    dir_light_direction: tuple[float, float, float] = (0.0, -1.0, 0.0)
    background_enable: int = 1
    background_diffuse: Rgba = field(default_factory=lambda: Rgba(1.0, 1.0, 1.0, 1.0))
    background_ambient: Rgba = field(default_factory=lambda: Rgba(0.5, 0.5, 0.5, 1.0))
    character_enable: int = 1
    character_diffuse: Rgba = field(default_factory=lambda: Rgba(1.0, 1.0, 1.0, 1.0))
    character_ambient: Rgba = field(default_factory=lambda: Rgba(0.5, 0.5, 0.5, 1.0))
    material_diffuse: Rgba = field(default_factory=lambda: Rgba(1.0, 1.0, 1.0, 1.0))
    material_ambient: Rgba = field(default_factory=lambda: Rgba(0.5, 0.5, 0.5, 1.0))
    material_emissive: Rgba = field(default_factory=lambda: Rgba(0.0, 0.0, 0.0, 1.0))
    fog_enable: int = 0
    fog_near: float = 50.0
    fog_far: float = 500.0
    fog_color: Rgba = field(default_factory=lambda: Rgba(0.8, 0.85, 1.0, 1.0))
    filter_enable: int = 0
    filter_color: Rgba = field(default_factory=lambda: Rgba(1.0, 1.0, 1.0, 1.0))
    filter_alpha_src: int = 0
    filter_alpha_dest: int = 0
    sky_texture_mode: int = 1
    sky_scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    sky_gradient_upper: int = 0
    sky_gradient_lower: int = 0
    sky_faces: list[str] = field(default_factory=lambda: [""] * 6)  # front/back/left/right/top/bottom
    cloud_scale: tuple[float, float] = (1.0, 1.0)
    cloud_height: float = 100.0
    cloud_tex_scale: tuple[float, float] = (1.0, 1.0)
    cloud_speed: tuple[float, float] = (0.01, 0.01)
    cloud_texture: str = ""
    cloud_first: Rgba = field(default_factory=lambda: Rgba(1.0, 1.0, 1.0, 1.0))
    cloud_second: Rgba = field(default_factory=lambda: Rgba(1.0, 1.0, 1.0, 1.0))
    gradients: list[tuple[Rgba, Rgba]] = field(default_factory=list)
    lens_enable: int = 0
    lens_brightness: Rgba = field(default_factory=lambda: Rgba(1.0, 1.0, 1.0, 1.0))
    lens_max_brightness: float = 1.0
    lens_main_enable: int = 0
    lens_main_texture: str = ""
    lens_main_size: float = 1.0
    unknown: list[ScriptLine] = field(default_factory=list)
    # Unknown Group blocks captured verbatim (incl. braces), file order.
    unknown_groups: list[list[ScriptLine]] = field(default_factory=list)

    def validate(self) -> None:
        _finite("ScriptVersion", self.script_version)
        for v in self.dir_light_direction:
            _finite("DirectionalLight.Direction", v)
        # Legacy %d BOOL fields: only 0/1 round-trip through the writer.
        for name in ("BackgroundEnable", "CharacterEnable", "FogEnable", "FilterEnable",
                     "SkyTextureMode", "LensEnable", "LensMainEnable"):
            value = getattr(self, _ENV_ATTR[name])
            _uint(name, value)
            if value not in (0, 1):
                raise ValidationError(f"{name}={value}: BOOL needs 0/1")
        for cname in ("background_diffuse", "background_ambient", "character_diffuse",
                      "character_ambient", "material_diffuse", "material_ambient",
                      "material_emissive", "fog_color", "filter_color",
                      "cloud_first", "cloud_second", "lens_brightness"):
            getattr(self, cname).validate(cname)
        _finite("FogNear", self.fog_near)
        _finite("FogFar", self.fog_far)
        if self.fog_far < self.fog_near:
            raise ValidationError(f"FogFar {self.fog_far} < FogNear {self.fog_near}")
        for byte_name in ("filter_alpha_src", "filter_alpha_dest",
                          "sky_gradient_upper", "sky_gradient_lower"):
            _uint(byte_name, getattr(self, byte_name), 8)
        for v in self.sky_scale:
            _finite("SkyBox.Scale", v)
        if len(self.sky_faces) != 6:
            raise ValidationError(f"SkyBox needs 6 face textures, got {len(self.sky_faces)}")
        for v in self.cloud_scale + self.cloud_tex_scale + self.cloud_speed:
            _finite("SkyBox.Cloud", v)
        _finite("CloudHeight", self.cloud_height)
        _finite("LensMaxBrightness", self.lens_max_brightness)
        _finite("LensMainSize", self.lens_main_size)
        for first, second in self.gradients:
            first.validate("Gradient.First")
            second.validate("Gradient.Second")


_ENV_ATTR = {
    "BackgroundEnable": "background_enable",
    "CharacterEnable": "character_enable",
    "FogEnable": "fog_enable",
    "FilterEnable": "filter_enable",
    "SkyTextureMode": "sky_texture_mode",
    "LensEnable": "lens_enable",
    "LensMainEnable": "lens_main_enable",
}

_SKY_FACE_KEYS = (
    "FrontFaceFileName", "BackFaceFileName", "LeftFaceFileName",
    "RightFaceFileName", "TopFaceFileName", "BottomFaceFileName",
)


class _EnvCursor:
    """Whitespace-tolerant sequential reader over environment records."""

    def __init__(self, doc: ScriptDocument):
        self.doc = doc
        self.recs: list[tuple[str, list[str], int]] = []  # (key, values, line_no)
        for line in doc.lines:
            if line.kind in ("kv", "indented") and line.key is not None:
                self.recs.append((line.key, line.values, line.number))
        self.pos = 0
        self.consumed: set[int] = set()

    def take(self, key: str) -> tuple[list[str], int]:
        for i in range(self.pos, len(self.recs)):
            if i in self.consumed:
                continue
            if self.recs[i][0] == key:
                self.consumed.add(i)
                self.pos = i + 1
                return self.recs[i][1], self.recs[i][2]
        raise ParseError(self.doc.source, f"environment: required key {key!r} not found")

    def take_opt(self, key: str) -> tuple[list[str], int] | None:
        for i in range(self.pos, len(self.recs)):
            if i in self.consumed:
                continue
            if self.recs[i][0] == key:
                self.consumed.add(i)
                self.pos = i + 1
                return self.recs[i][1], self.recs[i][2]
        return None

    # Group names of the verified template, by parent (None = top level).
    KNOWN_GROUPS: dict[str | None, set[str]] = {
        None: {"DirectionalLight", "Material", "Fog", "Filter", "SkyBox", "LensFlare"},
        "DirectionalLight": {"Background", "Character"},
    }

    def mark_unknown_groups(self) -> list[list[ScriptLine]]:
        """Capture unknown ``Group`` blocks verbatim (incl. braces).

        Blocks are marked consumed so their inner keys can never be
        mistaken for known fields. Returns the blocks in file order for
        verbatim re-emission after the canonical template.
        """
        blocks: list[list[ScriptLine]] = []
        # line-number -> rec index, for consumption marking
        by_number = {ln: i for i, (_k, _v, ln) in enumerate(self.recs)}
        # brace depth over kv/indented lines only
        depth = 0
        group_stack: list[str] = []
        i = 0
        lines = self.doc.lines
        while i < len(lines):
            line = lines[i]
            if line.kind in ("kv", "indented") and line.key == "Group" and line.values:
                name = line.values[0]
                parent = group_stack[-1] if group_stack else None
                known = name in self.KNOWN_GROUPS.get(parent, set())
                # find matching close brace at this depth
                inner_depth = depth
                j = i + 1
                closed = False
                while j < len(lines):
                    t = lines[j].text.strip()
                    if t == "{":
                        inner_depth += 1
                    elif t == "}":
                        # The group's own opening brace raised the level to
                        # depth+1, so its match is found at that level.
                        if inner_depth == depth + 1:
                            closed = True
                            break
                        inner_depth -= 1
                    j += 1
                if not closed:
                    raise ParseError(
                        self.doc.source,
                        f"environment: Group {name!r} is never closed",
                        line.number,
                    )
                if known:
                    group_stack.append(name)
                    # walk the canonical parser over it later; skip ahead
                    # past the Group line only (depth tracked inline below)
                    i += 1
                    continue
                block = lines[i : j + 1]
                blocks.append(block)
                for bline in block:
                    if bline.number in by_number:
                        self.consumed.add(by_number[bline.number])
                i = j + 1
                continue
            if line.kind in ("kv", "indented"):
                t = line.text.strip()
                if t == "{":
                    depth += 1
                elif t == "}":
                    depth -= 1
                    if group_stack and depth < len(group_stack):
                        group_stack.pop()
            i += 1
        return blocks

    def take_float_row(self, what: str) -> "Rgba | None":
        """Next bare rgba data row, or None at a structural boundary.

        ``{`` noise lines are skipped; ``}`` / ``Group`` / ``List``
        terminate the list. Any other keyword inside the list is a
        malformed file, reported loudly.
        """
        for i in range(self.pos, len(self.recs)):
            if i in self.consumed:
                continue
            key, vals, _ln = self.recs[i]
            if key == "{":
                self.consumed.add(i)
                self.pos = i + 1
                continue
            if key in ("}", "Group", "List"):
                return None
            try:
                float(key)
            except ValueError:
                raise ParseError(
                    self.doc.source, f"environment: unexpected {key!r} inside {what}"
                ) from None
            self.consumed.add(i)
            self.pos = i + 1
            return _parse_rgba(self.doc.source, [key] + vals, what)
        return None

    def unknowns(self) -> list[ScriptLine]:
        used_lines = {self.recs[i][2] for i in self.consumed}
        structural = {"Group", "{", "}", "List"}
        out = []
        for line in self.doc.lines:
            if line.kind == "comment":
                out.append(line)
            elif line.kind in ("kv", "indented") and line.number not in used_lines:
                if line.key in structural:
                    continue
                try:
                    float(line.key)  # bare rgba data row, not a record
                    continue
                except (ValueError, TypeError):
                    pass
                out.append(line)
        return out


def _need(source: str, values: list[str], key: str, n: int) -> list[str]:
    if len(values) != n:
        raise ParseError(source, f"environment: {key} needs {n} values, got {values!r}")
    return values


def _require_values(doc: "ScriptDocument", key: str, n: int) -> list[str]:
    """Required record with exact arity — bare ``Key`` lines become
    :class:`ParseError` instead of an :exc:`IndexError`."""
    values = doc.require_first(key)
    if len(values) != n:
        raise ParseError(doc.source, f"{key}: needs {n} value(s), got {values!r}")
    return values


def _parse_bool(source: str, token: str, name: str) -> int:
    """Legacy ``%d`` BOOL field: only 0/1 are representable on write."""
    value = _parse_int(source, token, name)
    if value not in (0, 1):
        raise ParseError(source, f"{name}: BOOL needs 0/1, got {value}")
    return value


def parse_environment(doc: ScriptDocument) -> EnvironmentData:
    magic = doc.get_first("ScriptType")
    if magic not in ([ENV_MAGIC_WRITTEN], [ENV_MAGIC_TOLERATED]):
        raise ParseError(doc.source, f"environment: bad magic {magic!r}")
    cur = _EnvCursor(doc)
    cur.take("ScriptType")  # consume the magic so it is not re-emitted as unknown
    unknown_groups = cur.mark_unknown_groups()  # pre-consume unknown blocks first
    env = EnvironmentData()
    ver, _ = cur.take("ScriptVersion")
    env.script_version = _parse_float(doc.source, _need(doc.source, ver, "ScriptVersion", 1)[0], "ScriptVersion")
    d, _ = cur.take("Direction")
    env.dir_light_direction = _parse_vec3(doc.source, _need(doc.source, d, "Direction", 3), "Direction")
    e, _ = cur.take("Enable")
    env.background_enable = _parse_bool(doc.source, _need(doc.source, e, "Background.Enable", 1)[0], "Background.Enable")
    df, _ = cur.take("Diffuse")
    env.background_diffuse = _parse_rgba(doc.source, _need(doc.source, df, "Background.Diffuse", 4), "Background.Diffuse")
    am, _ = cur.take("Ambient")
    env.background_ambient = _parse_rgba(doc.source, _need(doc.source, am, "Background.Ambient", 4), "Background.Ambient")
    e, _ = cur.take("Enable")
    env.character_enable = _parse_bool(doc.source, _need(doc.source, e, "Character.Enable", 1)[0], "Character.Enable")
    df, _ = cur.take("Diffuse")
    env.character_diffuse = _parse_rgba(doc.source, _need(doc.source, df, "Character.Diffuse", 4), "Character.Diffuse")
    am, _ = cur.take("Ambient")
    env.character_ambient = _parse_rgba(doc.source, _need(doc.source, am, "Character.Ambient", 4), "Character.Ambient")
    df, _ = cur.take("Diffuse")
    env.material_diffuse = _parse_rgba(doc.source, _need(doc.source, df, "Material.Diffuse", 4), "Material.Diffuse")
    am, _ = cur.take("Ambient")
    env.material_ambient = _parse_rgba(doc.source, _need(doc.source, am, "Material.Ambient", 4), "Material.Ambient")
    em, _ = cur.take("Emissive")
    env.material_emissive = _parse_rgba(doc.source, _need(doc.source, em, "Material.Emissive", 4), "Material.Emissive")
    e, _ = cur.take("Enable")
    env.fog_enable = _parse_bool(doc.source, _need(doc.source, e, "Fog.Enable", 1)[0], "Fog.Enable")
    nd, _ = cur.take("NearDistance")
    env.fog_near = _parse_float(doc.source, _need(doc.source, nd, "Fog.NearDistance", 1)[0], "Fog.NearDistance")
    fd, _ = cur.take("FarDistance")
    env.fog_far = _parse_float(doc.source, _need(doc.source, fd, "Fog.FarDistance", 1)[0], "Fog.FarDistance")
    co, _ = cur.take("Color")
    env.fog_color = _parse_rgba(doc.source, _need(doc.source, co, "Fog.Color", 4), "Fog.Color")
    e, _ = cur.take("Enable")
    env.filter_enable = _parse_bool(doc.source, _need(doc.source, e, "Filter.Enable", 1)[0], "Filter.Enable")
    co, _ = cur.take("Color")
    env.filter_color = _parse_rgba(doc.source, _need(doc.source, co, "Filter.Color", 4), "Filter.Color")
    asrc, _ = cur.take("AlphaSrc")
    env.filter_alpha_src = _parse_int(doc.source, _need(doc.source, asrc, "Filter.AlphaSrc", 1)[0], "AlphaSrc")
    adst, _ = cur.take("AlphaDest")
    env.filter_alpha_dest = _parse_int(doc.source, _need(doc.source, adst, "Filter.AlphaDest", 1)[0], "AlphaDest")
    tx, _ = cur.take("bTextureRenderMode")
    env.sky_texture_mode = _parse_bool(doc.source, _need(doc.source, tx, "SkyBox.bTextureRenderMode", 1)[0], "SkyBox.bTextureRenderMode")
    sc, _ = cur.take("Scale")
    env.sky_scale = _parse_vec3(doc.source, _need(doc.source, sc, "SkyBox.Scale", 3), "SkyBox.Scale")
    gu, _ = cur.take("GradientLevelUpper")
    env.sky_gradient_upper = _parse_int(doc.source, _need(doc.source, gu, "GradientLevelUpper", 1)[0], "GradientLevelUpper")
    gl, _ = cur.take("GradientLevelLower")
    env.sky_gradient_lower = _parse_int(doc.source, _need(doc.source, gl, "GradientLevelLower", 1)[0], "GradientLevelLower")
    faces: list[str] = []
    for fk in _SKY_FACE_KEYS:
        fv, _ = cur.take(fk)
        faces.append(_need(doc.source, fv, f"SkyBox.{fk}", 1)[0])
    env.sky_faces = faces
    cs, _ = cur.take("CloudScale")
    csp = _need(doc.source, cs, "CloudScale", 2)
    env.cloud_scale = (_parse_float(doc.source, csp[0], "CloudScale.x"),
                       _parse_float(doc.source, csp[1], "CloudScale.y"))
    ch, _ = cur.take("CloudHeight")
    env.cloud_height = _parse_float(doc.source, _need(doc.source, ch, "CloudHeight", 1)[0], "CloudHeight")
    cts, _ = cur.take("CloudTextureScale")
    ctp = _need(doc.source, cts, "CloudTextureScale", 2)
    env.cloud_tex_scale = (_parse_float(doc.source, ctp[0], "CloudTextureScale.x"),
                           _parse_float(doc.source, ctp[1], "CloudTextureScale.y"))
    cv, _ = cur.take("CloudSpeed")
    cvp = _need(doc.source, cv, "CloudSpeed", 2)
    env.cloud_speed = (_parse_float(doc.source, cvp[0], "CloudSpeed.x"),
                       _parse_float(doc.source, cvp[1], "CloudSpeed.y"))
    ct, _ = cur.take("CloudTextureFileName")
    env.cloud_texture = _need(doc.source, ct, "CloudTextureFileName", 1)[0]
    # List CloudColor: marker + two bare rgba rows
    marker, _ = cur.take("List")
    if marker != ["CloudColor"]:
        raise ParseError(doc.source, f"environment: expected 'List CloudColor', got {marker!r}")
    first_row = cur.take_float_row("CloudColor")
    second_row = cur.take_float_row("CloudColor")
    if first_row is None or second_row is None:
        raise ParseError(doc.source, "environment: List CloudColor needs 2 rgba rows")
    env.cloud_first, env.cloud_second = first_row, second_row
    # Optional List Gradient: pairs of rgba rows
    gradients: list[tuple[Rgba, Rgba]] = []
    marker_opt = cur.take_opt("List")
    if marker_opt is not None:
        if marker_opt[0] != ["Gradient"]:
            raise ParseError(doc.source, f"environment: expected 'List Gradient', got {marker_opt[0]!r}")
        while True:
            first = cur.take_float_row("Gradient")
            if first is None:
                break
            second = cur.take_float_row("Gradient")
            if second is None:
                raise ParseError(doc.source, "environment: List Gradient needs rgba pairs")
            gradients.append((first, second))
    env.gradients = gradients
    le, _ = cur.take("Enable")
    env.lens_enable = _parse_bool(doc.source, _need(doc.source, le, "LensFlare.Enable", 1)[0], "LensFlare.Enable")
    bc, _ = cur.take("BrightnessColor")
    env.lens_brightness = _parse_rgba(doc.source, _need(doc.source, bc, "LensFlare.BrightnessColor", 4), "BrightnessColor")
    mb, _ = cur.take("MaxBrightness")
    env.lens_max_brightness = _parse_float(doc.source, _need(doc.source, mb, "LensFlare.MaxBrightness", 1)[0], "MaxBrightness")
    me, _ = cur.take("MainFlareEnable")
    env.lens_main_enable = _parse_bool(doc.source, _need(doc.source, me, "LensFlare.MainFlareEnable", 1)[0], "LensFlare.MainFlareEnable")
    mt, _ = cur.take("MainFlareTextureFileName")
    env.lens_main_texture = _need(doc.source, mt, "LensFlare.MainFlareTextureFileName", 1)[0]
    ms, _ = cur.take("MainFlareSize")
    env.lens_main_size = _parse_float(doc.source, _need(doc.source, ms, "LensFlare.MainFlareSize", 1)[0], "MainFlareSize")
    env.unknown = cur.unknowns()
    env.unknown_groups = unknown_groups
    env.validate()
    return env


def write_environment(env: EnvironmentData, newline: bytes = CRLF) -> bytes:
    """Canonical environment writer.

    Group/key order and blank-line placement reproduce the verified
    reference template (``MapManagerEnvironment.cpp:339-463``).
    New-file indentation policy: one ``\\t`` per level — the reference
    indent helper (``PrintfTabs``) lives in the absent library sources,
    so only the structure is byte-guaranteed, not the indent bytes.
    Unknown records are appended at the end in original relative order.
    """
    env.validate()
    T = "\t"
    L: list[str] = []
    L.append(f"ScriptType         {ENV_MAGIC_WRITTEN}")
    L.append(f"ScriptVersion      {_c_float4(env.script_version)}")
    L.append("")
    L.append("Group DirectionalLight")
    L.append("{")
    d = env.dir_light_direction
    L.append(f"{T}Direction     {_c_float(d[0])} {_c_float(d[1])} {_c_float(d[2])}")
    L.append("")
    L.append(f"{T}Group Background")
    L.append(f"{T}{{")
    L.append(f"{T}{T}Enable        {env.background_enable}")
    L.append(f"{T}{T}Diffuse       {' '.join(env.background_diffuse.values())}")
    L.append(f"{T}{T}Ambient       {' '.join(env.background_ambient.values())}")
    L.append(f"{T}}}")
    L.append(f"{T}")
    L.append(f"{T}Group Character")
    L.append(f"{T}{{")
    L.append(f"{T}{T}Enable        {env.character_enable}")
    L.append(f"{T}{T}Diffuse       {' '.join(env.character_diffuse.values())}")
    L.append(f"{T}{T}Ambient       {' '.join(env.character_ambient.values())}")
    L.append(f"{T}}}")
    L.append("}")
    L.append("Group Material")
    L.append("{")
    L.append(f"{T}Diffuse       {' '.join(env.material_diffuse.values())}")
    L.append(f"{T}Ambient       {' '.join(env.material_ambient.values())}")
    L.append(f"{T}Emissive      {' '.join(env.material_emissive.values())}")
    L.append("}")
    L.append("")
    L.append("Group Fog")
    L.append("{")
    L.append(f"{T}Enable        {env.fog_enable}")
    L.append(f"{T}NearDistance  {_c_float(env.fog_near)}")
    L.append(f"{T}FarDistance   {_c_float(env.fog_far)}")
    L.append(f"{T}Color         {' '.join(env.fog_color.values())}")
    L.append("}")
    L.append("")
    L.append("Group Filter")
    L.append("{")
    L.append(f"{T}Enable        {env.filter_enable}")
    L.append(f"{T}Color         {' '.join(env.filter_color.values())}")
    L.append(f"{T}AlphaSrc      {env.filter_alpha_src}")
    L.append(f"{T}AlphaDest     {env.filter_alpha_dest}")
    L.append("}")
    L.append("")
    L.append("Group SkyBox")
    L.append("{")
    L.append(f"{T}bTextureRenderMode    {env.sky_texture_mode}")
    s = env.sky_scale
    L.append(f"{T}Scale                 {_c_float(s[0])} {_c_float(s[1])} {_c_float(s[2])}")
    L.append(f"{T}GradientLevelUpper    {env.sky_gradient_upper}")
    L.append(f"{T}GradientLevelLower    {env.sky_gradient_lower}")
    for fk, face in zip(_SKY_FACE_KEYS, env.sky_faces):
        pad = " " * max(1, 22 - len(fk))
        L.append(f"{T}{fk}{pad}\"{face}\"")
    L.append(f"{T}")
    cs = env.cloud_scale
    L.append(f"{T}CloudScale            {_c_float(cs[0])} {_c_float(cs[1])}")
    L.append(f"{T}CloudHeight           {_c_float(env.cloud_height)}")
    ts = env.cloud_tex_scale
    L.append(f"{T}CloudTextureScale     {_c_float(ts[0])} {_c_float(ts[1])}")
    cv = env.cloud_speed
    L.append(f"{T}CloudSpeed            {_c_float(cv[0])} {_c_float(cv[1])}")
    L.append(f"{T}CloudTextureFileName  \"{env.cloud_texture}\"")
    L.append(f"{T}List CloudColor")
    L.append(f"{T}{{")
    L.append(f"{T}{T}{' '.join(env.cloud_first.values())}")
    L.append(f"{T}{T}{' '.join(env.cloud_second.values())}")
    L.append(f"{T}}}")
    if env.gradients:
        L.append(f"{T}List Gradient")
        L.append(f"{T}{{")
        for i, (first, second) in enumerate(env.gradients):
            L.append(f"{T}{T}{' '.join(first.values())}")
            L.append(f"{T}{T}{' '.join(second.values())}")
            if i < len(env.gradients) - 1:
                L.append(f"{T}{T}")
        L.append(f"{T}}}")
    L.append("}")
    L.append("")
    L.append("Group LensFlare")
    L.append("{")
    L.append(f"{T}Enable                     {env.lens_enable}")
    L.append(f"{T}BrightnessColor            {' '.join(env.lens_brightness.values())}")
    L.append(f"{T}MaxBrightness              {_c_float(env.lens_max_brightness)}")
    L.append(f"{T}MainFlareEnable            {env.lens_main_enable}")
    L.append(f"{T}MainFlareTextureFileName   \"{env.lens_main_texture}\"")
    L.append(f"{T}MainFlareSize              {_c_float(env.lens_main_size)}")
    L.append("}")
    L.append("")
    for block in env.unknown_groups:
        for line in block:
            L.append(line.text)
    for line in env.unknown:
        L.append(line.text)
    nl = newline.decode("ascii")
    return (nl.join(L) + nl).encode("utf-8")
