import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from newschool.chunks import chunk_folder, chunk_id, iter_chunks, parse_chunk_folder
from newschool.errors import ValidationError


class ChunkTest(unittest.TestCase):
    def test_id_scheme(self):
        # Verified: folder id = X*1000+Y (MapAccessorOutdoor.cpp:780-781)
        self.assertEqual(chunk_id(0, 0), 0)
        self.assertEqual(chunk_id(1, 2), 1002)
        self.assertEqual(chunk_id(999, 999), 999999)

    def test_folder_format(self):
        self.assertEqual(chunk_folder(0, 0), "000000")
        self.assertEqual(chunk_folder(1, 2), "001002")
        self.assertEqual(chunk_folder(12, 34), "012034")

    def test_roundtrip(self):
        for x, y in [(0, 0), (1, 2), (999, 999), (0, 999), (999, 0)]:
            self.assertEqual(parse_chunk_folder(chunk_folder(x, y)), (x, y))

    def test_rejects_out_of_range(self):
        for bad in (-1, 1000, 10**6):
            with self.assertRaises(ValidationError):
                chunk_id(bad, 0)
            with self.assertRaises(ValidationError):
                chunk_id(0, bad)

    def test_rejects_malformed_folder(self):
        for bad in ("", "123", "1234567", "abcdef", "00102a", " 01002"):
            with self.assertRaises(ValidationError):
                parse_chunk_folder(bad)

    def test_iter_grid(self):
        self.assertEqual(list(iter_chunks(2, 2)), [(0, 0), (1, 0), (0, 1), (1, 1)])
        with self.assertRaises(ValidationError):
            list(iter_chunks(0, 1))


if __name__ == "__main__":
    unittest.main()
