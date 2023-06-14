import logging
import unittest

from copy import deepcopy
from timeit import timeit
import numpy as np

import nmmo
from nmmo.core import action
from nmmo.systems import item as Item
from nmmo.core.realm import Realm

from scripted import baselines

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

      # ActionTargets causes a problem here, so skip it
      if o == "ActionTargets":
        continue

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
  for atn in (action.Move, action.Attack, action.Sell, action.Use, action.Give, action.Buy):
    cnt_action[atn] = 0

  for ent_id in actions:
    for atn, _ in actions[ent_id].items():
      if atn in cnt_action:
        cnt_action[atn] += 1
      else:
        cnt_action[atn] = 1

  info_str = f"Tick: {tick}, acting agents: {len(actions)}, action counts " + \
             f"move: {cnt_action[action.Move]}, attack: {cnt_action[action.Attack]}, " + \
             f"sell: {cnt_action[action.Sell]}, use: {cnt_action[action.Move]}, " + \
             f"give: {cnt_action[action.Give]}, buy: {cnt_action[action.Buy]}"
  logging.info(info_str)

  return cnt_action


class ScriptedAgentTestConfig(nmmo.config.Small, nmmo.config.AllGameSystems):

  __test__ = False

  LOG_ENV = True

  LOG_MILESTONES = True
  LOG_EVENTS = False
  LOG_VERBOSE = False

  PLAYER_DEATH_FOG = 5

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
    return super().reset(map_id=map_id, seed=seed, options=options)

  def _compute_scripted_agent_actions(self, actions):
    assert actions is not None, "actions must be provided, even it's {}"
    # if actions are not provided, generate actions using the scripted policy
    if actions == {}:
      for eid, ent in self.realm.players.items():
        actions[eid] = ent.agent(self.obs[eid])

      # cache the actions for replay before deserialization
      self.actions = deepcopy(actions)

    # if actions are provided, just run ent.agent() to set the RNG to the same state
    else:
      # NOTE: This is a hack to set the random number generator to the same state
      # since scripted agents also use RNG. Without this, the RNG is in different state,
      # and the env.step() does not give the same results in the deterministic replay.
      for eid, ent in self.realm.players.items():
        ent.agent(self.obs[eid])

    return actions


def change_spawn_pos(realm: Realm, ent_id: int, new_pos):
  # check if the position is valid
  assert realm.map.tiles[new_pos].habitable, "Given pos is not habitable."
  assert realm.entity(ent_id), "No such entity in the realm"

  entity = realm.entity(ent_id)
  old_pos = entity.pos
  realm.map.tiles[old_pos].remove_entity(ent_id)

  # set to new pos
  entity.row.update(new_pos[0])
  entity.col.update(new_pos[1])
  entity.spawn_pos = new_pos
  realm.map.tiles[new_pos].add_entity(entity)

def provide_item(realm: Realm, ent_id: int,
                 item: Item.Item, level: int, quantity: int):
  for _ in range(quantity):
    realm.players[ent_id].inventory.receive(
      item(realm, level=level))


