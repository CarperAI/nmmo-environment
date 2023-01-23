# Unittest for entity.py

import unittest
import nmmo
from nmmo.entity import Entity
from nmmo.entity.entity import EntityState
from nmmo.lib.datastore.numpy_datastore import NumpyDatastore
import numpy as np

class MockRealm:
  def __init__(self):
    self.config = nmmo.config.Default()
    self.config.PLAYERS = range(100)
    self.datastore = NumpyDatastore()
    self.datastore.register_object_type("Entity", EntityState._num_cols)
class TestEntity(unittest.TestCase):
  def test_entity(self):
    realm = MockRealm()
    entity_id = 123
    population_id = 11
    entity = Entity(realm, (10,20), entity_id, "name", "color", population_id)

    self.assertEqual(entity.id.val, entity_id)
    self.assertEqual(entity.r.val, 10)
    self.assertEqual(entity.c.val, 20)
    self.assertEqual(entity.population_id.val, population_id)
    self.assertEqual(entity.damage.val, 0)
    self.assertEqual(entity.time_alive.val, 0)
    self.assertEqual(entity.freeze.val, 0)
    self.assertEqual(entity.item_level.val, 0)
    self.assertEqual(entity.attacker_id.val, 0)
    self.assertEqual(entity.message.val, 0)
    self.assertEqual(entity.gold.val, 0)
    self.assertEqual(entity.health.val, realm.config.PLAYER_BASE_HEALTH)
    self.assertEqual(entity.food.val, realm.config.RESOURCE_BASE)
    self.assertEqual(entity.water.val, realm.config.RESOURCE_BASE)
    self.assertEqual(entity.melee_level.val, 0)
    self.assertEqual(entity.range_level.val, 0)
    self.assertEqual(entity.mage_level.val, 0)
    self.assertEqual(entity.fishing_level.val, 0)
    self.assertEqual(entity.herbalism_level.val, 0)
    self.assertEqual(entity.prospecting_level.val, 0)
    self.assertEqual(entity.carving_level.val, 0)
    self.assertEqual(entity.alchemy_level.val, 0)

  def test_query_by_ids(self):
    realm = MockRealm()
    entity_id = 123
    population_id = 11
    entity = Entity(realm, (10,20), entity_id, "name", "color", population_id)

    entities = EntityState.Query.by_ids(realm.datastore, [entity_id])
    self.assertEqual(len(entities), 1)
    self.assertEqual(entities[0][Entity._attr_name_to_col["id"]], entity_id)
    self.assertEqual(entities[0][Entity._attr_name_to_col["r"]], 10)
    self.assertEqual(entities[0][Entity._attr_name_to_col["c"]], 20)
    
    entity.food.update(11)
    e_row = EntityState.Query.by_id(realm.datastore, entity_id)
    self.assertEqual(e_row[Entity._attr_name_to_col["food"]], 11)


if __name__ == '__main__':
  unittest.main()
