from __future__ import annotations
from ast import Tuple

import math
from types import SimpleNamespace
from typing import Dict, List
from nmmo.lib.datastore.datastore import Datastore, DatastoreRecord

"""
This code defines classes for serializing and deserializing data 
in a structured way. 

The SerializedAttribute class represents a single attribute of a 
record and provides methods for updating and querying its value, 
as well as enforcing minimum and maximum bounds on the value. 

The SerializedState class serves as a base class for creating 
serialized representations of specific types of data, using a 
list of attribute names to define the structure of the data. 
The subclass method is a factory method for creating subclasses 
of SerializedState that are tailored to specific types of data.
"""

class SerializedAttribute():
  def __init__(self, 
      name: str, 
      datastore_record: DatastoreRecord,
      column: int, min=-math.inf, max=math.inf) -> None:
    self._name = name
    self._datastore_record = datastore_record
    self._column = column
    self._min = min
    self._max = max
    self._val = 0

  @property
  def val(self):
    return self._val

  def update(self, value):
    value = min(self._max, max(self._min, value))
    
    self._datastore_record.update(self._column, value)
    self._val = value

  @property
  def min(self):
    return self._min

  @property
  def max(self):
    return self._max
    
  def increment(self, val=1, max_v=math.inf):
    self.update(min(max_v, self.val + val))
    return self

  def decrement(self, val=1, min_v=-math.inf):
    self.update(max(min_v, self.val - val))
    return self

  @property
  def empty(self):
    return self.val == 0

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
  def subclass(name: str, attributes: List[str]):
    class Subclass(SerializedState):
      _name = name
      _attr_name_to_col = {a: i for i, a in enumerate(attributes)}
      _attr_col_to_name = {i: a for i, a in enumerate(attributes)}
      _num_attributes = len(attributes)

      def __init__(self, datastore: Datastore, 
                   limits: Dict[str, Tuple[float, float]] = {}):
        self._datastore_record = datastore.create_record(name)
        for attr, col in self._attr_name_to_col.items():
          try:
            setattr(self, attr, 
              SerializedAttribute(attr, self._datastore_record, col, 
                *limits.get(attr, (-math.inf, math.inf))))
          except: 
            raise RuntimeError('Failed to set attribute' + attr)

      @classmethod
      def parse_array(cls, data) -> SimpleNamespace:
        # Takes in a data array and returns a SimpleNamespace object with 
        # attribute names as keys and corresponding values from the input 
        # data array.
        assert len(data) == cls._num_attributes, \
          f"Expected {cls._num_attributes} attributes, got {len(data)}"
        return SimpleNamespace(**{
          attr: data[col] for attr, col in cls._attr_name_to_col.items()
        })

    return Subclass