# pylint: disable=invalid-name,protected-access
class ScriptedTestTemplate(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    # only use Combat agents
    cls.config = ScriptedAgentTestConfig()
    cls.config.PROVIDE_ACTION_TARGETS = True

    cls.config.PLAYERS = [baselines.Melee, baselines.Range, baselines.Mage]
    cls.config.PLAYER_N = 3
    #cls.config.IMMORTAL = True

    # set up agents to test ammo use
    cls.policy = { 1:'Melee', 2:'Range', 3:'Mage' }
    # 1 cannot hit 3, 2 can hit 1, 3 cannot hit 2
    cls.spawn_locs = { 1:(17, 17), 2:(17, 19), 3:(21, 21) }
    cls.ammo = { 1:Item.Whetstone, 2:Item.Arrow, 3:Item.Runes }
    cls.ammo_quantity = 2

    # items to provide
    cls.init_gold = 5
    cls.item_level = [0, 3] # 0 can be used, 3 cannot be used
    cls.item_sig = {}

  def _make_item_sig(self):
    item_sig = {}
    for ent_id, ammo in self.ammo.items():
      item_sig[ent_id] = []
      for item in [ammo, Item.Top, Item.Gloves, Item.Ration, Item.Potion]:
        for lvl in self.item_level:
          item_sig[ent_id].append((item, lvl))

    return item_sig

  def _setup_env(self, random_seed, check_assert=True):
    """ set up a new env and perform initial checks """
    env = ScriptedAgentTestEnv(self.config, seed=random_seed)
    env.reset()

    # provide money for all
    for ent_id in env.realm.players:
      env.realm.players[ent_id].gold.update(self.init_gold)

    # provide items that are in item_sig
    self.item_sig = self._make_item_sig()
    for ent_id, items in self.item_sig.items():
      for item_sig in items:
        if item_sig[0] == self.ammo[ent_id]:
          provide_item(env.realm, ent_id, item_sig[0], item_sig[1], self.ammo_quantity)
        else:
          provide_item(env.realm, ent_id, item_sig[0], item_sig[1], 1)

    # teleport the players, if provided with specific locations
    for ent_id, pos in self.spawn_locs.items():
      change_spawn_pos(env.realm, ent_id, pos)

    env.obs = env._compute_observations()

    if check_assert:
      self._check_default_asserts(env)

    return env

  def _check_ent_mask(self, ent_obs, atn, target_id):
    assert atn in [action.Give, action.GiveGold], "Invalid action"
    gym_obs = ent_obs.to_gym()
    mask = gym_obs['ActionTargets'][atn][action.Target][:ent_obs.entities.len] > 0

    return target_id in ent_obs.entities.ids[mask]

  def _check_inv_mask(self, ent_obs, atn, item_sig):
    assert atn in [action.Destroy, action.Give, action.Sell, action.Use], "Invalid action"
    gym_obs = ent_obs.to_gym()
    mask = gym_obs['ActionTargets'][atn][action.InventoryItem][:ent_obs.inventory.len] > 0
    inv_idx = ent_obs.inventory.sig(*item_sig)

    return ent_obs.inventory.id(inv_idx) in ent_obs.inventory.ids[mask]

  def _check_mkt_mask(self, ent_obs, item_id):
    gym_obs = ent_obs.to_gym()
    mask = gym_obs['ActionTargets'][action.Buy][action.MarketItem][:ent_obs.market.len] > 0

    return item_id in ent_obs.market.ids[mask]

  def _check_default_asserts(self, env):
    """ The below asserts are based on the hardcoded values in setUpClass()
        This should not run when different values were used
    """
    # check if the agents are in specified positions
    for ent_id, pos in self.spawn_locs.items():
      self.assertEqual(env.realm.players[ent_id].pos, pos)

    for ent_id, sig_list in self.item_sig.items():
      # ammo instances are in the datastore and global item registry (realm)
      inventory = env.obs[ent_id].inventory
      self.assertTrue(inventory.len == len(sig_list))
      for inv_idx in range(inventory.len):
        item_id = inventory.id(inv_idx)
        self.assertTrue(Item.ItemState.Query.by_id(env.realm.datastore, item_id) is not None)
        self.assertTrue(item_id in env.realm.items)

      for lvl in self.item_level:
        inv_idx = inventory.sig(self.ammo[ent_id], lvl)
        self.assertTrue(inv_idx is not None)
        self.assertEqual(self.ammo_quantity, # provided 2 ammos
          Item.ItemState.parse_array(inventory.values[inv_idx]).quantity)

      # check ActionTargets
      ent_obs = env.obs[ent_id]

      if env.config.ITEM_SYSTEM_ENABLED:
        # USE InventoryItem mask
        for item_sig in sig_list:
          if item_sig[1] == 0:
            # items that can be used
            self.assertTrue(self._check_inv_mask(ent_obs, action.Use, item_sig))
          else:
            # items that are too high to use
            self.assertFalse(self._check_inv_mask(ent_obs, action.Use, item_sig))

      if env.config.EXCHANGE_SYSTEM_ENABLED:
        # SELL InventoryItem mask
        for item_sig in sig_list:
          # the agent can sell anything now
          self.assertTrue(self._check_inv_mask(ent_obs, action.Sell, item_sig))

        # BUY MarketItem mask -- there is nothing on the market, so mask should be all 0
        self.assertTrue(len(env.obs[ent_id].market.ids) == 0)

  def _check_assert_make_action(self, env, atn, test_cond):
    assert atn in [action.Give, action.GiveGold, action.Buy], "Invalid action"
    actions = {}
    for ent_id, cond in test_cond.items():
      ent_obs = env.obs[ent_id]

      if atn in [action.Give, action.GiveGold]:
        # self should be always masked
        self.assertFalse(self._check_ent_mask(ent_obs, atn, ent_id))

        # check if the target is masked as expected
        self.assertEqual(
          cond['ent_mask'],
          self._check_ent_mask(ent_obs, atn, cond['tgt_id']),
          f"ent_id: {ent_id}, atn: {ent_id}, tgt_id: {cond['tgt_id']}"
        )

      if atn in [action.Give]:
        self.assertEqual(
          cond['inv_mask'],
          self._check_inv_mask(ent_obs, atn, cond['item_sig']),
          f"ent_id: {ent_id}, atn: {ent_id}, tgt_id: {cond['item_sig']}"
        )

      if atn in [action.Buy]:
        self.assertEqual(
          cond['mkt_mask'],
          self._check_mkt_mask(ent_obs, cond['item_id']),
          f"ent_id: {ent_id}, atn: {ent_id}, tgt_id: {cond['item_id']}"
        )

      # append the actions
      if atn == action.Give:
        actions[ent_id] = { action.Give: {
          action.InventoryItem: env.obs[ent_id].inventory.sig(*cond['item_sig']),
          action.Target: cond['tgt_id'] } }

      elif atn == action.GiveGold:
        actions[ent_id] = { action.GiveGold:
          { action.Target: cond['tgt_id'], action.Price: cond['gold'] } }

      elif atn == action.Buy:
        mkt_idx = ent_obs.market.index(cond['item_id'])
        actions[ent_id] = { action.Buy: { action.MarketItem: mkt_idx } }

    return actions

# pylint: disable=unnecessary-lambda,bad-builtin
def profile_env_step(action_target=True, tasks=None, condition=None):
  config = nmmo.config.Default()
  config.PLAYERS = [baselines.Sleeper] # the scripted agents doing nothing
  config.IMMORTAL = True # otherwise the agents will die
  config.PROVIDE_ACTION_TARGETS = action_target
  env = nmmo.Env(config)
  if tasks is None:
    tasks = []
  env.reset(seed=0, make_task_fn=lambda: tasks)
  for _ in range(3):
    env.step({})

  obs = env._compute_observations()

  test_func = [
    ('env.step({}):', lambda: env.step({})),
    ('env.realm.step():', lambda: env.realm.step({})),
    ('env._compute_observations():', lambda: env._compute_observations()),
    ('obs.to_gym(), ActionTarget:', lambda: {a: o.to_gym() for a,o in obs.items()}),
    ('env._compute_rewards():', lambda: env._compute_rewards())
  ]

  if condition:
    print('=== Test condition:', condition, '===')
  for name, func in test_func:
    print(' -', name, timeit(func, number=100, globals=globals()))
