import numpy as np
import unittest
from nmmo.lib.datastore.numpy_datastore import NumpyDatastore


class TestDatastore(unittest.TestCase):

  def test_datastore_object(self):
    datastore = NumpyDatastore()
    datastore.register_object_type("TestObject", ["c1", "c2"])

    o = datastore.create_record("TestObject")
    self.assertEqual([o.get("c1"), o.get("c2")], [0, 0])

    o.update("c1", 1)
    o.update("c2", 2)
    self.assertEqual([o.get("c1"), o.get("c2")], [1, 2])

    np.testing.assert_array_equal(
      datastore.table("TestObject").get([o.id]).values, 
      np.array([[o.id, 1, 2]]))

    o2 = datastore.create_record("TestObject")
    o2.update("c2", 2)
    np.testing.assert_array_equal(
      datastore.table("TestObject").get([o.id, o2.id]).values, 
      np.array([[o.id, 1, 2], [o2.id, 0, 2]]))

    np.testing.assert_array_equal(
      datastore.table("TestObject").where_eq("c2", 2).values, 
      np.array([[o.id, 1, 2], [o2.id, 0, 2]]))

    o.delete()
    np.testing.assert_array_equal(
      datastore.table("TestObject").where_eq("c2", 2).values, 
      np.array([[o2.id, 0, 2]]))

  def test_result_set(self):
    pass

if __name__ == '__main__':
    unittest.main()
