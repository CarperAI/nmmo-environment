from pdb import set_trace as T

import numpy as np

import unittest
import lovely_numpy
lovely_numpy.set_config(repr=lovely_numpy.lovely)

from nmmo.lib.datastore.numpy_datastore import NumpyTable    

class TestNumpyTable(unittest.TestCase):
  def test_continous_table(self):
    table = NumpyTable(["a", "b", "c"], 10, np.float32)
    table.update(2, "a", 2.1)
    table.update(2, "b", 2.2)
    table.update(5, "a", 5.1)
    table.update(5, "c", 5.3)
    np.testing.assert_array_equal(
      table.get([1,2,5]).values, 
      np.array([[0, 0, 0, 0], [0, 2.1, 2.2, 0], [0, 5.1, 0, 5.3]], dtype=np.float32)
    )

  def test_discrete_table(self):
    table = NumpyTable(["a", "b", "c"], 10, np.int32)
    table.update(2, "a", 11)
    table.update(2, "b", 12)
    table.update(5, "a", 51)
    table.update(5, "c", 53)
    np.testing.assert_array_equal(
      table.get([1,2,5]).values, 
      np.array([[0, 0, 0, 0], [0, 11, 12, 0], [0, 51, 0, 53]], dtype=np.int32)
    )

  def test_expand(self):
    table = NumpyTable(["a", "b", "c"], 10, np.float32)

    table.update(2, "_row_id", 2)
    table.update(2, "a", 2.1)
    with self.assertRaises(IndexError):
      table.update(10, "a", 10.1)

    table._expand(11)
    table.update(10, "_row_id", 10)
    table.update(10, "a", 10.1)

    np.testing.assert_array_equal(
      table.get([10, 2]).values, 
      np.array([[10, 10.1, 0, 0], [2, 2.1, 0, 0]], dtype=np.float32)
    )

if __name__ == '__main__':
    unittest.main()
