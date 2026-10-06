import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from newschool import mapfiles as mf
from newschool.errors import ParseError, ValidationError
from newschool.scripttext import ScriptDocument

CRLF = b"\r\n"


def sample_setting():
    return mf.MapSetting(
        cell_scale=200, height_scale=0.5, view_radius=128,
        map_size_x=2, map_size_y=3, base_x=10, base_y=20,
        texture_set="textureset\\default.txt", environment="midnight",
    )


class SettingTest(unittest.TestCase):
    def test_golden_bytes_match_legacy_template(self):
        got = mf.write_setting(sample_setting())
        want = (
            b"ScriptType\tMapSetting\r\n\r\n"
            b"CellScale\t200\r\n"
            b"HeightScale\t0.500000\r\n\r\n"
            b"ViewRadius\t128\r\n\r\n"
            b"MapSize\t2\t3\r\n"
            b"BasePosition\t10\t20\r\n"
            b"TextureSet\ttextureset\\default.txt\r\n"
            b"Environment\tmidnight\r\n\r\n"
        )
        self.assertEqual(got, want)

    def test_roundtrip_semantic(self):
        back = mf.parse_setting(ScriptDocument.from_bytes(mf.write_setting(sample_setting())))
        self.assertEqual(back, sample_setting())

    def test_unknown_lines_survive(self):
        raw = mf.write_setting(sample_setting()) + b"FutureKey\t42\r\n"
        back = mf.parse_setting(ScriptDocument.from_bytes(raw))
        self.assertEqual(len(back.unknown), 1)
        self.assertIn(b"FutureKey\t42", mf.write_setting(back))

    def test_rejects_bad_magic(self):
        with self.assertRaises(ParseError):
            mf.parse_setting(ScriptDocument.from_bytes(b"ScriptType\tNope\r\n"))

    def test_rejects_non_finite(self):
        bad = sample_setting()
        bad.height_scale = float("inf")
        with self.assertRaises(ValidationError):
            mf.write_setting(bad)

    def test_rejects_absurd_size(self):
        bad = sample_setting()
        bad.map_size_x = 100000
        with self.assertRaises(ValidationError):
            mf.write_setting(bad)


class MapPropertyTest(unittest.TestCase):
    def test_golden_bytes(self):
        got = mf.write_map_property(mf.MapProperty(map_type="Outdoor"))
        self.assertEqual(got, b'ScriptType MapProperty\r\n\r\nMapType "Outdoor"\r\n\r\n')

    def test_roundtrip(self):
        for t in ("Indoor", "Outdoor", "Invalid"):
            back = mf.parse_map_property(
                ScriptDocument.from_bytes(mf.write_map_property(mf.MapProperty(map_type=t))))
            self.assertEqual(back.map_type, t)

    def test_rejects_unknown_type(self):
        # Structurally valid file, domain-invalid value -> ValidationError (actionable).
        with self.assertRaises(ValidationError):
            mf.parse_map_property(ScriptDocument.from_bytes(b'ScriptType MapProperty\r\n\r\nMapType "Moon"\r\n\r\n'))


class AreaPropertyTest(unittest.TestCase):
    def test_golden_bytes(self):
        got = mf.write_area_property(mf.AreaProperty(area_name="metin2_map", num_water=2))
        self.assertEqual(
            got,
            b'ScriptType AreaProperty\r\n\r\nAreaName "metin2_map"\r\n\r\nNumWater 2\r\n\r\n',
        )

    def test_roundtrip(self):
        back = mf.parse_area_property(
            ScriptDocument.from_bytes(mf.write_area_property(mf.AreaProperty("a", 0))))
        self.assertEqual((back.area_name, back.num_water), ("a", 0))


