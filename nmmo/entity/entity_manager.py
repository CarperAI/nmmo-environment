import numpy as np

from collections.abc import Mapping
from typing import Dict, Set
from ordered_set import OrderedSet

import nmmo
from nmmo.systems import combat
from nmmo.entity.npc import NPC
from nmmo.entity import Entity, Player
from nmmo.lib import colors, spawn, log

class EntityGroup(Mapping):
   def __init__(self, config, realm):
      self.datastore = realm.datastore
      self.config = config

      self.entities: Dict[int, Entity]  = {}
      self.dead: Set(int) = {}

   def __len__(self):
      return len(self.entities)

   def __contains__(self, e):
      return e in self.entities

   def __getitem__(self, key) -> Entity:
      return self.entities[key]
   
   def __iter__(self) -> Entity:
      yield from self.entities

   def items(self):
      return self.entities.items()

   @property
   def corporeal(self):
      return {**self.entities, **self.dead}

   @property
   def packet(self):
      return {k: v.packet() for k, v in self.corporeal.items()}

   def reset(self):
      for ent in self.entities.values():
         ent.datastore_object.delete()

      self.entities = {}
      self.dead     = {}


   def spawn(self, entity):
      pos, entID = entity.pos, entity.id.val
      self.realm.map.tiles[pos].addEnt(entity)
      self.entities[entID] = entity
 
   def cull(self):
      self.dead = {}
      for entID in list(self.entities):
         player = self.entities[entID]
         if not player.alive:
            r, c  = player.pos
            entID = player.entID
            self.dead[entID] = player

            self.realm.map.tiles[r, c].delEnt(entID)
            self.entities[entID]._datastore_record.delete()
            del self.entities[entID]

      return self.dead

   def update(self, actions):
      for entID, entity in self.entities.items():
         entity.update(self.realm, actions)


class NPCManager(EntityGroup):
   def __init__(self, config, realm):
      super().__init__(config, realm)
      self.realm   = realm

      self.spawn_dangers = []

   def reset(self):
      super().reset()
      self.idx     = -1

   def spawn(self):
      config = self.config

      if not config.NPC_SYSTEM_ENABLED:
         return

      for _ in range(config.NPC_SPAWN_ATTEMPTS):
         if len(self.entities) >= config.NPC_N:
            break

         if self.spawn_dangers:
            danger = self.spawn_dangers[-1]
            r, c   = combat.spawn(config, danger)
         else:
            center = config.MAP_CENTER
            border = self.config.MAP_BORDER
            r, c   = np.random.randint(border, center+border, 2).tolist()

         npc = NPC.spawn(self.realm, (r, c), self.idx)
         if npc: 
            super().spawn(npc)
            self.idx -= 1

         if self.spawn_dangers:
            self.spawn_dangers.pop()

   def cull(self):
       for entity in super().cull().values():
           self.spawn_dangers.append(entity.spawn_danger)

   def actions(self, realm):
      actions = {}
      for idx, entity in self.entities.items():
         actions[idx] = entity.decide(realm)
      return actions
       
class PlayerManager(EntityGroup):
   def __init__(self, config, realm):
      super().__init__(config, realm)
      self.palette = colors.Palette()
      self.loader  = config.PLAYER_LOADER
      self.realm   = realm

   def reset(self):
      super().reset()
      self.agents  = self.loader(self.config)
      self.spawned = OrderedSet()

   def spawnIndividual(self, r, c, idx):
      pop, agent = next(self.agents)
      agent      = agent(self.config, idx)
      player     = Player(self.realm, (r, c), agent, self.palette.color(pop), pop)
      super().spawn(player)

   def spawn(self):
      #TODO: remove hard check against fixed function
      if self.config.PLAYER_SPAWN_FUNCTION == spawn.spawn_concurrent:
         idx = 0
         for r, c in self.config.PLAYER_SPAWN_FUNCTION(self.config):
            idx += 1

            if idx in self.entities:
                continue

            if idx in self.spawned:
                continue

            self.spawned.add(idx)
            self.spawnIndividual(r, c, idx)

         return
          
      #MMO-style spawning
      for _ in range(self.config.PLAYER_SPAWN_ATTEMPTS):
         if len(self.entities) >= self.config.PLAYER_N:
            break

         r, c   = self.config.PLAYER_SPAWN_FUNCTION(self.config)

         self.spawnIndividual(r, c)

      while len(self.entities) == 0:
         self.spawn()
