from __future__ import annotations

import math
from nmmo.lib.datastore.datastore import DatastoreRecord

class SerializedAttributeDef():
  def __init__(self, 
    name: str, 
    min: float = 0, 
    max: float = math.inf):

    self._name = name
    self._min = min
    self._max = max

class SerializedAttribute():
  def __init__(self, attribute_def: SerializedAttributeDef, datastore_record: DatastoreRecord) -> None:
    self._def = attribute_def
    self._datastore_record = datastore_record

  @property
  def val(self):
    return min(
      self._def._max,
        max(self._def._min, 
            self._datastore_record.get(self._def._name))) 
  def update(self, value):
    self._datastore_record.update(self._def._name, value)

  @property
  def min(self):
    return self._def._min

  @property
  def max(self):
    return self._def._max
    
  def increment(self, val=1):
    self.update(self.val + val)
    return self

  def decrement(self, val=1):
    self.update(self.val - val)
    return self

  @property
  def empty(self):
    return self.val == 0

  def __add__(self, other):
    self.increment(other)
    return self

  def __sub__(self, other):
    self.decrement(other)
    return self

  def __eq__(self, other):
    return self.val == other

  def __ne__(self, other):
    return self.val != other

  def __lt__(self, other):
    return self.val < other

  def __le__(self, other):
    return self.val <= other

  def __gt__(self, other):
    return self.val > other

  def __ge__(self, other):
    return self.val >= other

class SerializedState():
  @staticmethod
  def subclass(name: str, attributes_def_fn):
    class Subclass(SerializedState):
      _name = name
      _attributes_def_fn = attributes_def_fn
      _initialized = False
       
      def __init__(self, datastore, config):
        if not Subclass._initialized:
          Subclass._attribute_defs = Subclass._attributes_def_fn(config)
          Subclass._attr_name_to_def = {a._name: a for a in Subclass._attribute_defs}
          Subclass._attr_name_to_col = {a._name: i for i, a in enumerate(Subclass._attribute_defs)}
          Subclass._attr_col_to_name = {i: a._name for i, a in enumerate(Subclass._attribute_defs)}
          datastore.register_object_type(name, [a._name for a in attributes_def_fn(config)])

        self._datastore_record = datastore.create_record(name)
        for attr_def in self._attribute_defs:
          try:
            setattr(self, attr_def._name, SerializedAttribute(attr_def, self._datastore_record))
          except: 
            print('Failed to set attribute', attr_def._name)
            raise    
    return Subclass
