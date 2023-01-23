from __future__ import annotations

from pdb import set_trace as T
import numpy as np

from collections import defaultdict
from typing import Dict

import nmmo
from nmmo.core.render_helper import RenderHelper
from nmmo.core.replay_helper import ReplayHelper
from nmmo.core.tile import TileState
from nmmo.entity.entity import EntityState
from nmmo.lib.datastore.numpy_datastore import NumpyDatastore
from nmmo.systems.exchange import Exchange
from nmmo.systems.item import Item, ItemState
from nmmo.entity.entity_manager import PlayerManager, NPCManager

from nmmo.io.action import Action
from nmmo.lib import log


def prioritized(entities: Dict, merged: Dict):
   '''Sort actions into merged according to priority'''
   for idx, actions in entities.items():
      for atn, args in actions.items():
         merged[atn.priority].append((idx, (atn, args.values())))
   return merged

class Realm:
   '''Top-level world object'''
   def __init__(self, config):
      self.config   = config
      assert isinstance(config, nmmo.config.Config), f'Config {config} is not a config instance (did you pass the class?)'

      Action.hook(config)

      # Generate maps if they do not exist
      config.MAP_GENERATOR(config).generate_all_maps()

      self.datastore = NumpyDatastore()
      for s in [TileState, EntityState, ItemState]:
         self.datastore.register_object_type(s._name, s._num_attributes)

      # Load the world file
      self.map       = nmmo.core.Map(config, self)

      self.replay_helper = ReplayHelper.create(self)
      self.render_helper = RenderHelper.create(self)

      # Entity handlers
      self.players  = PlayerManager(config, self)
      self.npcs     = NPCManager(config, self)

      # Global item exchange
      self.exchange = Exchange(config)

      # Global item registry
      self.items    = {}

      # Initialize actions
      nmmo.Action.init(config)

   def reset(self, map_id: int = None):
      '''Reset the environment and load the specified map

      Args:
         idx: Map index to load
      ''' 
      Item.INSTANCE_ID = 0
      self.quill = log.Quill(self.config)
      self.map.reset(self, map_id or np.random.randint(self.config.MAP_N) + 1)
      self.players.reset()
      self.npcs.reset()
      self.players.spawn()
      self.npcs.spawn()
      self.tick = 0

      # Global item exchange
      self.exchange = Exchange(self.config)

      # Global item registry
      self.items    = {}

      self.replay_helper.update()

   def packet(self):
      '''Client packet'''
      return {'environment': self.map.repr,
              'border': self.config.MAP_BORDER,
              'size': self.config.MAP_SIZE,
              'resource': self.map.packet,
              'player': self.players.packet,
              'npc': self.npcs.packet,
              'market': self.exchange.packet}

   @property
   def population(self):
      '''Number of player agents'''
      return len(self.players.entities)

   def entity(self, entID):
      e = self.entityOrNone(entID)
      assert e is not None, f'Entity {entID} does not exist'
      return e

   def entityOrNone(self, entID):
      '''Get entity by ID'''
      if entID < 0:
         return self.npcs.get(entID)
      else:
         return self.players.get(entID)

   def step(self, actions):
      '''Run game logic for one tick
      
      Args:
         actions: Dict of agent actions

      Returns:
         dead: List of dead agents
      '''
      # Prioritize actions
      npcActions = self.npcs.actions(self)
      merged     = defaultdict(list)
      prioritized(actions, merged)
      prioritized(npcActions, merged)

      # Update entities and perform actions
      self.players.update(actions)
      self.npcs.update(npcActions)

      #Execute actions
      for priority in sorted(merged):
         # xcxc Should these get hashed with tick?
         entID, (atn, args) = merged[priority][0]
         for entID, (atn, args) in merged[priority]:
            ent = self.entity(entID)
            atn.call(self, ent, *args)

      dead = self.players.cull()
      self.npcs.cull()

      #Update map
      self.map.step()
      self.exchange.step(self.tick)

      self.tick += 1

      self.replay_helper.update()

      return dead
