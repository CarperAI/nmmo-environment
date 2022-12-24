from pdb import set_trace as T

import numpy as np

from typing import List
import unittest
import lovely_numpy
lovely_numpy.set_config(repr=lovely_numpy.lovely)

from nmmo.lib.datastore.numpy_datastore import NumpyTable, NumpyGrid

class TestNumpyTable(unittest.TestCase):
  def test_continous_table(self):
    table = NumpyTable(["a", "b", "c"], 10, np.float32)
    table.update(2, "a", 2.1)
    table.update(2, "b", 2.2)
    table.update(5, "a", 5.1)
    table.update(5, "c", 5.3)
    np.testing.assert_array_equal(
      table.get([1,2,5]), 
      np.array([[0, 0, 0], [2.1, 2.2, 0], [5.1, 0, 5.3]], dtype=np.float32)
    )

  def test_discrete_table(self):
    table = NumpyTable(["a", "b", "c"], 10, np.int32)
    table.update(2, "a", 11)
    table.update(2, "b", 12)
    table.update(5, "a", 51)
    table.update(5, "c", 53)
    np.testing.assert_array_equal(
      table.get([1,2,5]), 
      np.array([[0, 0, 0], [11, 12, 0], [51, 0, 53]], dtype=np.int32)
    )

  def test_expand(self):
    table = NumpyTable(["a", "b", "c"], 10, np.float32)
    
    table.update(2, "a", 2.1)
    with self.assertRaises(IndexError):
      table.update(10, "a", 10.1)

    table._expand(11)
    table.update(10, "a", 10.1)

    np.testing.assert_array_equal(
      table.get([10,2]), 
      np.array([[10.1, 0, 0], [2.1, 0, 0]], dtype=np.float32)
    )

class TestNumpyGrid(unittest.TestCase):
  def test_grid(self):
    grid = NumpyGrid(10, 20)
    grid.set((1,1), 11)
    grid.set((1,2), 12)
    grid.set((5,5), 55)
    grid.set((8,8), 88)

    np.testing.assert_array_equal(
      grid.window(0, 6, 2, 6), 
      np.array([12, 55], dtype=np.int32)
    )

    grid.move((5,5), (6,6))
    np.testing.assert_array_equal(
      grid.window(0, 6, 2, 6), 
      np.array([12], dtype=np.int32)
    )
    np.testing.assert_array_equal(
      grid.window(0, 7, 2, 7), 
      np.array([12, 55], dtype=np.int32)
    )

    np.testing.assert_array_equal(
      grid.window(0, 20, 0, 20), 
      np.array([11, 12, 55, 88], dtype=np.int32)
    )


  # def test_grid_tables(self):
  #   gt = GridTables(nmmo.Serialized, )
  # def test_dataframe(self):
  #   mock_realm = MockRealm()
  #   df = Dataframe(mock_realm)




if __name__ == '__main__':
    unittest.main()
