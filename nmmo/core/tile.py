from pdb import set_trace as T
import numpy as np

import nmmo
from nmmo.lib import material

class Tile:
   def __init__(self, config, realm, r, c):
      self.config = config
      self.realm  = realm

      self.datastore_object = realm.datastore.create_object(nmmo.Serialized.Tile)

      self.r     = nmmo.Serialized.Tile.R(self.datastore_object, r)
      self.c     = nmmo.Serialized.Tile.C(self.datastore_object, c)
      self.nEnts = nmmo.Serialized.Tile.NEnts(self.datastore_object)
      self.index = nmmo.Serialized.Tile.Index(self.datastore_object, 0)

   @property
   def repr(self):
      return ((self.r, self.c))

   @property
   def pos(self):
      return self.r.val, self.c.val

   @property
   def habitable(self):
      return self.mat in material.Habitable

   @property
   def vacant(self):
      return len(self.ents) == 0 and self.habitable

   @property
   def occupied(self):
      return not self.vacant

   @property
   def impassible(self):
      return self.mat in material.Impassible

   @property
   def lava(self):
      return self.mat == material.Lava

   def reset(self, mat, config):
      self.state  = mat(config)
      self.mat    = mat(config)

      self.depleted = False
      self.tex      = mat.tex
      self.ents     = {}

      self.nEnts.update(0)
      self.index.update(self.state.index)
 
   def addEnt(self, ent):
      assert ent.entID not in self.ents
      self.nEnts.update(1)
      self.ents[ent.entID] = ent

   def delEnt(self, entID):
      assert entID in self.ents
      self.nEnts.update(0)
      del self.ents[entID]

   def step(self):
      if not self.depleted or np.random.rand() > self.mat.respawn:
         return

      self.depleted = False
      self.state = self.mat

      self.index.update(self.state.index)

   def harvest(self, deplete):
      if __debug__:
          assert not self.depleted, f'{self.state} is depleted'
          assert self.state in material.Harvestable, f'{self.state} not harvestable'

      if deplete:
          self.depleted = True
          self.state    = self.mat.deplete(self.config)
          self.index.update(self.state.index)

      return self.mat.harvest()