class AreaDataTest(unittest.TestCase):
    def test_golden_bytes_with_portal_dedup(self):
        obj = mf.ObjectInstance(x=100.0, y=200.0, z=0.0, crc=12345,
                                yaw=45.0, pitch=0.0, roll=0.0, height_bias=0.0,
                                portals=[5, 7, 7, 9])
        got = mf.write_area_data([obj])
        want = (
            b"AreaDataFile\r\n\r\n"
            b"Start Object000\r\n"
            b"    100.000000 200.000000 0.000000\r\n"
            b"    12345\r\n"
            b"    45.000000#0.000000#0.000000\r\n"
            b"    0.000000\r\n"
            b"    5 7 9\r\n"
            b"End Object\r\n\r\n"
            b"ObjectCount 1\r\n"
        )
        self.assertEqual(got, want)

    def test_object_without_portals_has_no_portal_line(self):
        obj = mf.ObjectInstance(x=0, y=0, z=0, crc=1, yaw=0, pitch=0, roll=0, height_bias=0)
        out = mf.write_area_data([obj]).decode()
        self.assertNotIn("   \n", out)
        back = mf.parse_area_data(ScriptDocument.from_bytes(mf.write_area_data([obj])))
        self.assertEqual(back[0].portals, [])

    def test_roundtrip(self):
        objs = [
            mf.ObjectInstance(x=1.5, y=-2.5, z=10.0, crc=999, yaw=90, pitch=1, roll=2,
                              height_bias=0.25, portals=[3, 1]),
            mf.ObjectInstance(x=0, y=0, z=0, crc=2, yaw=0, pitch=0, roll=0, height_bias=0),
        ]
        back = mf.parse_area_data(ScriptDocument.from_bytes(mf.write_area_data(objs)))
        self.assertEqual(len(back), 2)
        self.assertEqual(back[0].portals, [3, 1])
        self.assertAlmostEqual(back[0].x, 1.5)
        # byte-stable second write (deterministic writer)
        self.assertEqual(mf.write_area_data(back), mf.write_area_data(objs))

    def test_rejects_zero_portal_id(self):
        # The legacy writer stops at the first 0 byte, so a 0 portal id
        # proves the file did not come from it — fail loudly.
        raw = (b"AreaDataFile\r\n\r\nStart Object000\r\n    0.000000 0.000000 0.000000\r\n"
               b"    1\r\n    0.000000#0.000000#0.000000\r\n    0.000000\r\n"
               b"    5 0\r\nEnd Object\r\n\r\nObjectCount 1\r\n")
        with self.assertRaises(ParseError):
            mf.parse_area_data(ScriptDocument.from_bytes(raw))

    def test_rejects_count_mismatch(self):
        raw = (b"AreaDataFile\r\n\r\nStart Object000\r\n    0.000000 0.000000 0.000000\r\n"
               b"    1\r\n    0.000000#0.000000#0.000000\r\n    0.000000\r\nEnd Object\r\n\r\n"
               b"ObjectCount 2\r\n")
        with self.assertRaises(ParseError):
            mf.parse_area_data(ScriptDocument.from_bytes(raw))

    def test_empty_map(self):
        out = mf.write_area_data([])
        self.assertEqual(out, b"AreaDataFile\r\n\r\n\r\nObjectCount 0\r\n")
        self.assertEqual(mf.parse_area_data(ScriptDocument.from_bytes(out)), [])


class AmbienceTest(unittest.TestCase):
    def test_golden_bytes(self):
        amb = mf.AmbienceInstance(x=1, y=2, z=3, crc=77, range=500, max_volume_pct=80.0)
        got = mf.write_area_ambience([amb])
        want = (
            b"AreaAmbienceDataFile\r\n\r\n"
            b"Start Object000\r\n"
            b"    1.000000 2.000000 3.000000\r\n"
            b"    77\r\n"
            b"    500\r\n"
            b"    80.000000\r\n"
            b"End Object\r\n\r\n"
            b"ObjectCount 1\r\n"
        )
        self.assertEqual(got, want)

    def test_roundtrip(self):
        amb = mf.AmbienceInstance(x=1, y=2, z=3, crc=77, range=500, max_volume_pct=80.0)
        back = mf.parse_area_ambience(ScriptDocument.from_bytes(mf.write_area_ambience([amb])))
        self.assertEqual(back, [amb])


