from collections import defaultdict
import unittest

from nmmo.lib.serialized import SerializedState

# pylint: disable=no-member,unused-argument

FooState = SerializedState.subclass("FooState", [
  "a", "b", "col"
])

FooState.Limits = {
  "a": (-10, 10),
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
    assert attributes == ["a", "b", "col"]

class TestSerialized(unittest.TestCase):

  def test_serialized(self):
    state = FooState(MockDatastore(), FooState.Limits)

    self.assertEqual(state.a.val, 0)
    state.a.update(1)
    self.assertEqual(state.a.val, 1)
    state.a.update(-20)
    self.assertEqual(state.a.val, -10)
    state.a.update(100)
    self.assertEqual(state.a.val, 10)

if __name__ == '__main__':
  unittest.main()
