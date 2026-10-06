import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from newschool.errors import MissingAssetError, ParseError, PathSecurityError
from newschool.paths import PathResolver, normalize_logical, parse_index


class PathsTest(unittest.TestCase):
    def test_index_two_line_pairs(self):
        pairs = parse_index("pack_folder\npack_name\nsecond/\nsecond_pack\n")
        self.assertEqual(pairs, [("pack_folder", "pack_name"), ("second/", "second_pack")])
        with self.assertRaises(ParseError):
            parse_index("only_one_line\n")

    def test_normalize(self):
        self.assertEqual(normalize_logical("a\\b//c"), "a/b/c")
        with self.assertRaises(PathSecurityError):
            normalize_logical("../escape")
        with self.assertRaises(PathSecurityError):
            normalize_logical("a/../../escape")
        with self.assertRaises(PathSecurityError):
            normalize_logical("D:/absolute")
        with self.assertRaises(PathSecurityError):
            normalize_logical("c:\\absolute")
        with self.assertRaises(PathSecurityError):
            normalize_logical("/posix-absolute")
        with self.assertRaises(PathSecurityError):
            normalize_logical("\\\\unc\\share")

    def test_resolve_rejects_escape(self):
        r = PathResolver(roots=[], ymir_fallback=None)
        with self.assertRaises(PathSecurityError):
            r.resolve("C:/windows")
        self.assertIsNone(r.resolve("simply-missing.txt"))

    def test_loose_first_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            loose = Path(tmp) / "loose"
            packed = Path(tmp) / "packed"
            (loose / "env").mkdir(parents=True)
            (packed / "env").mkdir(parents=True)
            (loose / "env" / "day.txt").write_bytes(b"loose")
            (packed / "env" / "day.txt").write_bytes(b"packed")
            r = PathResolver(roots=[loose], pack_roots=[packed], loose_first=True,
                             ymir_fallback=None)
            self.assertEqual(r.require("env/day.txt").read_bytes(), b"loose")
            r2 = PathResolver(roots=[loose], pack_roots=[packed], loose_first=False,
                              ymir_fallback=None)
            self.assertEqual(r2.require("env/day.txt").read_bytes(), b"packed")

    def test_missing_asset_diagnostic(self):
        r = PathResolver(roots=[], pack_roots=[], loose_first=True, ymir_fallback=None)
        with self.assertRaises(MissingAssetError) as ctx:
            r.require("monster/mansion.gr2")
        self.assertIn("monster/mansion.gr2", str(ctx.exception))
        report = r.missing_report(["a.txt", "b.txt"])
        self.assertEqual(len(report), 2)

    def test_map_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mymap").mkdir()
            (root / "mymap" / "Setting.txt").write_bytes(b"x")
            r = PathResolver(roots=[root], ymir_fallback=None)
            self.assertEqual(r.map_directory("mymap"), root / "mymap")
            self.assertIsNone(r.map_directory("ghost"))
            with self.assertRaises(PathSecurityError):
                r.map_directory("../escape")


if __name__ == "__main__":
    unittest.main()
