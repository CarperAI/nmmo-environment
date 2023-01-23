from collections import defaultdict
import unittest

from nmmo.lib.serialized import SerializedState

FooState = SerializedState.subclass("FooState", [
  "a", "min_attr", "max_attr"
])

FooState.Limits = lambda: {
  "a": (0, 10),
  "min_attr": (10, 100),
  "max_attr": (0, 100),
}
class MockDatastoreRecord():
  def __init__(self):
    self._data = defaultdict(lambda: 0)

  def get(self, name):
    return self._data[name]

  def update(self, name, value):
    self._data[name] = value

class MockDatastore():
  def create_record(self, name):
    return MockDatastoreRecord()

  def register_object_type(self, name, attributes):
    assert name == "FooState"
    assert attributes == ["a", "min_attr", "max_attr"]

class TestSerialized(unittest.TestCase):

  def test_serialized(self):
    state = FooState(MockDatastore(), {
      "min_attr": (10, 100),
      "max_attr": (0, 100),
    })

    self.assertEqual(state.a.val, 0)
    state.a.update(1)
    self.assertEqual(state.a.val, 1)

    with self.assertRaises(AssertionError):
      state.min_attr.update(3)
    state.min_attr.update(10)
    self.assertEqual(state.min_attr.val, 10)

    self.assertEqual(state.max_attr.val, 0)
    with self.assertRaises(AssertionError):
      state.max_attr.update(101)
    state.max_attr.update(100)
    self.assertEqual(state.max_attr.val, 100)

if __name__ == '__main__':
    unittest.main()
