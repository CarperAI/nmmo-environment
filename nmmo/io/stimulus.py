from pdb import set_trace as T
from typing import Any
import numpy as np

from nmmo.lib import utils
from nmmo.lib.datastore.datastore import DatastoreRecord

class SerializedVariable:
   CONTINUOUS = False
   DISCRETE   = False
   def __init__(self, datastore_object: DatastoreRecord, val=None, config=None):
 
      self.attr = self.__class__.__name__
      self.min = 0
      self.max = np.inf
      self.val = val
      self.datastore_object = datastore_object
      if config is None:
         config = datastore_object.config
      self.datastore_object = datastore_object
      if config is None:
         config = datastore_object.config

      self.init(config)
      assert self.val is not None, 'Must set a default val upon instantiation or init()'
      assert self.val is not None, 'Must set a default val upon instantiation or init()'

      self.update(self.val)
      self.update(self.val)

   #Defined for cleaner stim files
   def init(self):
      pass

   def packet(self):
      return {
            'val': self.val,
            'max': self.max}

   def update(self, val):
      self.val = min(max(val, self.min), self.max)
      self.datastore_object.update(self.attr, self.val)
      self.datastore_object.update(self.attr, self.val)
      return self



   @classmethod
   def attr(cls, result_set):
      return result_set.attribute(cls.__name__)

class Continuous(SerializedVariable):
   CONTINUOUS = True

class Discrete(Continuous):
   DISCRETE = True


class Serialized(metaclass=utils.IterableNameComparable):
   class Item(metaclass=utils.IterableNameComparable):
      @staticmethod
      def enabled(config):
         return config.ITEM_SYSTEM_ENABLED

      @staticmethod
      def N(config):
         return config.ITEM_N_OBS

      class ID(Continuous):
         def init(self, config):
            self.scale = 0.001

      class ItemType(Discrete):
         def init(self, config):
            self.max   = config.ITEM_N + 1
            self.scale = 1.0 / self.max

      class Level(Continuous):
         def init(self, config):
            self.max   = 99
            self.scale = 1.0 / self.max

      class Capacity(Continuous):
         def init(self, config):
            self.max   = 99
            self.scale = 1.0 / self.max

      class Quantity(Continuous):
         def init(self, config):
            self.max   = 99
            self.scale = 1.0 / self.max

      class Tradable(Discrete):
         def init(self, config):
            self.max   = 1
            self.scale = 1.0

      class MeleeAttack(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class RangeAttack(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class MageAttack(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class MeleeDefense(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class RangeDefense(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class MageDefense(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class HealthRestore(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class ResourceRestore(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class Price(Continuous):
         def init(self, config):
            self.scale = 0.01

      class Equipped(Discrete):
         def init(self, config):
            self.scale = 1.0

      class Owner(Discrete):
         def init(self, config):
            self.scale = 1.0

      class ForSale(Discrete):
         def init(self, config):
            self.scale = 1.0

      class Owner(Discrete):
         def init(self, config):
            self.scale = 1.0

      class ForSale(Discrete):
         def init(self, config):
            self.scale = 1.0

   # TODO: Figure out how to autogen this from Items
   class Market(metaclass=utils.IterableNameComparable):
      @staticmethod
      def enabled(config):
         return config.EXCHANGE_SYSTEM_ENABLED

      @staticmethod
      def N(config):
         return config.EXCHANGE_N_OBS

      class ID(Continuous):
         def init(self, config):
            self.scale = 0.001

      class Index(Discrete):
         def init(self, config):
            self.max   = config.ITEM_N + 1
            self.scale = 1.0 / self.max

      class Level(Continuous):
         def init(self, config):
            self.max   = 99
            self.scale = 1.0 / self.max

      class Capacity(Continuous):
         def init(self, config):
            self.max   = 99
            self.scale = 1.0 / self.max

      class Quantity(Continuous):
         def init(self, config):
            self.max   = 99
            self.scale = 1.0 / self.max

      class Tradable(Discrete):
         def init(self, config):
            self.max   = 1
            self.scale = 1.0

      class MeleeAttack(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class RangeAttack(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class MageAttack(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class MeleeDefense(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class RangeDefense(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class MageDefense(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class HealthRestore(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class ResourceRestore(Continuous):
         def init(self, config):
            self.max   = 100
            self.scale = 1.0 / self.max

      class Price(Continuous):
         def init(self, config):
            self.scale = 0.01

      class Equipped(Discrete):
         def init(self, config):
            self.scale = 1.0

