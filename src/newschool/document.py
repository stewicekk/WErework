"""WorldDocument — the canonical editor-side map model.

Separation of concerns (see docs/ARCHITECTURE_TARGET.md):

* ``WorldDocument`` owns **game data only**: map setting/property, per
  chunk area objects + ambience, environment, regen. No editor state,
  no renderer handles, no UI pointers.
* Every mutation goes through :mod:`newschool.commands` so it is
  validated, dirty-tracked and undoable.
* Persistence is transactional (:mod:`newschool.store`): temp ->
  validate -> replace + backup. A failed save never destroys the
  previous content, and a failed load never mutates the document
  (stale-filename guard — cf. reference risk R4).

Chunk addressing follows the verified ``X*1000+Y`` / ``%06u`` scheme
(:mod:`newschool.chunks`).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from . import binary as binfmt
from . import mapfiles as mf
from .chunks import chunk_folder, iter_chunks
from .errors import ParseError, RecoveryError, TransactionError, ValidationError
from .paths import PathResolver
from .scripttext import ScriptDocument
from .store import atomic_write_bytes

AUTOSAVE_VERSION = 1

#: New-file policy for maps created by this core (no legacy file names
#: are invented for reading; this only names files WE create).
NEW_ENVIRONMENT_NAME = "environment.txt"


@dataclass
class ChunkData:
    x: int
    y: int
    area_name: str = ""
    num_water: int = 0
    objects: list[mf.ObjectInstance] = field(default_factory=list)
    ambience: list[mf.AmbienceInstance] = field(default_factory=list)
    # Raw payloads, kept byte-identical. Element counts are a property of
    # the terrain build (absent GameLib constants), so decoding always
    # takes an explicit count — see decode_height/decode_tile.
    height_raw: bytes | None = None
    tile_raw: bytes | None = None

    def validate(self) -> None:
        if not self.area_name:
            raise ValidationError(f"chunk ({self.x},{self.y}): AreaName is empty")
        if not 0 <= self.num_water <= 0xFF:
            raise ValidationError(f"chunk ({self.x},{self.y}): NumWater out of BYTE range")
        for obj in self.objects:
            obj.validate()
        for amb in self.ambience:
            amb.validate()
        if self.height_raw is not None and len(self.height_raw) % 2:
            raise ValidationError(f"chunk ({self.x},{self.y}): height.raw has odd length")

    def decode_height(self, count: int) -> list[int]:
        if self.height_raw is None:
            raise ValidationError(f"chunk ({self.x},{self.y}): no height data")
        return binfmt.load_height(self.height_raw, count)

    def decode_tile(self, count: int) -> bytes:
        if self.tile_raw is None:
            raise ValidationError(f"chunk ({self.x},{self.y}): no tile data")
        return binfmt.load_tile(self.tile_raw, count)

    def set_height(self, samples: list[int] | tuple[int, ...] | bytes | bytearray) -> None:
        self.height_raw = binfmt.dump_height(samples)

    def set_tile(self, samples: list[int] | tuple[int, ...] | bytes | bytearray) -> None:
        self.tile_raw = binfmt.dump_tile(samples)


class WorldDocument:
    """Canonical in-memory map. Create via :meth:`create_new` or :meth:`load`."""

    def __init__(self) -> None:
        self.map_name: str = ""
        self.map_dir: Path | None = None
        self.setting: mf.MapSetting | None = None
        self.property: mf.MapProperty | None = None
        self.environment: mf.EnvironmentData | None = None
        self.environment_name: str = ""
        self.environment_source: str | None = None
        self.chunks: dict[tuple[int, int], ChunkData] = {}
        self.regen: list[mf.RegenEntry] = []
        # Non-fatal diagnostics (missing optional files, fallbacks used).
        self.notes: list[str] = []
        self._dirty = False
        self._last_error: str | None = None

    # -- lifecycle ----------------------------------------------------
    @classmethod
    def create_new(cls, map_name: str, size_x: int, size_y: int,
                   base_x: int = 0, base_y: int = 0,
                   texture_set: str = "textureset\\default.txt",
                   environment: str = NEW_ENVIRONMENT_NAME) -> "WorldDocument":
        doc = cls()
        doc.map_name = map_name
        doc.setting = mf.MapSetting(
            cell_scale=200, height_scale=0.5, view_radius=128,
            map_size_x=size_x, map_size_y=size_y,
            base_x=base_x, base_y=base_y,
            texture_set=texture_set, environment=environment,
        )
        doc.setting.validate()
        doc.property = mf.MapProperty(map_type="Outdoor")
        doc.environment = mf.EnvironmentData()
        doc.environment_name = environment
        for x, y in iter_chunks(size_x, size_y):
            doc.chunks[(x, y)] = ChunkData(x=x, y=y, area_name=f"{map_name}_{x}_{y}")
        doc._dirty = True
        return doc

    @classmethod
    def load(cls, map_dir: str | Path) -> "WorldDocument":
        """Load a map tree. The document is only populated on full success."""
        root = Path(map_dir)
        setting_raw = _read(root / "Setting.txt", "Setting.txt")
        prop_raw = _read(root / "MapProperty.txt", "MapProperty.txt")
        setting = mf.parse_setting(ScriptDocument.from_bytes(setting_raw, str(root / "Setting.txt")))
        prop = mf.parse_map_property(ScriptDocument.from_bytes(prop_raw, str(root / "MapProperty.txt")))
        doc = cls()
        doc.map_name = root.name
        doc.map_dir = root
        doc.setting = setting
        doc.property = prop
        for x, y in iter_chunks(setting.map_size_x, setting.map_size_y):
            folder = root / chunk_folder(x, y)
            area_doc = ScriptDocument.from_bytes(
                _read(folder / "AreaData.txt", "AreaData.txt"), str(folder / "AreaData.txt"))
            objects = mf.parse_area_data(area_doc)
            amb_path = folder / "AreaAmbienceData.txt"
            ambience: list[mf.AmbienceInstance] = []
            if amb_path.is_file():
                ambience = mf.parse_area_ambience(
                    ScriptDocument.from_bytes(_read(amb_path, "AreaAmbienceData.txt"), str(amb_path)))
            aprop_path = folder / "AreaProperty.txt"
            area_name, num_water = f"{root.name}_{x}_{y}", 0
            if aprop_path.is_file():
                aprop = mf.parse_area_property(
                    ScriptDocument.from_bytes(_read(aprop_path, "AreaProperty.txt"), str(aprop_path)))
                area_name, num_water = aprop.area_name, aprop.num_water
            chunk = ChunkData(x=x, y=y, area_name=area_name, num_water=num_water,
                              objects=objects, ambience=ambience)
            height_path = folder / "height.raw"
            if height_path.is_file():
                chunk.height_raw = _read(height_path, "height.raw")
            tile_path = folder / "tile.raw"
            if tile_path.is_file():
                chunk.tile_raw = _read(tile_path, "tile.raw")
            chunk.validate()
            doc.chunks[(x, y)] = chunk
        regen_path = root / "regen.txt"
        if regen_path.is_file():
            doc.regen = mf.parse_regen(
                ScriptDocument.from_bytes(_read(regen_path, "regen.txt"), str(regen_path)))
        for entry in doc.regen:
            entry.validate()
        env_name = setting.environment
        doc.environment_name = env_name
        env_path = _locate_environment(root, env_name)
        if env_path is None:
            doc.notes.append(
                f"environment '{env_name}' not found beside the map; "
                "environment left empty (no silent default applied)"
            )
        else:
            doc.environment = mf.parse_environment(
                ScriptDocument.from_bytes(_read(env_path, "environment"), str(env_path))
            )
            doc.environment_source = str(env_path)
        doc._dirty = False
        return doc

    # -- validation / dirty -------------------------------------------
    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.setting is None:
            errors.append("document has no Setting")
        else:
            try:
                self.setting.validate()
            except ValidationError as exc:
                errors.append(str(exc))
        if self.property is None:
            errors.append("document has no MapProperty")
        else:
            try:
                self.property.validate()
            except ValidationError as exc:
                errors.append(str(exc))
        if self.setting is not None:
            want = {
                (x, y)
                for x, y in iter_chunks(self.setting.map_size_x, self.setting.map_size_y)
            }
            if set(self.chunks) != want:
                errors.append(
                    f"chunk set {sorted(set(self.chunks))} != MapSize grid {sorted(want)}"
                )
        for key in sorted(self.chunks):
            try:
                self.chunks[key].validate()
            except ValidationError as exc:
                errors.append(str(exc))
        if self.environment is not None:
            try:
                self.environment.validate()
            except ValidationError as exc:
                errors.append(str(exc))
        for entry in self.regen:
            try:
                entry.validate()
            except ValidationError as exc:
                errors.append(str(exc))
        return errors

    def assert_valid(self) -> None:
        errors = self.validate()
        if errors:
            raise ValidationError("document invalid: " + "; ".join(errors))

    @property
    def dirty(self) -> bool:
        return self._dirty

    def mark_dirty(self) -> None:
        self._dirty = True

    def mark_clean(self) -> None:
        self._dirty = False

    @property
    def last_error(self) -> str | None:
        return self._last_error

    # -- persistence ----------------------------------------------------
    def save(self, map_dir: str | Path | None = None, backup: bool = True) -> list[str]:
        """Save the whole map tree.

        Atomicity is per file (temp -> validate -> replace + backup);
        files are written in a fixed order and the first failure raises,
        naming the exact file. Files already written stay valid, but a
        mid-save failure can leave a mix of old and new files — map-wide
        staging/rollback is tracked future work, so treat the backup
        files as the recovery path. Returns created backups.
        """
        self.assert_valid()
        assert self.setting is not None and self.property is not None
        root = Path(map_dir) if map_dir is not None else self.map_dir
        if root is None:
            raise TransactionError("save: no target directory (document was never loaded nor saved)")
        backups: list[str] = []
        put = lambda p, data, v: _put(backups, p, data, v, backup)
        put(root / "Setting.txt", mf.write_setting(self.setting),
            lambda b: mf.parse_setting(ScriptDocument.from_bytes(b, "Setting.txt")))
        put(root / "MapProperty.txt", mf.write_map_property(self.property),
            lambda b: mf.parse_map_property(ScriptDocument.from_bytes(b, "MapProperty.txt")))
        for (x, y), chunk in sorted(self.chunks.items()):
            folder = root / chunk_folder(x, y)
            put(folder / "AreaData.txt", mf.write_area_data(chunk.objects),
                lambda b: mf.parse_area_data(ScriptDocument.from_bytes(b, "AreaData.txt")))
            put(folder / "AreaAmbienceData.txt", mf.write_area_ambience(chunk.ambience),
                lambda b: mf.parse_area_ambience(ScriptDocument.from_bytes(b, "AreaAmbienceData.txt")))
            put(folder / "AreaProperty.txt",
                mf.write_area_property(mf.AreaProperty(area_name=chunk.area_name,
                                                       num_water=chunk.num_water)),
                lambda b: mf.parse_area_property(ScriptDocument.from_bytes(b, "AreaProperty.txt")))
            if chunk.height_raw is not None:
                put(folder / "height.raw", bytes(chunk.height_raw), _validate_height_raw)
            if chunk.tile_raw is not None:
                put(folder / "tile.raw", bytes(chunk.tile_raw), _validate_tile_raw)
        # Always rewritten (even when empty) so an emptied regen list
        # can never leave stale files behind.
        put(root / "regen.txt", mf.write_regen(self.regen),
            lambda b: mf.parse_regen(ScriptDocument.from_bytes(b, "regen.txt")))
        put(root / "MonsterArrange.txt",
            mf.write_monster_arrange([e.vnum for e in self.regen]),
            lambda b: mf.parse_monster_arrange(ScriptDocument.from_bytes(b, "MonsterArrange.txt")))
        if self.environment is not None:
            env_target = (
                Path(self.environment_source)
                if self.environment_source
                else root / (self.environment_name or NEW_ENVIRONMENT_NAME)
            )
            put(env_target, mf.write_environment(self.environment),
                lambda b: mf.parse_environment(ScriptDocument.from_bytes(b, "environment")))
            self.environment_source = str(env_target)
        if self.map_dir is None:
            self.map_dir = root
        self.map_name = root.name
        self._dirty = False
        self._last_error = None
        return backups

    # -- autosave / recovery --------------------------------------------
    def autosave(self, recovery_dir: str | Path) -> Path:
        """Write a timestamped full-tree snapshot for crash recovery.

        The snapshot is a complete, loadable map tree (same layout as
        :meth:`save`) plus a ``.snapshot`` marker, so recovery is a
        plain :meth:`load` — counts-only markers would never restore.
        """
        self.assert_valid()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target = Path(recovery_dir) / f"{self.map_name or 'unnamed'}-{stamp}"
        self.save(target, backup=False)
        marker = target / ".snapshot"
        atomic_write_bytes(
            marker,
            f"NewSchoolSnapshot {AUTOSAVE_VERSION}\n{stamp}\n".encode("utf-8"),
            validate=_validate_snapshot_marker,
            backup=False,
        )
        return target

    @staticmethod
    def list_recovery(recovery_dir: str | Path) -> list[Path]:
        root = Path(recovery_dir)
        if not root.is_dir():
            return []
        return sorted(
            p for p in root.iterdir()
            if p.is_dir() and (p / ".snapshot").is_file() and (p / "Setting.txt").is_file()
        )

    @classmethod
    def recover(cls, snapshot_dir: str | Path) -> "WorldDocument":
        """Load a snapshot written by :meth:`autosave`."""
        root = Path(snapshot_dir)
        marker = root / ".snapshot"
        if not marker.is_file():
            raise RecoveryError(f"{root}: not a snapshot (missing .snapshot marker)")
        try:
            text = marker.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise RecoveryError(f"{root}: unreadable snapshot marker: {exc}") from exc
        if not text.startswith(f"NewSchoolSnapshot {AUTOSAVE_VERSION}\n"):
            raise RecoveryError(f"{root}: snapshot has a bad magic/version: {text[:60]!r}")
        doc = cls.load(root)
        doc.notes.append(f"recovered from snapshot {root.name}")
        return doc


def _validate_snapshot_marker(payload: bytes) -> None:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TransactionError(f"snapshot marker is not UTF-8: {exc}") from exc
    if not text.startswith(f"NewSchoolSnapshot {AUTOSAVE_VERSION}\n"):
        raise TransactionError("snapshot marker has a bad magic/version")


def _locate_environment(map_dir: Path, env_name: str) -> Path | None:
    """Find the environment file beside the map (exact name, then +.txt)."""
    if not env_name:
        return None
    candidates = [map_dir / env_name]
    if not env_name.lower().endswith(".txt"):
        candidates.append(map_dir / (env_name + ".txt"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _validate_height_raw(payload: bytes) -> None:
    if len(payload) % 2:
        raise TransactionError(f"height.raw payload has odd length {len(payload)}")


def _validate_tile_raw(_payload: bytes) -> None:
    return None


def _read(path: Path, what: str) -> bytes:
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError as exc:
        raise ParseError(str(path), f"cannot read {what}: {exc}") from exc


def _put(backups: list[str], path: Path, data: bytes, validate, backup: bool) -> None:
    made = atomic_write_bytes(path, data, validate=validate, backup=backup)
    if made is not None:
        backups.append(str(made))


def locate_map(resolver: PathResolver, map_name: str) -> Path:
    """Find a map directory or raise a diagnostic error (never stale state)."""
    found = resolver.map_directory(map_name)
    if found is None:
        raise TransactionError(
            f"map '{map_name}' not found (Setting.txt missing in search order: "
            + ", ".join(resolver.search_order())
            + ")"
        )
    return found
