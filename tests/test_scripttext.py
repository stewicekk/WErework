import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from newschool.errors import ParseError
from newschool.scripttext import ScriptDocument, detect_newline


class ScriptTextTest(unittest.TestCase):
    def test_newline_detection(self):
        self.assertEqual(detect_newline(b"a\r\nb\r\n"), b"\r\n")
        self.assertEqual(detect_newline(b"a\nb\n"), b"\n")
        self.assertEqual(detect_newline(b""), b"\r\n")  # legacy text-mode default
        self.assertEqual(detect_newline(b"a\r\nb\nc\r\nd\r\n"), b"\r\n")

    def test_kv_access(self):
        doc = ScriptDocument.from_bytes(b"ScriptType\tMapSetting\r\n\r\nCellScale\t200\r\n")
        self.assertEqual(doc.get_first("ScriptType"), ["MapSetting"])
        self.assertEqual(doc.get_first("CellScale"), ["200"])
        self.assertIsNone(doc.get_first("Missing"))

    def test_comments_and_blanks_are_not_keys(self):
        doc = ScriptDocument.from_bytes(b"//type\tcx\r\n\r\nReal\t1\r\n")
        self.assertIsNone(doc.get_first("//type"))
        self.assertEqual(doc.get_first("Real"), ["1"])

    def test_unknown_bytes_preserved(self):
        raw = b"ScriptType\tMapSetting\r\nCustom-Weird \xff\xfe binary \x01\x02\r\n"
        with self.assertRaises(ParseError):
            ScriptDocument.from_bytes(raw)  # invalid UTF-8 must fail loudly
        raw2 = "ScriptType\tMapSetting\r\nX-Customünïcodé line ☃\r\n".encode("utf-8")
        doc = ScriptDocument.from_bytes(raw2)
        self.assertEqual(doc.to_bytes(), raw2)

    def test_set_first_updates_in_place(self):
        doc = ScriptDocument.from_bytes(b"A\t1\r\nB\t2\r\n")
        self.assertTrue(doc.set_first("A", ["9"]))
        self.assertEqual(doc.get_first("A"), ["9"])
        self.assertEqual(doc.to_bytes(), b"A 9\r\nB\t2\r\n")

    def test_quoted_values(self):
        doc = ScriptDocument.from_bytes(b'MapType "Outdoor"\r\nAreaName "my map"\r\n')
        self.assertEqual(doc.get_first("MapType"), ["Outdoor"])
        self.assertEqual(doc.get_first("AreaName"), ["my map"])

    def test_roundtrip_stable(self):
        raw = b"Start Object000\r\n    1.000000 2.000000 3.000000\r\nEnd Object\r\n"
        doc = ScriptDocument.from_bytes(raw)
        self.assertEqual(doc.to_bytes(), raw)

    def test_missing_trailing_newline_preserved(self):
        raw = b"A\t1\r\nB\t2"
        doc = ScriptDocument.from_bytes(raw)
        self.assertEqual(doc.to_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
