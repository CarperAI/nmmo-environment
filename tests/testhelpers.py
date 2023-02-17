import logging
from copy import deepcopy
import numpy as np

import nmmo

from scripted import baselines
from nmmo.io.action import Move, Attack, Sell, Use, Give, Buy
from nmmo.entity.entity import EntityState
from nmmo.systems.item import ItemState

# this function can be replaced by assertDictEqual
# but might be still useful for debugging
def actions_are_equal(source_atn, target_atn, debug=True):

  # compare the numbers and player ids
  player_src = list(source_atn.keys())
  player_tgt = list(target_atn.keys())
  if player_src != player_tgt:
    if debug:
      logging.error("players don't match")
    return False

  # for each player, compare the actions
  for ent_id in player_src:
    atn1 = source_atn[ent_id]
    atn2 = target_atn[ent_id]

    if list(atn1.keys()) != list(atn2.keys()):
      if debug:
        logging.error("action keys don't match. player: %s", str(ent_id))
      return False

    for atn, args in atn1.items():
      if atn2[atn] != args:
        if debug:
          logging.error("action args don't match. player: %s, action: %s", str(ent_id), str(atn))
        return False

  return True


# this function CANNOT be replaced by assertDictEqual
def observations_are_equal(source_obs, target_obs, debug=True):

  keys_src = list(source_obs.keys())
  keys_obs = list(target_obs.keys())
  if keys_src != keys_obs:
    if debug:
      logging.error("entities don't match")
    return False

  for k in keys_src:
    ent_src = source_obs[k]
    ent_tgt = target_obs[k]
    if list(ent_src.keys()) != list(ent_tgt.keys()):
      if debug:
        logging.error("entries don't match. key: %s", str(k))
      return False

    obj = ent_src.keys()
    for o in obj:
      obj_src = ent_src[o]
      obj_tgt = ent_tgt[o]
      if np.sum(obj_src != obj_tgt) > 0:
        if debug:
          logging.error("objects don't match. key: %s, obj: %s", str(k), str(o))
        return False

  return True


def player_total(env):
  return sum(ent.gold.val for ent in env.realm.players.values())


def count_actions(tick, actions):
  cnt_action = {}
  for atn in (Move, Attack, Sell, Use, Give, Buy):
    cnt_action[atn] = 0

  for ent_id in actions:
    for atn, _ in actions[ent_id].items():
      if atn in cnt_action:
        cnt_action[atn] += 1
      else:
        cnt_action[atn] = 1

  info_str = f"Tick: {tick}, acting agents: {len(actions)}, action counts " + \
             f"move: {cnt_action[Move]}, attack: {cnt_action[Attack]}, " + \
             f"sell: {cnt_action[Sell]}, use: {cnt_action[Move]}, " + \
             f"give: {cnt_action[Give]}, buy: {cnt_action[Buy]}"
  logging.info(info_str)

  return cnt_action


class ScriptedAgentTestConfig(nmmo.config.Small, nmmo.config.AllGameSystems):

  __test__ = False

  LOG_ENV = True

  LOG_MILESTONES = True
  LOG_EVENTS = False
  LOG_VERBOSE = False

  SPECIALIZE = True
  PLAYERS = [
    baselines.Fisher, baselines.Herbalist,
    baselines.Prospector,baselines.Carver, baselines.Alchemist,
    baselines.Melee, baselines.Range, baselines.Mage]


# pylint: disable=abstract-method,duplicate-code
class ScriptedAgentTestEnv(nmmo.Env):
  '''
  EnvTest step() bypasses some differential treatments for scripted agents
  To do so, actions of scripted must be serialized using the serialize_actions function above
  '''
  __test__ = False

  def __init__(self, config: nmmo.config.Config, seed=None):
    super().__init__(config=config, seed=seed)

    # all agent must be scripted agents when using ScriptedAgentTestEnv
    for ent in self.realm.players.values():
      assert isinstance(ent.agent, baselines.Scripted), 'All agent must be scripted.'

    # this is to cache the actions generated by scripted policies
    self.actions = {}

  def reset(self, map_id=None, seed=None, options=None):
    self.actions = {}
    # manually resetting the EntityState, ItemState datastore tables
    EntityState.State.table(self.realm.datastore).reset()
    ItemState.State.table(self.realm.datastore).reset()
    return super().reset(map_id=map_id, seed=seed, options=options)

  def _compute_scripted_agent_actions(self, actions):
    # if actions are not provided, generate actions using the scripted policy
    if actions == {}:
      for eid, entity in self.realm.players.items():
        actions[eid] = entity.agent(self.obs[eid])

      # cache the actions for replay before deserialization
      self.actions = deepcopy(actions)

    # if actions are provided, just run ent.agent() to set the RNG to the same state
    else:
      # NOTE: This is a hack to set the random number generator to the same state
      # since scripted agents also use RNG. Without this, the RNG is in different state,
      # and the env.step() does not give the same results in the deterministic replay.
      for eid, ent in self.realm.players.items():
        ent.agent(self.obs[eid])

    return self._deserialize_scripted_actions(actions)

  def _process_actions(self, actions, obs):
    # TODO(kywch): Try to remove this override
    #   after rewriting _process_actions() using ActionTargets
    #   The output of scripted agents are somewhat different from
    #   what the current _process_actions() expects, so these need
    #   to be reconciled.

    # bypass the current _process_actions()
    return actions
