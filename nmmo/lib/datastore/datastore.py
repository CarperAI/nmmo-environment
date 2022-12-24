from typing import Dict, List, Tuple
from nmmo.lib.datastore.id_allocator import IdAllocator

class DataTable:
  def __init__(self, columns: List[str]):
    self._cols: Dict[str, int] = {}
    self._num_columns: int = 0
    for c in columns:
        self._cols[c] = self._num_columns
        self._num_columns += 1
    self._id_allocator = IdAllocator(100)

  def update(self, id: int, attribute: str, value):
    raise NotImplemented

  def get(self, ids: List[id]):
    raise NotImplemented

  def remove_row(self, id: int):
    raise NotImplemented

  def add_row(self) -> int:
    raise NotImplemented

class Grid:
  def set(self, location: Tuple[int, int], value):
      raise NotImplemented
  
  def move(self, origin: Tuple[int, int], destination: Tuple[int, int]):
      raise NotImplemented

  def window(self, row_min: int, row_max: int, col_min: int, col_max: int):
    raise NotImplemented

class DatastoreObject:
  def __init__(self, datastore, table: DataTable, id: int) -> None:
    self.datastore = datastore
    self.table = table
    self.id = id

  def update(self, attribute, value):
    self.table.update(self.id, attribute, value)

  def get(self, attribute):
    return self.table.get([self.id])[0][self.table._cols[attribute]]

  def delete(self):
    self.table.remove_row(self.id)

class Datastore:
  def __init__(self) -> None:
    self._tables: Dict[str, DataTable] = {}

  def register_object_type(self, object_type: str, columns: List[str]):
    self._tables[object_type] = self._create_table(columns)

  def create_object(self, object_type: str) -> DatastoreObject:
    table = self._tables[object_type]
    row_id = table.add_row()
    return DatastoreObject(self, table, row_id)

  def get(self, object_type: str, object_ids: List[int]):
    return self._tables[object_type].get(object_ids)

  def _create_table(self, columns: List[str]) -> DataTable:
    raise NotImplemented