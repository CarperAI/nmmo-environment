from pdb import set_trace as T

from typing import List
import unittest
from tqdm import tqdm

import nmmo
from nmmo.core.observation import Observation
from nmmo.core.tile import TileState
from nmmo.entity.entity import Entity, EntityState
from nmmo.core.realm import Realm
from nmmo.systems.item import ItemState

from scripted import baselines

# 30 seems to be enough to test variety of agent actions
TEST_HORIZON = 1024
RANDOM_SEED = 342

class Config(nmmo.config.Small, nmmo.config.AllGameSystems):
  RENDER = False
  SPECIALIZE = True
  PLAYERS = [
    baselines.Fisher, baselines.Herbalist, baselines.Prospector, baselines.Carver, baselines.Alchemist,
    baselines.Melee, baselines.Range, baselines.Mage]

class TestApi(unittest.TestCase):
  @classmethod 
  def setUpClass(cls):
    cls.config = Config()
    cls.env = nmmo.Env(cls.config, RANDOM_SEED)

  def test_action_space(self):
    action_space = self.env.action_space(0)
    self.assertSetEqual(
        set(action_space.keys()),
        set(nmmo.Action.edges(self.config)))

  def test_observations(self):
    obs = self.env.reset()

    self.assertEqual(obs.keys(), self.env.realm.players.keys())

    for _ in tqdm(range(TEST_HORIZON)):
      entity_locations = [
        [ev.r.val, ev.c.val, e] for e, ev in self.env.realm.players.entities.items()
      ] + [
        [ev.r.val, ev.c.val, e] for e, ev in self.env.realm.npcs.entities.items()
      ]

      for player_id, player_obs in obs.items():
        self._validate_tiles(player_obs, self.env.realm)
        self._validate_entitites(
            player_id, player_obs, self.env.realm, entity_locations)
        self._validate_inventory(player_id, player_obs, self.env.realm)
        self._validate_market(player_obs, self.env.realm)
      obs, _, _, _ = self.env.step({})

  def _validate_tiles(self, obs, realm: Realm):
    for tile_obs in obs["Tile"]:
      tile_obs = TileState.parse_array(tile_obs)
      tile = realm.map.tiles[(int(tile_obs.r), int(tile_obs.c))]
      for k,v in tile_obs.__dict__.items():
        if v != getattr(tile, k).val:
          self.assertEqual(v, getattr(tile, k).val, 
            f"Mismatch for {k} in tile {tile_obs.r}, {tile_obs.c}")

  def _validate_entitites(self, player_id, obs, realm: Realm, entity_locations: List[List[int]]):
    observed_entities = set()

    for entity_obs in obs["Entity"]:
      entity_obs = EntityState.parse_array(entity_obs)
      entity: Entity = realm.entity(entity_obs.id)

      observed_entities.add(entity.entID)

      for k,v in entity_obs.__dict__.items():
        if getattr(entity, k) is None:
          raise ValueError(f"Entity {entity} has no attribute {k}")
        self.assertEqual(v, getattr(entity, k).val,
          f"Mismatch for {k} in entity {entity_obs.id}")

    # Make sure that we see entities IFF they are in our vision radius
    pr = realm.players.entities[player_id].r.val
    pc = realm.players.entities[player_id].c.val
    visible_entitites = set([e for r, c, e in entity_locations if
                              r >= pr - realm.config.PLAYER_VISION_RADIUS and
                              r <= pr + realm.config.PLAYER_VISION_RADIUS and
                              c >= pc - realm.config.PLAYER_VISION_RADIUS and
                              c <= pc + realm.config.PLAYER_VISION_RADIUS])
    self.assertSetEqual(visible_entitites, observed_entities,
      f"Mismatch between observed: {observed_entities} and visible {visible_entitites} for {player_id}")

  def _validate_inventory(self, player_id, obs, realm: Realm):
    self._validate_items(
        {i.id.val: i for i in realm.players[player_id].inventory._items},
        obs["Inventory"]
    )

  def _validate_market(self, obs, realm: Realm):
    self._validate_items(
        {i.item.id.val: i.item for i in realm.exchange._item_listings.values()},
        obs["Market"]
    )

  def _validate_items(self, items_dict, item_obs):
    assert len(items_dict) == len(item_obs)
    for ob in item_obs:
      item_ob = ItemState.parse_array(ob)
      item = items_dict[item_ob.id]
      for k,v in item_ob.__dict__.items():
        self.assertEqual(v, getattr(item, k).val,
          f"Mismatch for {k} in item {item_ob.id}: {v} != {getattr(item, k).val}")

if __name__ == '__main__':
  unittest.main()
