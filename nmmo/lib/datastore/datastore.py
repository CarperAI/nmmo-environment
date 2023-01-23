from __future__ import annotations
from types import SimpleNamespace
from typing import Dict, List, Tuple, Union
from nmmo.lib.datastore.id_allocator import IdAllocator
class DataTable:
  def __init__(self, num_columns: int):
    self._num_columns = num_columns
    self._id_allocator = IdAllocator(100)

  def update(self, id: int, attribute: str, value):
    raise NotImplementedError

  def get(self, ids: List[id]):
    raise NotImplementedError

  def where_in(self, col: int, values: List):
    raise NotImplementedError
  
  def where_eq(self, col: str, value):
    raise NotImplementedError

  def window(self, row_idx: int, col_idx: int, row: int, col: int, radius: int):
    raise NotImplementedError

  def remove_row(self, id: int):
    raise NotImplementedError

  def add_row(self) -> int:
    raise NotImplementedError

class DatastoreRecord:
  def __init__(self, datastore, table: DataTable, id: int) -> None:
    self.datastore = datastore
    self.table = table
    self.id = id

  def update(self, col: int, value):
    self.table.update(self.id, col, value)

  def get(self, col: int):
    return self.table.get(self.id)[col]

  def delete(self):
    self.table.remove_row(self.id)

class Datastore:
  def __init__(self) -> None:
    self._tables: Dict[str, DataTable] = {}

  def register_object_type(self, object_type: str, num_colums: int):
    if object_type not in self._tables:
      self._tables[object_type] = self._create_table(num_colums)

  def create_record(self, object_type: str) -> DatastoreRecord:
    table = self._tables[object_type]
    row_id = table.add_row()
    return DatastoreRecord(self, table, row_id)

  def table(self, object_type: str) -> DataTable:
    return self._tables[object_type]

  def _create_table(self, num_cols: int) -> DataTable:
    raise NotImplementedError