from functools import lru_cache
from pdb import set_trace as T
import numpy as np

import nmmo
from nmmo.lib.serialized import SerializedAttributeDef as Attr, SerializedState
from nmmo.lib import material

TileState = SerializedState.subclass(
   "Tile", lambda config: [
      Attr("r", max=config.MAP_SIZE-1),
      Attr("c", max=config.MAP_SIZE-1),
      Attr("entity_id"),
      Attr("material_id", max=config.MAP_N_TILE)
   ])
   
class Tile(TileState):
   def __init__(self, config, realm, r, c):
      super().__init__(realm.datastore, config)
      self.config = config
      self.realm  = realm

      self.r.update(r)
      self.c.update(c)

   @property
   def repr(self):
      return ((self.r, self.c))

   @property
   def pos(self):
      return self.r.val, self.c.val

   @property
   def habitable(self):
      return self.material in material.Habitable

   @property
   def vacant(self):
      return self.entity_id.val == 0 and self.habitable

   @property
   def occupied(self):
      return not self.vacant

   @property
   def impassible(self):
      return self.material in material.Impassible

   @property
   def lava(self):
      return self.material == material.Lava

   def reset(self, mat, config):
      self.state  = mat(config)
      self.mat    = mat(config)

      self.depleted = False
      self.tex      = mat.tex

      self.entity_id.update(0)
      self.material_id.update(self.state.index)
 
   def addEnt(self, ent):
      assert self.entity_id.val == 0
      self.entity_id.update(ent.entID)

   def delEnt(self, entID):
      assert self.entity_id.val == entID
      self.entity_id.update(0)

   def step(self):
      if not self.depleted or np.random.rand() > self.mat.respawn:
         return

      self.depleted = False
      self.state = self.mat

      self.material_id.update(self.state.index)

   def harvest(self, deplete):
      if __debug__:
          assert not self.depleted, f'{self.state} is depleted'
          assert self.state in material.Harvestable, f'{self.state} not harvestable'

      if deplete:
          self.depleted = True
          self.state    = self.mat.deplete(self.config)
          self.material_id.update(self.state.index)

      return self.mat.harvest()
