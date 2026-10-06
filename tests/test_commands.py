import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from newschool.commands import CompositeCommand, FnCommand, MoveObjectCommand, UndoStack
from newschool.errors import ValidationError
from newschool.mapfiles import ObjectInstance


class UndoStackTest(unittest.TestCase):
    def test_execute_undo_redo(self):
        state = {"x": 0}
        stack = UndoStack()
        stack.execute(FnCommand("inc", lambda: state.update(x=1), lambda: state.update(x=0)))
        self.assertEqual(state["x"], 1)
        self.assertEqual(stack.undo(), "inc")
        self.assertEqual(state["x"], 0)
        self.assertEqual(stack.redo(), "inc")
        self.assertEqual(state["x"], 1)

    def test_redo_cleared_by_new_command(self):
        state = {"x": 0}
        stack = UndoStack()
        stack.execute(FnCommand("a", lambda: state.update(x=1), lambda: state.update(x=0)))
        stack.undo()
        stack.execute(FnCommand("b", lambda: state.update(x=2), lambda: state.update(x=0)))
        self.assertFalse(stack.can_redo)
        self.assertEqual(state["x"], 2)

    def test_group_undoes_as_one(self):
        state = {"x": 0}
        stack = UndoStack()
        stack.begin_group("two steps")
        stack.execute(FnCommand("s1", lambda: state.update(x=1), lambda: state.update(x=0)))
        stack.execute(FnCommand("s2", lambda: state.update(x=2), lambda: state.update(x=1)))
        stack.end_group()
        self.assertEqual(stack.undo_depth, 1)
        stack.undo()
        self.assertEqual(state["x"], 0)
        self.assertEqual(stack.history(), [])

    def test_empty_group_records_nothing(self):
        stack = UndoStack()
        stack.begin_group("empty")
        stack.end_group()
        self.assertFalse(stack.can_undo)

    def test_limit_trims_oldest(self):
        stack = UndoStack(limit=2)
        for i in range(3):
            stack.execute(FnCommand(f"c{i}", lambda: None, lambda: None))
        self.assertEqual(stack.history(), ["c1", "c2"])

    def test_undo_empty_raises(self):
        with self.assertRaises(ValidationError):
            UndoStack().undo()
        with self.assertRaises(ValidationError):
            UndoStack().redo()

    def test_failed_validation_does_not_execute(self):
        ran = []
        stack = UndoStack()
        cmd = FnCommand("bad", lambda: ran.append(1), lambda: None,
                        validate_fn=lambda: (_ for _ in ()).throw(ValidationError("nope")))
        with self.assertRaises(ValidationError):
            stack.execute(cmd)
        self.assertEqual(ran, [])


class MoveObjectCommandTest(unittest.TestCase):
    def _holder(self, obj):
        return {"obj": obj}

    def test_move_and_undo(self):
        obj = ObjectInstance(x=1, y=2, z=3, crc=5, yaw=0, pitch=0, roll=0, height_bias=0)
        box = self._holder(obj)
        stack = UndoStack()
        stack.execute(MoveObjectCommand(dx=10, dy=-2, dz=0.5, lookup=lambda: box["obj"]))
        self.assertEqual((obj.x, obj.y, obj.z), (11.0, 0.0, 3.5))
        stack.undo()
        self.assertEqual((obj.x, obj.y, obj.z), (1.0, 2.0, 3.0))
        stack.redo()
        self.assertEqual((obj.x, obj.y, obj.z), (11.0, 0.0, 3.5))

    def test_rejects_non_finite(self):
        obj = ObjectInstance(x=0, y=0, z=0, crc=1, yaw=0, pitch=0, roll=0, height_bias=0)
        with self.assertRaises(ValidationError):
            UndoStack().execute(MoveObjectCommand(dx=float("nan"), lookup=lambda: obj))
        self.assertEqual((obj.x, obj.y, obj.z), (0, 0, 0))

    def test_deleted_target_fails_loudly(self):
        box = self._holder(ObjectInstance(x=0, y=0, z=0, crc=1, yaw=0, pitch=0, roll=0,
                                           height_bias=0))
        stack = UndoStack()
        stack.execute(MoveObjectCommand(dx=1, lookup=lambda: box["obj"]))
        box["obj"] = None  # object deleted afterwards
        with self.assertRaises(ValidationError):
            stack.undo()
        # failed undo keeps the command on the stack (nothing silently lost)
        self.assertTrue(stack.can_undo)

    def test_composite_rolls_back_partial_do(self):
        state = {"x": 0}
        good = FnCommand("good", lambda: state.update(x=1), lambda: state.update(x=0))
        bad = FnCommand("bad", lambda: (_ for _ in ()).throw(RuntimeError("boom")),
                        lambda: None)
        with self.assertRaises(RuntimeError):
            CompositeCommand("grp", [good, bad]).do()
        self.assertEqual(state["x"], 0)  # prefix rolled back

    def test_group_abort(self):
        stack = UndoStack()
        stack.begin_group("work")
        stack.execute(FnCommand("s", lambda: None, lambda: None))
        stack.abort_group()
        self.assertFalse(stack.can_undo)
        with self.assertRaises(ValidationError):
            stack.abort_group()


class CompositeCommandTest(unittest.TestCase):
    def test_validates_members(self):
        good = FnCommand("g", lambda: None, lambda: None)
        bad = FnCommand("b", lambda: None, lambda: None,
                        validate_fn=lambda: (_ for _ in ()).throw(ValidationError("x")))
        with self.assertRaises(ValidationError):
            CompositeCommand("grp", [good, bad]).validate()
        with self.assertRaises(ValidationError):
            CompositeCommand("empty").validate()


if __name__ == "__main__":
    unittest.main()
