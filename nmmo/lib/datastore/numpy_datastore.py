
import numpy as np
from typing import Dict, List, Tuple

from nmmo.lib.datastore.datastore import Datastore, DataTable, Grid

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

  def get_padded(self, ids: List[int], padding: int):
    data = np.pad(self.get(ids), ((0, padding - len(data)), (0, 0)))

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


class NumpyGrid(Grid):
    def __init__(self, max_rows: int, max_columns: int):
      self.data = np.zeros((max_rows, max_columns), dtype=np.int32)

    def set(self, location: Tuple[int, int], value: int):
      self.data[location] = value
 
    def move(self, origin: Tuple[int, int], destination: Tuple[int, int]):
      self.set(destination, self.data[origin])
      self.data[origin] = 0

    def window(self, row_min: int, row_max: int, col_min: int, col_max: int):
      crop = self.data[row_min:row_max, col_min:col_max].ravel()
      return crop[np.nonzero(crop)]
      

class NumpyDatastore(Datastore):
  def _create_table(self, columns: List[str]) -> DataTable:
    return NumpyTable(columns, 100)
    
