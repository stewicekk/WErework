import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from newschool import binary as b
from newschool.errors import ParseError, ValidationError


class BinaryTest(unittest.TestCase):
    def test_height_roundtrip(self):
        samples = [0, 1, 0x7FFF, 0xFFFF, 12345]
        raw = b.dump_height(samples)
        self.assertEqual(len(raw), 10)
        self.assertEqual(b.load_height(raw, 5), samples)

    def test_height_new_fill(self):
        self.assertEqual(b.new_height(3), [0x7FFF] * 3)  # legacy fill
        self.assertEqual(b.load_height(b.dump_height(b.new_height(4)), 4), [0x7FFF] * 4)

    def test_height_rejects_bad_sample(self):
        with self.assertRaises(ValidationError):
            b.dump_height([70000])
        with self.assertRaises(ValidationError):
            b.dump_height([-1])

    def test_height_rejects_length_mismatch(self):
        with self.assertRaises(ParseError):
            b.load_height(b"\x00" * 6, 4)

    def test_tile_roundtrip(self):
        raw = b.dump_tile([0, 1, 255, 7])
        self.assertEqual(raw, bytes([0, 1, 255, 7]))
        self.assertEqual(b.load_tile(raw, 4), bytes([0, 1, 255, 7]))

    def test_tile_rejects_bad_index(self):
        with self.assertRaises(ValidationError):
            b.dump_tile([256])

    def test_attr_roundtrip(self):
        raw = b.dump_attr(4, 2, bytes(range(8)))
        self.assertTrue(raw.startswith(b"\x4a\x0a"))  # mapver 2634 LE
        w, h, body = b.load_attr(raw)
        self.assertEqual((w, h, body), (4, 2, bytes(range(8))))

    def test_attr_rejects_bad_magic(self):
        with self.assertRaises(ParseError):
            b.load_attr(b"\x00\x00\x04\x00\x02\x00" + b"\x00" * 8)

    def test_attr_rejects_truncation(self):
        with self.assertRaises(ParseError):
            b.load_attr(b"\x4a\x0a\x04\x00\x02\x00" + b"\x00" * 7)

    def test_water_roundtrip(self):
        raw = b.dump_water(2, 2, bytes([0, 1, 0xFF, 2]), [100, -5])
        self.assertTrue(raw.startswith(b"\x32\x15"))  # mapver 5426 LE
        w, h, wm, heights = b.load_water(raw)
        self.assertEqual((w, h, wm, heights), (2, 2, bytes([0, 1, 0xFF, 2]), [100, -5]))

    def test_water_empty(self):
        raw = b.dump_water(1, 1, bytes([0xFF]), [])
        w, h, wm, heights = b.load_water(raw)
        self.assertEqual(heights, [])

    def test_water_rejects_bad_magic(self):
        with self.assertRaises(ParseError):
            b.load_water(b"\x00\x00\x01\x00\x01\x00\x00\x00")

    def test_collision_header(self):
        self.assertEqual(b.dump_collision_header(3, 4), b"M2CD\x03\x00\x04\x00")


if __name__ == "__main__":
    unittest.main()
