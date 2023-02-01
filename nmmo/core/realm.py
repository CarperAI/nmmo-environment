from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict

import numpy as np

import nmmo
from nmmo.core.log_helper import LogHelper
from nmmo.core.render_helper import RenderHelper
from nmmo.core.replay_helper import ReplayHelper
from nmmo.core.tile import TileState
from nmmo.entity.entity import EntityState
from nmmo.entity.entity_manager import NPCManager, PlayerManager
from nmmo.io.action import Action
from nmmo.lib.datastore.numpy_datastore import NumpyDatastore
from nmmo.systems.exchange import Exchange
from nmmo.systems.item import Item, ItemState


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
      self.log_helper = LogHelper.create(self)

      # Entity handlers
      self.players  = PlayerManager(config, self)
      self.npcs     = NPCManager(config, self)

      # Global item registry
      self.items    = {}

      # Initialize actions
      nmmo.Action.init(config)

   def reset(self, map_id: int = None):
      '''Reset the environment and load the specified map

      Args:
         idx: Map index to load
      ''' 
      self.log_helper.reset()
      self.map.reset(self, map_id or np.random.randint(self.config.MAP_N) + 1)
      self.players.reset()
      self.npcs.reset()
      self.players.spawn()
      self.npcs.spawn()
      self.tick = 0

      # Global item exchange
      self.exchange = Exchange(self)

      # Global item registry
      Item.INSTANCE_ID = 0
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
         # TODO: we should be randomizing these, otherwise the lower ID agents
         # will always go first.
         entID, (atn, args) = merged[priority][0]
         for entID, (atn, args) in merged[priority]:
            ent = self.entity(entID)
            atn.call(self, ent, *args)

      dead = self.players.cull()
      self.npcs.cull()

      #Update map
      self.map.step()
      self.exchange.step(self.tick)
      self.log_helper.update(dead)

      self.tick += 1

      self.replay_helper.update()

      return dead

   def log_milestone(self, category: str, value: float, message: str = None):
      self.log_helper.log_milestone(category, value)
      self.log_helper.log_event(category, value)
      if self.config.LOG_VERBOSE:
         logging.info(f'Milestone: {category} {value} {message}')
