import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from newschool import mapfiles as mf
from newschool.document import WorldDocument, locate_map
from newschool.errors import ParseError, RecoveryError, TransactionError, ValidationError
from newschool.paths import PathResolver


class DocumentTest(unittest.TestCase):
    def _sample(self):
        doc = WorldDocument.create_new("testmap", 2, 2)
        chunk = doc.chunks[(0, 0)]
        chunk.objects.append(mf.ObjectInstance(x=10, y=20, z=0, crc=4242, yaw=0,
                                               pitch=0, roll=0, height_bias=0,
                                               portals=[1, 2]))
        chunk.set_height([0x7FFF] * 4)
        chunk.set_tile(bytes([0, 1, 2, 3]))
        doc.regen.append(mf.RegenEntry(kind="m", cx=1, cy=2, sx=3, sy=4, count=5, vnum=101))
        return doc

    def test_create_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = self._sample()
            self.assertTrue(doc.dirty)
            backups = doc.save(Path(tmp) / "testmap")
            self.assertEqual(backups, [])  # fresh save: nothing to back up
            self.assertFalse(doc.dirty)
            self.assertEqual(doc.validate(), [])
            reloaded = WorldDocument.load(Path(tmp) / "testmap")
            self.assertEqual(reloaded.validate(), [])
            self.assertEqual(reloaded.setting.map_size_x, 2)
            obj = reloaded.chunks[(0, 0)].objects[0]
            self.assertEqual((obj.x, obj.y, obj.crc, obj.portals), (10.0, 20.0, 4242, [1, 2]))
            self.assertEqual(reloaded.chunks[(0, 0)].decode_height(4), [0x7FFF] * 4)
            self.assertEqual(reloaded.chunks[(0, 0)].decode_tile(4), bytes([0, 1, 2, 3]))
            self.assertEqual(len(reloaded.regen), 1)

    def test_resave_creates_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = self._sample()
            root = Path(tmp) / "testmap"
            doc.save(root)
            backups = doc.save(root)
            self.assertTrue(any(b.endswith("Setting.txt.bak") for b in backups))

    def test_save_invalid_raises_and_keeps_clean_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = self._sample()
            assert doc.setting is not None
            doc.setting.map_size_x = 0  # corrupt in memory
            with self.assertRaises(ValidationError):
                doc.save(Path(tmp) / "testmap")
            self.assertTrue(doc.dirty)  # failed save never clears dirty

    def test_load_broken_map_raises_without_partial_doc(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "broken"
            root.mkdir()
            (root / "Setting.txt").write_bytes(b"ScriptType\tBroken\r\n")
            (root / "MapProperty.txt").write_bytes(
                b'ScriptType MapProperty\r\n\r\nMapType "Outdoor"\r\n\r\n')
            with self.assertRaises(ParseError):
                WorldDocument.load(root)

    def test_failed_save_never_points_at_wrong_folder(self):
        # Regression guard for reference risk R4: failed load/save must not
        # silently retarget the document.
        with tempfile.TemporaryDirectory() as tmp:
            doc = self._sample()
            root = Path(tmp) / "testmap"
            doc.save(root)
            first_dir = doc.map_dir
            blocker = Path(tmp) / "blocker"
            blocker.write_bytes(b"i am a file, not a directory")
            was_dirty = doc.dirty
            with self.assertRaises(TransactionError):
                doc.save(blocker / "x")
            self.assertEqual(doc.map_dir, first_dir)
            self.assertEqual(doc.dirty, was_dirty)  # failed save never touches dirty
            # original content still intact
            reloaded = WorldDocument.load(root)
            self.assertEqual(len(reloaded.chunks[(0, 0)].objects), 1)

    def test_autosave_and_recovery_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = self._sample()
            snap = doc.autosave(Path(tmp) / "recovery")
            self.assertTrue(snap.is_dir())
            self.assertTrue((snap / "Setting.txt").is_file())
            found = WorldDocument.list_recovery(Path(tmp) / "recovery")
            self.assertEqual(found, [snap])
            self.assertEqual(WorldDocument.list_recovery(Path(tmp) / "empty"), [])

    def test_recover_restores_full_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = self._sample()
            snap = doc.autosave(Path(tmp) / "recovery")
            recovered = WorldDocument.recover(snap)
            self.assertEqual(recovered.validate(), [])
            self.assertEqual(len(recovered.chunks[(0, 0)].objects), 1)
            self.assertEqual(len(recovered.regen), 1)
            self.assertTrue(any("recovered from snapshot" in n for n in recovered.notes))

    def test_recover_rejects_non_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RecoveryError):
                WorldDocument.recover(Path(tmp))

    def test_empty_regen_leaves_no_stale_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = WorldDocument.create_new("plainmap", 1, 1)
            root = Path(tmp) / "plainmap"
            doc.save(root)
            self.assertTrue((root / "regen.txt").is_file())
            self.assertTrue((root / "MonsterArrange.txt").is_file())
            reloaded = WorldDocument.load(root)
            self.assertEqual(reloaded.regen, [])

    def test_environment_saved_and_reloaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = WorldDocument.create_new("envmap", 1, 1)
            assert doc.environment is not None
            doc.environment.fog_enable = 1
            root = Path(tmp) / "envmap"
            doc.save(root)
            reloaded = WorldDocument.load(root)
            assert reloaded.environment is not None
            self.assertEqual(reloaded.environment.fog_enable, 1)

    def test_missing_environment_is_diagnostic_not_crash(self):
        import shutil

        with tempfile.TemporaryDirectory() as tmp:
            doc = WorldDocument.create_new("noenv", 1, 1)
            root = Path(tmp) / "noenv"
            doc.save(root)
            (root / "environment.txt").unlink()
            reloaded = WorldDocument.load(root)
            self.assertIsNone(reloaded.environment)
            self.assertTrue(any("environment" in n for n in reloaded.notes))

    def test_locate_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = self._sample()
            doc.save(Path(tmp) / "testmap")
            resolver = PathResolver(roots=[Path(tmp)], ymir_fallback=None)
            self.assertEqual(locate_map(resolver, "testmap"), Path(tmp) / "testmap")
            with self.assertRaises(TransactionError):
                locate_map(resolver, "ghost")


if __name__ == "__main__":
    unittest.main()