class RegenTest(unittest.TestCase):
    def test_golden_bytes(self):
        entries = [mf.RegenEntry(kind="m", cx=100, cy=200, sx=10, sy=10, direction=3,
                                 count=5, vnum=101),
                   mf.RegenEntry(kind="g", cx=1, cy=2, sx=3, sy=4, direction=0,
                                 count=1, vnum=900)]
        got = mf.write_regen(entries)
        self.assertTrue(got.startswith(b"//type\tcx\tcy\tsx\tsy\tz\tdir\ttime\tpercent\tcount\tvnum\r\n"))
        self.assertIn(b"m\t100\t200\t10\t10\t0\t3\t1m\t100\t5\t101\r\n", got)
        back = mf.parse_regen(ScriptDocument.from_bytes(got))
        self.assertEqual(back, entries)

    def test_monster_arrange_dedup_sorted(self):
        out = mf.write_monster_arrange([900, 101, 900, 50])
        self.assertEqual(out, b"50\r\n101\r\n900\r\n")
        back = mf.parse_monster_arrange(ScriptDocument.from_bytes(out))
        self.assertEqual(back, [50, 101, 900])

    def test_rejects_bad_kind(self):
        with self.assertRaises(ValidationError):
            mf.write_regen([mf.RegenEntry(kind="x", cx=0, cy=0, sx=0, sy=0)])

    def test_rejects_time_without_m_suffix(self):
        raw = (b"//type\tcx\tcy\tsx\tsy\tz\tdir\ttime\tpercent\tcount\tvnum\r\n"
               b"m\t1\t2\t3\t4\t0\t0\t5\t100\t1\t101\r\n")
        with self.assertRaises(ParseError):
            mf.parse_regen(ScriptDocument.from_bytes(raw))


class AtlasTest(unittest.TestCase):
    def test_roundtrip(self):
        entries = [mf.AtlasEntry("metin2_map", 0, 0, 2, 3, 7)]
        back = mf.parse_atlas_info(ScriptDocument.from_bytes(mf.write_atlas_info(entries)))
        self.assertEqual(back, entries)


class EnvironmentTest(unittest.TestCase):
    def test_roundtrip_with_gradients(self):
        env = mf.EnvironmentData()
        env.gradients = [(mf.Rgba(1, 0, 0, 1), mf.Rgba(0, 0, 1, 1)),
                         (mf.Rgba(0, 1, 0, 1), mf.Rgba(1, 1, 0, 1))]
        env.sky_faces = ["f.dds", "b.dds", "l.dds", "r.dds", "t.dds", "bo.dds"]
        env.cloud_texture = "cloud.dds"
        env.lens_main_texture = "flare.dds"
        raw = mf.write_environment(env)
        back = mf.parse_environment(ScriptDocument.from_bytes(raw))
        self.assertEqual(back.sky_faces, env.sky_faces)
        self.assertEqual(len(back.gradients), 2)
        self.assertEqual(back.cloud_texture, "cloud.dds")
        # deterministic writer: second write is byte-identical
        self.assertEqual(mf.write_environment(back), raw)

    def test_magic_spelling_preserved(self):
        raw = mf.write_environment(mf.EnvironmentData())
        self.assertIn(b"ScriptType         EnvrionmentData\r\n", raw)
        self.assertIn(b"ScriptVersion      1.0000\r\n", raw)

    def test_rejects_fog_inversion(self):
        env = mf.EnvironmentData()
        env.fog_near, env.fog_far = 500.0, 50.0
        with self.assertRaises(ValidationError):
            mf.write_environment(env)

    def test_unknown_keys_and_groups_survive(self):
        env = mf.EnvironmentData()
        raw = mf.write_environment(env)
        injected = raw + (
            b"Group CustomFX\r\n{\r\n\tStrength        3\r\n}\r\n"
            b"// a legacy comment\r\n"
        )
        back = mf.parse_environment(ScriptDocument.from_bytes(injected))
        self.assertEqual(len(back.unknown_groups), 1)
        out = mf.write_environment(back)
        self.assertIn(b"Group CustomFX\r\n{\r\n\tStrength        3\r\n}\r\n", out)
        self.assertIn(b"// a legacy comment\r\n", out)
        # byte-stable on second pass
        self.assertEqual(mf.write_environment(
            mf.parse_environment(ScriptDocument.from_bytes(out))), out)

    def test_rejects_enable_two(self):
        env = mf.EnvironmentData()
        env.fog_enable = 2
        with self.assertRaises(ValidationError):
            mf.write_environment(env)

    def test_rejects_odd_gradient_rows(self):
        env = mf.EnvironmentData()
        env.gradients = [(mf.Rgba(1, 0, 0, 1), mf.Rgba(0, 0, 1, 1))]
        raw = mf.write_environment(env)
        # splice an unpaired rgba row into List Gradient
        marker = b"\tList Gradient\r\n\t{\r\n"
        head, tail = raw.split(marker)
        broken = head + marker + b"\t\t1.000000 0.000000 0.000000 1.000000\r\n" + tail
        with self.assertRaises(ParseError):
            mf.parse_environment(ScriptDocument.from_bytes(broken))


if __name__ == "__main__":
    unittest.main()
