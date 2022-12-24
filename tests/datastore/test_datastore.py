import numpy as np
import unittest
from nmmo.lib.datastore.numpy_datastore import NumpyDatastore


class TestDatastore(unittest.TestCase):

  def test_datastore_object(self):
    datastore = NumpyDatastore()
    datastore.register_object_type("TestObject", ["c1", "c2"])

    o = datastore.create_object("TestObject")
    self.assertEqual([o.get("c1"), o.get("c2")], [0, 0])

    o.update("c1", 1)
    o.update("c2", 2)
    self.assertEqual([o.get("c1"), o.get("c2")], [1, 2])

    np.testing.assert_array_equal(
      datastore.get("TestObject", [o.id]), np.array([[1, 2]]))

if __name__ == '__main__':
    unittest.main()
