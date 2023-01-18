from __future__ import annotations
from typing import Dict, List, Tuple, Union
from nmmo.lib.datastore.id_allocator import IdAllocator
class DataTable:
  def __init__(self, columns: List[str]):
    self._cols: Dict[str, int] = {
      c:i for i, c in enumerate(["_row_id"] + columns)
    }

    self._id_allocator = IdAllocator(100)

  def update(self, id: int, attribute: str, value):
    raise NotImplementedError

  def get(self, ids: List[id]) -> ResultSet:
    raise NotImplementedError

  def where_eq(self, attribute: str, value: float) -> ResultSet:
    raise NotImplementedError

  def window(self, row_idx: int, col_idx: int, row: int, col: int, radius: int) -> ResultSet:
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
    self.row = self.table.get([self.id])

  def update(self, attribute, value):
    self.table.update(self.id, attribute, value)

  def get(self, attribute):
    return self.table.get([self.id]).attribute(attribute)

  def delete(self):
    self.table.remove_row(self.id)

class Datastore:
  def __init__(self) -> None:
    self._tables: Dict[str, DataTable] = {}

  def register_object_type(self, object_type: str, columns: List[str]):
    self._tables[object_type] = self._create_table(columns)

  def create_record(self, object_type: str) -> DatastoreRecord:
    table = self._tables[object_type]
    row_id = table.add_row()
    return DatastoreRecord(self, table, row_id)

  def table(self, object_type: str) -> DataTable:
    return self._tables[object_type]

  def _create_table(self, columns: List[str]) -> DataTable:
    raise NotImplementedError