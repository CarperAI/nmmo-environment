from pdb import set_trace as T
from typing import Any, Dict
import numpy as np
import random

import functools

import gym
from pettingzoo import ParallelEnv

import nmmo
from nmmo import entity, core, emulation
from nmmo.core import terrain
from nmmo.core.log_helper import LogHelper
from nmmo.core.render_helper import RenderHelper
from nmmo.core.replay_helper import ReplayHelper
from nmmo.core.tile import Tile
from nmmo.entity.entity import Entity
from nmmo.lib import log
from nmmo.infrastructure import DataType
from nmmo.systems import item as Item
from nmmo.core.config import Config


class Env(ParallelEnv):
   '''Environment wrapper for Neural MMO using the Parallel PettingZoo API

   Neural MMO provides complex environments featuring structured observations/actions,
   variably sized agent populations, and long time horizons. Usage in conjunction
   with RLlib as demonstrated in the /projekt wrapper is highly recommended.'''

   def __init__(self, config: Config=nmmo.config.Default(), seed=None):
      if seed is not None:
          np.random.seed(seed)
          random.seed(seed)

      super().__init__()

      self.config     = config
      self.realm      = core.Realm(config)

      self.render_helper = RenderHelper.from_config(config)
      self.replay_helper = ReplayHelper.from_config(self.config, self.realm)
      self.log_helper = LogHelper.from_config(config, self.realm)

      self.initialized  = False

   @functools.lru_cache(maxsize=None)
   def observation_space(self, agent: int):
      '''Neural MMO Observation Space

      Args:
         agent: Agent ID

      Returns:
         observation: gym.spaces object contained the structured observation
         for the specified agent. Each visible object is represented by
         continuous and discrete vectors of attributes. A 2-layer attentional
         encoder can be used to convert this structured observation into
         a flat vector embedding.'''

      observation = {}
      for entity in sorted(nmmo.Serialized.values()):
         if not entity.enabled(self.config):
            continue

         rows       = entity.N(self.config)
         continuous = 0
         discrete   = 0

         for _, attr in entity:
            if attr.DISCRETE:
               discrete += 1
            if attr.CONTINUOUS:
               continuous += 1

         name = entity.__name__
         observation[name] = gym.spaces.Dict({
               'Continuous': gym.spaces.Box(
                        low=-2**20, high=2**20,
                        shape=(rows, continuous),
                        dtype=DataType.CONTINUOUS),
               'Discrete': gym.spaces.Box(
                        low=0, high=4096,
                        shape=(rows, discrete),
                        dtype=DataType.DISCRETE),
               'Mask': gym.spaces.Box(
                        low=0, high=1,
                        shape=(rows,),
                        dtype=DataType.DISCRETE),
               })

      return gym.spaces.Dict(observation)

   @functools.lru_cache(maxsize=None)
   def action_space(self, agent):
      '''Neural MMO Action Space

      Args:
         agent: Agent ID

      Returns:
         actions: gym.spaces object contained the structured actions
         for the specified agent. Each action is parameterized by a list
         of discrete-valued arguments. These consist of both fixed, k-way
         choices (such as movement direction) and selections from the
         observation space (such as targeting)'''
      actions = {}
      for atn in sorted(nmmo.Action.edges(self.config)):
         actions[atn] = {}
         for arg in sorted(atn.edges):
            n                 = arg.N(self.config)
            actions[atn][arg] = gym.spaces.Discrete(n)

         actions[atn] = gym.spaces.Dict(actions[atn])

      return gym.spaces.Dict(actions)


   ############################################################################
   ### Core API
   def reset(self, map_id=None):
      '''OpenAI Gym API reset function

      Loads a new game map and returns initial observations

      Args:
         idx: Map index to load. Selects a random map by default


      Returns:
         observations, as documented by _compute_observations()

      Notes:
         Neural MMO simulates a persistent world. Ideally, you should reset
         the environment only once, upon creation. In practice, this approach
         limits the number of parallel environment simulations to the number
         of CPU cores available. At small and medium hardware scale, we
         therefore recommend the standard approach of resetting after a long
         but finite horizon: ~1000 timesteps for small maps and
         5000+ timesteps for large maps
      '''

      self.realm.reset(map_id)
      self.agents = list(self.realm.players.keys())
      self.log_helper.reset()
      self.replay_helper.update()

      self.initialized = True

      return self._compute_observations()

   def step(self, actions):
      '''Simulates one game tick or timestep

      Args:
         actions: A dictionary of agent decisions of format::

               {
                  agent_1: {
                     action_1: [arg_1, arg_2],
                     action_2: [...],
                     ...
                  },
                  agent_2: {
                     ...
                  },
                  ...
               }

            Where agent_i is the integer index of the i\'th agent 

            The environment only evaluates provided actions for provided
            agents. Unprovided action types are interpreted as no-ops and
            illegal actions are ignored

            It is also possible to specify invalid combinations of valid
            actions, such as two movements or two attacks. In this case,
            one will be selected arbitrarily from each incompatible sets.

            A well-formed algorithm should do none of the above. We only
            Perform this conditional processing to make batched action
            computation easier.

      Returns:
         (dict, dict, dict, None):

         observations:
            A dictionary of agent observations of format::

               {
                  agent_1: obs_1,
                  agent_2: obs_2,
                  ...
               }

            Where agent_i is the integer index of the i\'th agent and
            obs_i is specified by the observation_space function.
           
         rewards:
            A dictionary of agent rewards of format::

               {
                  agent_1: reward_1,
                  agent_2: reward_2,
                  ...
               }

            Where agent_i is the integer index of the i\'th agent and
            reward_i is the reward of the i\'th' agent.

            By default, agents receive -1 reward for dying and 0 reward for
            all other circumstances. Override Env.reward to specify
            custom reward functions
 
         dones:
            A dictionary of agent done booleans of format::

               {
                  agent_1: done_1,
                  agent_2: done_2,
                  ...
               }

            Where agent_i is the integer index of the i\'th agent and
            done_i is a boolean denoting whether the i\'th agent has died.

            Note that obs_i will be a garbage placeholder if done_i is true.
            This is provided only for conformity with PettingZoo. Your
            algorithm should not attempt to leverage observations outside of
            trajectory bounds. You can omit garbage obs_i values by setting
            omitDead=True.

         infos:
            A dictionary of agent infos of format:

               {
                  agent_1: None,
                  agent_2: None,
                  ...
               }

            Provided for conformity with PettingZoo
      '''
      assert self.initialized, 'step before reset'

      actions = self._process_actions(actions)
      dones = self.realm.step(self.actions)
      obs = self._compute_observations()
      rewards = self._compute_rewards()
      infos  = self._compute_infos()

      self.log_helper.log_env(self)
      self.replay_helper.update()
      return obs, rewards, dones, infos



   def _xcxc(self):
      for entID, ent in self.realm.players.items():
         ob = obs[entID]
         self.obs[entID] = ob
         if ent.agent.scripted:
            atns = ent.agent(ob)
            for atn, args in atns.items():
               for arg, val in args.items():
                  atns[atn][arg] = arg.deserialize(self.realm, ent, val)
            self.actions[entID] = atns

         else:
            obs[entID]     = ob
            rewards[entID], infos[entID] = self.reward(ent)
            dones[entID]   = False
      

   def _process_actions(self, actions: Dict[int, Dict[str, Dict[str, Any]]]):
      #Preprocess actions for neural models
      for entID in list(actions.keys()):
         #TODO: Should this silently fail? Warning level options?
         if entID not in self.realm.players:
            continue

         ent = self.realm.players[entID]

         # Fix later -- don't allow action inputs for scripted agents
         if ent.agent.scripted:
             continue

         if not ent.alive:
            continue

         self.actions[entID] = {}
         for atn, args in actions[entID].items():
            self.actions[entID][atn] = {}
            drop = False
            for arg, val in args.items():
               if arg.argType == nmmo.action.Fixed:
                  self.actions[entID][atn][arg] = arg.edges[val]
               elif arg == nmmo.action.Target:
                  # xcxc
                  # targ = self.action_lookup[entID]['Entity'][val]
                  targ = 1
                  # xcxc
                  # targ = self.action_lookup[entID]['Entity'][val]
                  targ = 1

                  #TODO: find a better way to err check for dead/missing agents
                  try:
                    self.actions[entID][atn][arg] = self.realm.entity(targ)
                  except:
                    #print(self.realm.players.entities)
                    #print(val, targ, np.where(np.array(self.action_lookup[entID]['Entity']) != 0), self.action_lookup[entID]['Entity'])
                    del self.actions[entID][atn]
               elif atn in (nmmo.action.Sell, nmmo.action.Use, nmmo.action.Give) and arg == nmmo.action.Item:
                  if val >= len(ent.inventory._items):
                      drop = True
                      continue
                  itm = [e for e in ent.inventory._items][val]
                  if type(itm) == Item.Gold:
                      drop = True
                      continue
                  self.actions[entID][atn][arg] = itm
               elif atn == nmmo.action.Buy and arg == nmmo.action.Item:
                  if val >= len(self.realm.exchange.item_listings):
                      drop = True
                      continue
                  itm = self.realm.exchange.item_listings[val]
                  itm = self.realm.exchange.item_listings[val]
                  self.actions[entID][atn][arg] = itm
               elif __debug__: #Fix -inf in classifier and assert err on bad atns
                  assert False, f'Argument {arg} invalid for action {atn}'
               else:
                  assert False

            # Cull actions with bad args
            if drop and atn in self.actions[entID]:
                del self.actions[entID][atn]

   def _compute_observations(self, agents=None):
      '''Neural MMO Observation API

      Args:
         agents: List of agents to return observations for. If None, returns
         observations for all agents

      Returns:
         obs: Dictionary of observations for each agent
         obs[agent_id] = {
            "Entity": [e1, e2, ...],
            "Tile": [t1, t2, ...],
            "Inventory": [i1, i2, ...],
            "Market": [m1, m2, ...],
            "ActionTargets": {
               "Attack": [a1, a2, ...],
               "Sell": [s1, s2, ...],
               "Buy": [b1, b2, ...],
               "Move": [m1, m2, ...],
            }
         '''

      obs = {}
      agent_ids = [p.datastore_object.id for p in (agents or self.agents)]
      agent_rows = Entity.Query.by_ids(self.realm.datastore, agent_ids)
      market = Item.Query.for_sale(self.realm.datastore)

      for agent_row in agent_rows:
         agent_id = Entity.get(agent_row, 'id')

         visible_entities = Entity.Query.window(
            self.realm.datastore, 
            agent_row,
            self.config.PLAYER_VISION_RADIUS
         )
         visible_tiles = Tile.Query.window(
            *Entity.Query.position(agent_row),
            self.config.PLAYER_VISION_RADIUS)
         
         inventory = Item.Query.by_owner(self.realm.datastore, agent_id)
         # TODO(daveey) pad these
         obs[agent_id] = {
            "Entity": visible_entities,
            "Tile": visible_tiles,
            "Inventory": inventory,
            "Market": market,
            # TODO(daveey): implement these
            "ActionTargets": {
               "Attack": visible_entities,
               "Sell": inventory,
               "Buy": market,
               "Move": visible_tiles
            }
         }

      return obs

   def _compute_rewards(self, player):
      '''Computes the reward for the specified agent

      Override this method to create custom reward functions. You have full
      access to the environment state via self.realm. Our baselines do not
      modify this method; specify any changes when comparing to baselines

      Args:
         player: player object

      Returns:
         reward:
            The reward for the actions on the previous timestep of the
            entity identified by entID.
      '''
      info = {'population': player.pop}
 
      if player.entID not in self.realm.players:
         return -1, info

      if not player.diary:
         return 0, info

      achievement_rewards = player.diary.update(self.realm, player)
      reward = sum(achievement_rewards.values())

      info = {**info, **achievement_rewards}
      return reward, info
      
   ############################################################################
   # PettingZoo API
   ############################################################################

   def render(self, mode='human'):
      '''For conformity with the PettingZoo API only; rendering is external'''
      pass

   @property
   def agents(self):
      '''For conformity with the PettingZoo API only; rendering is external'''
      return self.realm.players.keys()

   def close(self):
       '''For conformity with the PettingZoo API only; rendering is external'''
       pass
   
   metadata = {'render.modes': ['human'], 'name': 'neural-mmo'}

