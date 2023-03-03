import unittest
import logging

# pylint: disable=import-error
from testhelpers import ScriptedTestTemplate

from nmmo.io import action
from nmmo.systems import item as Item
from nmmo.systems.item import ItemState

RANDOM_SEED = 284

LOGFILE = 'tests/action/test_ammo_use.log'

class TestAmmoUse(ScriptedTestTemplate):
  @classmethod
  def setUpClass(cls):
    super().setUpClass()

    # config specific to the tests here
    cls.config.IMMORTAL = True
    cls.config.LOG_VERBOSE = False
    if cls.config.LOG_VERBOSE:
      logging.basicConfig(filename=LOGFILE, level=logging.INFO)

  def test_ammo_fire_all(self):
    env = self._setup_env(random_seed=RANDOM_SEED)

    # First tick actions: USE (equip) level-0 ammo
    env.step({ ent_id: { action.Use: 
        { action.InventoryItem: env.obs[ent_id].inventory.sig(self.ammo[ent_id], 0) }
      } for ent_id in self.ammo })

    # check if the agents have equipped the ammo
    for ent_id in self.ammo:
      gym_obs = env.obs[ent_id].to_gym()
      inventory = env.obs[ent_id].inventory
      inv_idx = inventory.sig(self.ammo[ent_id], 0)
      self.assertEqual(1, # True
        ItemState.parse_array(inventory.values[inv_idx]).equipped)

      # check SELL InventoryItem mask -- one cannot sell equipped item
      mask = gym_obs['ActionTargets'][action.Sell][action.InventoryItem][:inventory.len] > 0
      self.assertTrue(inventory.id(inv_idx) not in inventory.ids[mask])

    # Second tick actions: ATTACK other agents using ammo
    #  NOTE that the agents are immortal
    #  NOTE that agents 1 & 3's attack are invalid due to out-of-range
    env.step({ ent_id: { action.Attack: 
        { action.Style: env.realm.players[ent_id].agent.style[0],
          action.Target: (ent_id+1)%3+1 } }
        for ent_id in self.ammo })

    # check if the ammos were consumed
    ammo_ids = []
    for ent_id in self.ammo:
      inventory = env.obs[ent_id].inventory
      inv_idx = inventory.sig(self.ammo[ent_id], 0)
      item_info = ItemState.parse_array(inventory.values[inv_idx])
      if ent_id == 2:
        # only agent 2's attack is valid and consume ammo
        self.assertEqual(self.ammo_quantity - 1, item_info.quantity)
        ammo_ids.append(inventory.id(inv_idx))
      else:
        self.assertEqual(self.ammo_quantity, item_info.quantity)

    # Third tick actions: ATTACK again to use up all the ammo, except agent 3
    #  NOTE that agent 3's attack command is invalid due to out-of-range
    env.step({ ent_id: { action.Attack: 
        { action.Style: env.realm.players[ent_id].agent.style[0],
          action.Target: (ent_id+1)%3+1 } }
        for ent_id in self.ammo })

    # check if the ammos are depleted and the ammo slot is empty
    ent_id = 2
    self.assertTrue(env.obs[ent_id].inventory.len == len(self.item_sig[ent_id]) - 1)
    self.assertTrue(env.realm.players[ent_id].inventory.equipment.ammunition.item == None)

    for item_id in ammo_ids:
      self.assertTrue(len(ItemState.Query.by_id(env.realm.datastore, item_id)) == 0)
      self.assertTrue(item_id not in env.realm.items)

    # invalid attacks
    for ent_id in [1, 3]:
      # agent 3 gathered shaving, so the item count increased
      #self.assertTrue(env.obs[ent_id].inventory.len == len(self.item_sig[ent_id]))
      self.assertTrue(env.realm.players[ent_id].inventory.equipment.ammunition.item is not None)

    # DONE

  def test_cannot_use_listed_items(self):
    env = self._setup_env(random_seed=RANDOM_SEED)

    sell_price = 1

    # provide extra scrap to range to make its inventory full
    # but level-0 scrap overlaps with the listed item
    ent_id = 2
    self._provide_item(env.realm, ent_id, Item.Scrap, level=0, quantity=3)
    self._provide_item(env.realm, ent_id, Item.Scrap, level=1, quantity=3)

    # provide extra scrap to mage to make its inventory full
    # there will be no overlapping item
    ent_id = 3
    self._provide_item(env.realm, ent_id, Item.Scrap, level=5, quantity=3)
    self._provide_item(env.realm, ent_id, Item.Scrap, level=7, quantity=3)
    env.obs = env._compute_observations()

    # First tick actions: SELL level-0 ammo
    env.step({ ent_id: { action.Sell: 
        { action.InventoryItem: env.obs[ent_id].inventory.sig(self.ammo[ent_id], 0),
          action.Price: sell_price } }
        for ent_id in self.ammo })

    # check if the ammos were listed
    for ent_id in self.ammo:
      gym_obs = env.obs[ent_id].to_gym()
      inventory = env.obs[ent_id].inventory
      inv_idx = inventory.sig(self.ammo[ent_id], 0)
      item_info = ItemState.parse_array(inventory.values[inv_idx])
      # ItemState data
      self.assertEqual(sell_price, item_info.listed_price)
      # Exchange listing
      self.assertTrue(item_info.id in env.realm.exchange._item_listings)
      self.assertTrue(item_info.id in env.obs[ent_id].market.ids)

      # check SELL InventoryItem mask -- one cannot sell listed item
      mask = gym_obs['ActionTargets'][action.Sell][action.InventoryItem][:inventory.len] > 0
      self.assertTrue(inventory.id(inv_idx) not in inventory.ids[mask])

      # check USE InventoryItem mask -- one cannot use listed item
      mask = gym_obs['ActionTargets'][action.Use][action.InventoryItem][:inventory.len] > 0
      self.assertTrue(inventory.id(inv_idx) not in inventory.ids[mask])

      # check BUY MarketItem mask -- there should be two ammo items in the market
      mask = gym_obs['ActionTargets'][action.Buy][action.MarketItem][:inventory.len] > 0
      # agent 1 has inventory space
      if ent_id == 1: self.assertTrue(sum(mask) == 2)
      # agent 2's inventory is full but can buy level-0 scrap (existing ammo)
      if ent_id == 2: self.assertTrue(sum(mask) == 1)
      # agent 3's inventory is full without overlapping ammo
      if ent_id == 3: self.assertTrue(sum(mask) == 0)

    # Second tick actions: USE ammo, which should NOT happen
    env.step({ ent_id: { action.Use: 
        { action.InventoryItem: env.obs[ent_id].inventory.sig(self.ammo[ent_id], 0) }
      } for ent_id in self.ammo })

    # check if the agents have equipped the ammo
    for ent_id in self.ammo:
      inventory = env.obs[ent_id].inventory
      inv_idx = inventory.sig(self.ammo[ent_id], 0)
      self.assertEqual(0, # False
        ItemState.parse_array(inventory.values[inv_idx]).equipped)

    # DONE

  def test_receive_extra_ammo_swap(self):
    env = self._setup_env(random_seed=RANDOM_SEED)

    extra_ammo = 500
    scrap_lvl0 = (Item.Scrap, 0)
    scrap_lvl1 = (Item.Scrap, 1)
    scrap_lvl3 = (Item.Scrap, 3)
    sig_int_tuple = lambda sig: (sig[0].ITEM_TYPE_ID, sig[1])

    for ent_id in self.policy:
      # provide extra scrap 
      self._provide_item(env.realm, ent_id, Item.Scrap, level=0, quantity=extra_ammo)
      self._provide_item(env.realm, ent_id, Item.Scrap, level=1, quantity=extra_ammo)

    # level up the agent 1 (Melee) to 2
    env.realm.players[1].skills.melee.level.update(2)
    env.obs = env._compute_observations()

    # check inventory
    for ent_id in self.ammo:
      # realm data
      inv_realm = { item.signature: item.quantity.val
                    for item in env.realm.players[ent_id].inventory.items
                    if isinstance(item, Item.Stack) }
      self.assertTrue( sig_int_tuple(scrap_lvl0) in inv_realm )
      self.assertTrue( sig_int_tuple(scrap_lvl1) in inv_realm )
      self.assertEqual( inv_realm[sig_int_tuple(scrap_lvl1)], extra_ammo )

      # item datastore
      inv_obs = env.obs[ent_id].inventory
      self.assertTrue(inv_obs.sig(*scrap_lvl0) is not None)
      self.assertTrue(inv_obs.sig(*scrap_lvl1) is not None)
      self.assertEqual( extra_ammo,
        ItemState.parse_array(inv_obs.values[inv_obs.sig(*scrap_lvl1)]).quantity)
      if ent_id == 1:
        # if the ammo has the same signature, the quantity is added to the existing stack
        self.assertEqual( inv_realm[sig_int_tuple(scrap_lvl0)], extra_ammo + self.ammo_quantity )
        self.assertEqual( extra_ammo + self.ammo_quantity,
          ItemState.parse_array(inv_obs.values[inv_obs.sig(*scrap_lvl0)]).quantity)
        # so there should be 1 more space
        self.assertEqual( inv_obs.len, self.config.ITEM_INVENTORY_CAPACITY - 1)

      else:
        # if the signature is different, it occupies a new inventory space
        self.assertEqual( inv_realm[sig_int_tuple(scrap_lvl0)], extra_ammo )
        self.assertEqual( extra_ammo,
          ItemState.parse_array(inv_obs.values[inv_obs.sig(*scrap_lvl0)]).quantity)
        # thus the inventory is full
        self.assertEqual( inv_obs.len, self.config.ITEM_INVENTORY_CAPACITY)

      if ent_id == 1:
        gym_obs = env.obs[ent_id].to_gym()
        # check USE InventoryItem mask
        mask = gym_obs['ActionTargets'][action.Use][action.InventoryItem][:inv_obs.len] > 0
        # level-2 melee should be able to use level-0, level-1 scrap but not level-3
        self.assertTrue(inv_obs.id(inv_obs.sig(*scrap_lvl0)) in inv_obs.ids[mask])
        self.assertTrue(inv_obs.id(inv_obs.sig(*scrap_lvl1)) in inv_obs.ids[mask])
        self.assertTrue(inv_obs.id(inv_obs.sig(*scrap_lvl3)) not in inv_obs.ids[mask])

    # First tick actions: USE (equip) level-0 ammo
    #   execute only the agent 1's action
    ent_id = 1
    env.step({ ent_id: { action.Use: 
        { action.InventoryItem: env.obs[ent_id].inventory.sig(*scrap_lvl0) } }})

    # check if the agents have equipped the ammo 0
    inv_obs = env.obs[ent_id].inventory
    self.assertTrue(ItemState.parse_array(inv_obs.values[inv_obs.sig(*scrap_lvl0)]).equipped == 1)
    self.assertTrue(ItemState.parse_array(inv_obs.values[inv_obs.sig(*scrap_lvl1)]).equipped == 0)
    self.assertTrue(ItemState.parse_array(inv_obs.values[inv_obs.sig(*scrap_lvl3)]).equipped == 0)

    # Second tick actions: USE (equip) level-1 ammo
    #   this should unequip level-0 then equip level-1 ammo
    env.step({ ent_id: { action.Use: 
        { action.InventoryItem: env.obs[ent_id].inventory.sig(*scrap_lvl1) } }})

    # check if the agents have equipped the ammo 1
    inv_obs = env.obs[ent_id].inventory
    self.assertTrue(ItemState.parse_array(inv_obs.values[inv_obs.sig(*scrap_lvl0)]).equipped == 0)
    self.assertTrue(ItemState.parse_array(inv_obs.values[inv_obs.sig(*scrap_lvl1)]).equipped == 1)
    self.assertTrue(ItemState.parse_array(inv_obs.values[inv_obs.sig(*scrap_lvl3)]).equipped == 0)

    # Third tick actions: USE (equip) level-3 ammo
    #   this should ignore USE action and leave level-1 ammo equipped
    env.step({ ent_id: { action.Use: 
        { action.InventoryItem: env.obs[ent_id].inventory.sig(*scrap_lvl3) } }})

    # check if the agents have equipped the ammo 1
    inv_obs = env.obs[ent_id].inventory
    self.assertTrue(ItemState.parse_array(inv_obs.values[inv_obs.sig(*scrap_lvl0)]).equipped == 0)
    self.assertTrue(ItemState.parse_array(inv_obs.values[inv_obs.sig(*scrap_lvl1)]).equipped == 1)
    self.assertTrue(ItemState.parse_array(inv_obs.values[inv_obs.sig(*scrap_lvl3)]).equipped == 0)

    # DONE

  def test_use_ration_poultice(self):
    # cannot use level-3 ration & poultice due to low level
    # can use level-0 ration & poultice to increase food/water/health
    env = self._setup_env(random_seed=RANDOM_SEED)

    # make food/water/health 20
    res_dec_tick = env.config.RESOURCE_DEPLETION_RATE
    init_res = 20
    for ent_id in self.policy:
      env.realm.players[ent_id].resources.food.update(init_res)
      env.realm.players[ent_id].resources.water.update(init_res)
      env.realm.players[ent_id].resources.health.update(init_res)
    env.obs = env._compute_observations()

    """First tick: try to use level-3 ration & poultice"""
    ration_lvl3 = (Item.Ration, 3)
    poultice_lvl3 = (Item.Poultice, 3)
    
    actions = {}
    ent_id = 1; actions[ent_id] = { action.Use:
      { action.InventoryItem: env.obs[ent_id].inventory.sig(*ration_lvl3) } }
    ent_id = 2; actions[ent_id] = { action.Use:
      { action.InventoryItem: env.obs[ent_id].inventory.sig(*ration_lvl3) } }
    ent_id = 3; actions[ent_id] = { action.Use:
      { action.InventoryItem: env.obs[ent_id].inventory.sig(*poultice_lvl3) } }

    env.step(actions)

    # check if the agents have used the ration & poultice
    for ent_id in [1, 2]:
      # cannot use due to low level, so still in the inventory
      self.assertFalse( env.obs[ent_id].inventory.sig(*ration_lvl3) is None)

      # failed to restore food/water, so no change
      resources = env.realm.players[ent_id].resources
      self.assertEqual( resources.food.val, init_res - res_dec_tick)
      self.assertEqual( resources.water.val, init_res - res_dec_tick)
    
    ent_id = 3 # failed to use the item
    self.assertFalse( env.obs[ent_id].inventory.sig(*poultice_lvl3) is None)
    self.assertEqual( env.realm.players[ent_id].resources.health.val, init_res)

    """Second tick: try to use level-0 ration & poultice"""
    ration_lvl0 = (Item.Ration, 0)
    poultice_lvl0 = (Item.Poultice, 0)
    
    actions = {}
    ent_id = 1; actions[ent_id] = { action.Use:
      { action.InventoryItem: env.obs[ent_id].inventory.sig(*ration_lvl0) } }
    ent_id = 2; actions[ent_id] = { action.Use:
      { action.InventoryItem: env.obs[ent_id].inventory.sig(*ration_lvl0) } }
    ent_id = 3; actions[ent_id] = { action.Use:
      { action.InventoryItem: env.obs[ent_id].inventory.sig(*poultice_lvl0) } }

    env.step(actions)

    # check if the agents have successfully used the ration & poultice
    restore = env.config.PROFESSION_CONSUMABLE_RESTORE(0)
    for ent_id in [1, 2]:
      # items should be gone
      self.assertTrue( env.obs[ent_id].inventory.sig(*ration_lvl0) is None)

      # successfully restored food/water
      resources = env.realm.players[ent_id].resources
      self.assertEqual( resources.food.val, init_res + restore - 2*res_dec_tick)
      self.assertEqual( resources.water.val, init_res + restore - 2*res_dec_tick)
    
    ent_id = 3 # successfully restored health
    self.assertTrue( env.obs[ent_id].inventory.sig(*poultice_lvl0) is None) # item gone
    self.assertEqual( env.realm.players[ent_id].resources.health.val, init_res + restore)

    # DONE


if __name__ == '__main__':
  unittest.main()
