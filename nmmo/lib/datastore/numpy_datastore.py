import numpy as np
from typing import List, Union

from nmmo.lib.datastore.datastore import Datastore, DataTable, ResultSet

class NumpyResultSet(ResultSet):
  def attribute(self, attribute: Union[str, type]) -> float:
    assert self.values.shape[0] == 1
    return float(self.values[0][self.columns[self._attr(attribute)]])

  def rows(self, row_ids):
    return NumpyResultSet(self.values[row_ids], self.columns)

  def where_eq(self, attribute: Union[str, type], value: float) -> ResultSet:
    matching_rows = self.values[:,self.columns[self._attr(attribute)]] == value
    return NumpyResultSet(self.values[matching_rows], self.columns)

class NumpyTable(DataTable):
  def __init__(self, columns: List[str], initial_size: int, dtype=np.float32):
    super().__init__(columns)
    self._dtype  = dtype
    self._max_rows = 0

    self._data = np.zeros((0, len(self._cols)))
    self._expand(initial_size)

  def update(self, id: int, attribute: str, value):
    col = self._cols[attribute] 
    self._data[id, col] = value

  def get(self, ids: List[int]) -> NumpyResultSet:
    return NumpyResultSet(self._data[ids], self._cols)

  def where_eq(self, attribute: str, value: float) -> NumpyResultSet:
    return NumpyResultSet(self._data, self._cols).where_eq(attribute, value)

  def add_row(self) -> int:
    if self._id_allocator.full():
      self._expand(self._max_rows * 2)
    id = self._id_allocator.allocate()
    self._data[id, 0] = id
    return id

  def remove_row(self, id) -> int:
    self._id_allocator.remove(id)
    self._data[id] = 0

  def _expand(self, max_rows: int):
    assert max_rows > self._max_rows
    data = np.zeros((max_rows, len(self._cols)), dtype=self._dtype)
    data[:self._max_rows] = self._data
    self._max_rows = max_rows
    self._id_allocator.expand(max_rows)

    self._data  = data

  def window(self, row_idx: int, col_idx: int, row: int, col: int, radius: int):
    return NumpyResultSet(self._data[(
      (np.abs(self._data[:,row_idx] - row) <= radius) &
      (np.abs(self._data[:,col_idx] - col) <= radius)
    ).ravel()], self._cols)

class NumpyDatastore(Datastore):
  def _create_table(self, columns: List[str]) -> DataTable:
    return NumpyTable(columns, 100)
    
