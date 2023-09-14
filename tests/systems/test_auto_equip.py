# pylint: disable=protected-access, no-member
import unittest

import nmmo
import nmmo.systems.item as Item


class TestAutoEquip(unittest.TestCase):
  def test_auto_equip(self):
    config = nmmo.config.Default()
    config.PLAYERS = [nmmo.Agent]
    config.EQUIPMENT_AUTO_UPGRADE_EQUIPPED_ITEM = [Item.Hat.ITEM_TYPE_ID]
    env = nmmo.Env(config)
    env.reset()

    ent_id = 1
    agent = env.realm.players[ent_id]
    agent.skills.melee.level.update(2)

    # provide hat and top
    hat1 = Item.Hat(env.realm, level=1)
    agent.inventory.receive(hat1)
    top1 = Item.Top(env.realm, level=1)
    agent.inventory.receive(top1)

    env.obs = env._compute_observations()

    # equip both items
    env.step({ent_id: {nmmo.action.Use: {nmmo.action.InventoryItem: 0}}})
    env.step({ent_id: {nmmo.action.Use: {nmmo.action.InventoryItem: 1}}})

    # check if the items are equipped
    self.assertEqual(hat1.equipped.val, 1)
    self.assertEqual(top1.equipped.val, 1)

    # provide level 2 hat and top
    hat2 = Item.Hat(env.realm, level=2)
    agent.inventory.receive(hat2)
    top2 = Item.Top(env.realm, level=2)
    agent.inventory.receive(top2)

    # hat should be auto equipped, top should not
    self.assertEqual(hat1.equipped.val, 0)
    self.assertEqual(hat2.equipped.val, 1)
    self.assertEqual(top1.equipped.val, 1)
    self.assertEqual(top2.equipped.val, 0)

if __name__ == '__main__':
  unittest.main()
