import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from newschool.errors import TransactionError
from newschool.store import atomic_write_bytes, atomic_write_text, read_bytes


class StoreTest(unittest.TestCase):
    def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "Setting.txt"
            self.assertIsNone(atomic_write_bytes(target, b"v1"))
            self.assertEqual(read_bytes(target), b"v1")

    def test_second_write_preserves_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "Setting.txt"
            atomic_write_bytes(target, b"v1")
            backup = atomic_write_bytes(target, b"v2")
            self.assertIsNotNone(backup)
            self.assertEqual(Path(str(backup)).read_bytes(), b"v1")
            self.assertEqual(read_bytes(target), b"v2")

    def test_failed_validation_keeps_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "AreaData.txt"
            atomic_write_bytes(target, b"good")
            with self.assertRaises(TransactionError):
                atomic_write_bytes(target, b"bad", validate=self._rejector)
            self.assertEqual(read_bytes(target), b"good")
            leftovers = list(Path(tmp).glob("*.tmp"))
            self.assertEqual(leftovers, [])

    def test_failed_validation_on_new_file_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "AreaData.txt"
            with self.assertRaises(TransactionError):
                atomic_write_bytes(target, b"bad", validate=self._rejector)
            self.assertFalse(target.exists())

    def test_read_missing_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(TransactionError):
                read_bytes(Path(tmp) / "ghost.txt")

    def test_text_write_no_double_crlf(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "note.txt"
            atomic_write_text(target, "a\r\nb\nc\n")
            self.assertEqual(read_bytes(target), b"a\r\nb\r\nc\r\n")

    @staticmethod
    def _rejector(_payload: bytes):
        raise ValueError("rejected")


if __name__ == "__main__":
    unittest.main()
