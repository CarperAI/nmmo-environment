from pdb import set_trace as T

from typing import List
import unittest
from tqdm import tqdm
# import lovely_numpy
# lovely_numpy.set_config(repr=lovely_numpy.lovely)

import nmmo
from nmmo.core.observation import Observation
from nmmo.entity.entity import Entity
from nmmo.core.realm import Realm

from scripted import baselines

# 30 seems to be enough to test variety of agent actions
TEST_HORIZON = 30
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

  def test_observation_space(self):
    obs_space = self.env.observation_space(0)

    for entity in nmmo.Serialized.values():
        self.assertEqual(
            obs_space[entity.__name__]["Continuous"].shape[0], entity.N(self.config))

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
        [ev.base.r.val, ev.base.c.val, e] for e, ev in self.env.realm.players.entities.items()
      ] + [
        [ev.base.r.val, ev.base.c.val, e] for e, ev in self.env.realm.npcs.entities.items()
      ]

      for player_id, player_obs in obs.items():
        player_obs = player_obs.to_gym_obs()
        self._validate_tiles(player_obs, self.env.realm)
        self._validate_entitites(
            player_id, player_obs, self.env.realm, entity_locations)
        # self._validate_inventory(player_id, player_obs, self.env.realm)
        # xcxc fix market
        # self._validate_market(player_obs, self.env.realm)
      obs, _, _, _ = self.env.step({})

  def _validate_tiles(self, obs: Observation, realm: Realm):
    for tile_obs in obs["Tile"]["Continuous"]:
      tile = realm.map.tiles[(int(tile_obs[2]), int(tile_obs[3]))]
      self.assertListEqual(list(tile_obs),
                          [tile.num_entities.val, tile.index.val, tile.r.val, tile.c.val])

  def _validate_entitites(self, player_id, obs, realm: Realm, entity_locations: List[List[int]]):
    observed_entities = set()

    for entity_obs in obs["Entity"]["Continuous"]:
      entity: Entity = realm.entity(entity_obs[1])

      observed_entities.add(entity.entID)

      self.assertListEqual(list(entity_obs), [
        1,
        entity.entID,
        entity.attackerID.val,
        entity.level.val,
        entity.item_level.val,
        entity.comm.val,
        entity.population.val,
        entity.r.val,
        entity.c.val,
        entity.history.damage.val,
        entity.history.timeAlive.val,
        entity.status.freeze.val,
        entity.base.gold.val,
        entity.resources.health.val,
        entity.resources.food.val,
        entity.resources.water.val,
        entity.skills.melee.level.val,
        entity.skills.range.level.val,
        entity.skills.mage.level.val,
        (entity.skills.fishing.level.val if entity.isPlayer else 0),
        (entity.skills.herbalism.level.val if entity.isPlayer else 0),
        (entity.skills.prospecting.level.val if entity.isPlayer else 0),
        (entity.skills.carving.level.val if entity.isPlayer else 0),
        (entity.skills.alchemy.level.val if entity.isPlayer else 0),
    ], f"Mismatch for Entity {entity.entID}")

    # Make sure that we see entities IFF they are in our vision radius
    pr = realm.players.entities[player_id].base.r.val
    pc = realm.players.entities[player_id].base.c.val
    visible_entitites = set([e for r, c, e in entity_locations if
                              r >= pr - realm.config.PLAYER_VISION_RADIUS and
                              r <= pr + realm.config.PLAYER_VISION_RADIUS and
                              c >= pc - realm.config.PLAYER_VISION_RADIUS and
                              c <= pc + realm.config.PLAYER_VISION_RADIUS])
    self.assertSetEqual(visible_entitites, observed_entities,
                        f"Mismatch between observed: {observed_entities} and visible {visible_entitites} for {player_id}")

  def _validate_inventory(self, player_id, obs, realm: Realm):
    self._validate_items(
        realm.players[player_id].inventory._items,
        obs["Item"]["Continuous"]
    )

  def _validate_market(self, obs, realm: Realm):
    self._validate_items(
        [i for i,l in realm.exchange.item_listings.keys()],
        obs["Market"]["Continuous"]
    )

  def _validate_items(self, item_refs, item_obs):
    assert len(item_refs) == len(item_obs)
    for ob, item in zip(item_obs, item_refs):
        self.assertListEqual(list(ob), [
          item.datastore_object.id,
          item.item_type.val,
          item.level.val,
          item.capacity.val,
          item.quantity.val,
          item.tradable.val,
          item.melee_attack.val,
          item.range_attack.val,
          item.mage_attack.val,
          item.melee_defense.val,
          item.range_defense.val,
          item.mage_defense.val,
          item.health_restore.val,
          item.resource_restore.val,
          item.price.val,
          item.equipped.val,
          item.owner.val,
          item.for_sale.val,
        ], f"Mismatch for Item {item.datastore_object.id}")


if __name__ == '__main__':
  unittest.main()
