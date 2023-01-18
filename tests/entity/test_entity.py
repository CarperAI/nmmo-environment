# Unittest for entity.py

import unittest
import nmmo
from nmmo.entity import Entity
from nmmo.lib.datastore.numpy_datastore import NumpyDatastore

class MockRealm:
  def __init__(self):
    self.datastore = NumpyDatastore()
    self.config = nmmo.config.Default()
    self.config.PLAYERS = range(100)

class TestEntity(unittest.TestCase):
  def test_entity(self):
    mock_realm = MockRealm()
    config = mock_realm.config
    entity_id = 123
    population_id = 11
    entity = Entity(mock_realm, (10,20), entity_id, "name", "color", population_id)

    self.assertEqual(entity.id.val, entity_id)
    self.assertEqual(entity.r.val, 10)
    self.assertEqual(entity.c.val, 20)
    self.assertEqual(entity.population_id.val, population_id)
    self.assertEqual(entity.level.val, 3)
    self.assertEqual(entity.damage.val, 0)
    self.assertEqual(entity.time_alive.val, 0)
    self.assertEqual(entity.freeze.val, 0)
    self.assertEqual(entity.item_level.val, 0)
    self.assertEqual(entity.attacker_id.val, 0)
    self.assertEqual(entity.message.val, 0)
    self.assertEqual(entity.gold.val, 0)
    self.assertEqual(entity.health.val, config.PLAYER_BASE_HEALTH)
    self.assertEqual(entity.food.val, config.RESOURCE_BASE)
    self.assertEqual(entity.water.val, config.RESOURCE_BASE)
    self.assertEqual(entity.melee_level.val, 0)
    self.assertEqual(entity.range_level.val, 0)
    self.assertEqual(entity.mage_level.val, 0)
    self.assertEqual(entity.fishing_level.val, 0)
    self.assertEqual(entity.herbalism_level.val, 0)
    self.assertEqual(entity.prospecting_level.val, 0)
    self.assertEqual(entity.carving_level.val, 0)
    self.assertEqual(entity.alchemy_level.val, 0)

if __name__ == '__main__':
  unittest.main()
