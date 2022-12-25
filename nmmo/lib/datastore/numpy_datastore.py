import numpy as np
from typing import List

from nmmo.lib.datastore.datastore import Datastore, DataTable

class NumpyTable(DataTable):
  def __init__(self, columns: List[str], initial_size: int, dtype=np.float32):
    super().__init__(columns)
    self._dtype  = dtype
    self._max_rows = 0

    self._data = np.zeros((0, self._num_columns))
    self._expand(initial_size)

  def update(self, id: int, attribute: str, value):
    col = self._cols[attribute] 
    self._data[id, col] = value

  def get(self, ids: List[int]):
    return self._data[ids]

  def add_row(self) -> int:
    if self._id_allocator.full():
      self._expand(self._max_rows * 2)
    return self._id_allocator.allocate()

  def remove_row(self, id) -> int:
    self._id_allocator.remove(id)
    self._data[id] = 0

  def _expand(self, max_rows: int):
    assert max_rows > self._max_rows
    data = np.zeros((max_rows, self._num_columns), dtype=self._dtype)
    data[:self._max_rows] = self._data
    self._max_rows = max_rows
    self._id_allocator.expand(max_rows)

    self._data  = data

  def where_eq(self, col_idx: int, value: float):
    return self._data[self._data[:,col_idx] == value]

  def window(self, row_idx: int, col_idx: int, row: int, col: int, radius: int):
    return self._data[(
      (np.abs(self._data[:,row_idx] - row) <= radius) &
      (np.abs(self._data[:,col_idx] - col) <= radius)
    ).ravel()]


class NumpyDatastore(Datastore):
  def _create_table(self, columns: List[str]) -> DataTable:
    return NumpyTable(columns, 100)
    
