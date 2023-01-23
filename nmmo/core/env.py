import itertools
from typing import Any, Dict, List
import numpy as np
import random

import functools

import gym
from pettingzoo.utils.env import ParallelEnv, AgentID

import nmmo
from nmmo import core
from nmmo.core.agent import Agent
from nmmo.core.log_helper import LogHelper
from nmmo.core.observation import Observation
from nmmo.core.tile import Tile
from nmmo.entity.entity import Entity, EntityState
from nmmo.core.config import Default
from nmmo.systems.item import Item, ItemState
from scripted.baselines import Scripted


class Env(ParallelEnv):
  '''Environment wrapper for Neural MMO using the Parallel PettingZoo API

  Neural MMO provides complex environments featuring structured observations/actions,
  variably sized agent populations, and long time horizons. Usage in conjunction
  with RLlib as demonstrated in the /projekt wrapper is highly recommended.'''

  def __init__(self,
    config: Default = nmmo.config.Default(), seed=None):
    if seed is not None:
      np.random.seed(seed)
      random.seed(seed)

    super().__init__()

    self.config = config
    self.realm = core.Realm(config)

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

    def box(rows, cols): return gym.spaces.Box(
      low=-2**20, high=2**20,
      shape=(rows, cols),
      dtype=np.float32
    )

    return gym.spaces.Dict({
      "Tile": box(self.config.MAP_N_OBS, len(Tile._attribute_defs)),
      "Entity": box(self.config.PLAYER_N_OBS, len(Entity._attribute_defs)),
      "Inventory": box(self.config.ITEM_N_OBS, len(Item._attribute_defs)),
      "Market": box(self.config.EXCHANGE_N_OBS, len(Item._attribute_defs)),
    })

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
        n = arg.N(self.config)
        actions[atn][arg] = gym.spaces.Discrete(n)

      actions[atn] = gym.spaces.Dict(actions[atn])

    return gym.spaces.Dict(actions)

  ############################################################################
  # Core API

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
    self.initialized = True
    self.obs = self._compute_observations()

    return {a: o.to_gym() for a,o in self.obs.items()}

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
    assert self.obs is not None, 'step() called before reset'

    actions = self._process_actions(actions, self.obs)

    # Compute actions for scripted agents, add them into the action dict,
    # and remove them from the observations.
    for eid, ent in self.realm.players.items():
      if isinstance(ent.agent, Scripted):
        assert eid not in actions, f'Received an action for a scripted agent {eid}'
        atns = ent.agent(self.obs[eid])
        for atn, args in atns.items():
          for arg, val in args.items():
            atns[atn][arg] = arg.deserialize(self.realm, ent, val)
            actions[eid] = atns
        del self.obs[eid]

    dones = self.realm.step(actions)

    # Store the observations, since actions reference them
    self.obs = self._compute_observations()
    gym_obs = {a: o.to_gym() for a,o in self.obs.items()}

    rewards, infos = self._compute_rewards(self.obs.keys())

    # xcxc
    # self.realm.log_env(self)
    return gym_obs, rewards, dones, infos

  def _process_actions(self, 
      actions: Dict[int, Dict[str, Dict[str, Any]]], 
      obs: Dict[int, Observation]):

    processed_actions = {}

    for entity_id in actions.keys():
      assert entity_id in self.realm.players, f'Entity {entity_id} not in realm'
      entity = self.realm.players[entity_id]
      entity_obs = obs[entity_id]

      assert entity.alive, f'Entity {entity_id} is dead'

      processed_actions[entity_id] = {}
      for atn, args in actions[entity_id].items():
        actions[entity_id][atn] = {}

        for arg, val in args.items():

          if arg.argType == nmmo.action.Fixed:
            actions[entity_id][atn][arg] = arg.edges[val]

          elif arg == nmmo.action.Target:
            target_id = entity_obs.entities.ids[val]
            target = self.realm.entitiyOrNone(target_id)
            if target is not None:
              actions[entity_id][atn][arg] = target
            else:
              del actions[entity_id][atn]

          elif atn in (nmmo.action.Sell, nmmo.action.Use, nmmo.action.Give) and arg == nmmo.action.Item:
            item_id = entity_obs.inventory.ids[val]
            actions[entity_id][atn][arg] = entity.inventory._items[item_id]
          
          elif atn == nmmo.action.Buy and arg == nmmo.action.Item:
            item_id = entity_obs.market.ids[val]
            actions[entity_id][atn][arg] = self.realm.items[item_id]

          else:
            raise RuntimeError(f'Argument {arg} invalid for action {atn}')

    return processed_actions

  def _compute_observations(self):
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

    market = Item.Query.for_sale(self.realm.datastore)

    for agent in self.realm.players.values():
      agent_id = agent.id.val
      agent_r = agent.r.val
      agent_c = agent.c.val

      visible_entities = Entity.Query.window(
          self.realm.datastore,
          agent_r, agent_c,
          self.config.PLAYER_VISION_RADIUS
      )
      visible_tiles = Tile.Query.window(
          self.realm.datastore,
          agent_r, agent_c,
          self.config.PLAYER_VISION_RADIUS)

      inventory = Item.Query.owned_by(self.realm.datastore, agent_id)

      obs[agent_id] = Observation(
        self.config, agent_id, visible_tiles, visible_entities, inventory, market)

    return obs

  def _compute_rewards(self, agents: List[AgentID] = None):
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
      infos = {}
      rewards = {}

      for agent_id in agents:
        infos[agent_id] = {}
        agent = self.realm.players.get(agent_id)

        if agent is None:
          rewards[agent_id] = -1
          continue

        infos[agent_id] =  {'population': agent.population}

        if agent.diary is None:
          rewards[agent_id] = 0
          continue

        achievements = agent.diary.update(self.realm, agent)
        rewards[agent_id] = sum(achievements.values())
        infos[agent_id].update(achievements)

      return rewards, infos


  ############################################################################
  # PettingZoo API
  ############################################################################

  def render(self, mode='human'):
      '''For conformity with the PettingZoo API only; rendering is external'''

  @property
  def agents(self) -> List[AgentID]:
      '''For conformity with the PettingZoo API only; rendering is external'''
      return self.realm.players.keys()

  def close(self):
      '''For conformity with the PettingZoo API only; rendering is external'''

  metadata = {'render.modes': ['human'], 'name': 'neural-mmo'}
