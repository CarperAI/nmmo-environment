from pdb import set_trace as T

from typing import List
import unittest
import lovely_numpy
lovely_numpy.set_config(repr=lovely_numpy.lovely)

import nmmo
from nmmo.entity.entity import Entity
from nmmo.core.realm import Realm
from nmmo.systems.item import Item


class TestApi(unittest.TestCase):
   env = nmmo.Env()
   config = env.config

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

      self.assertEqual(obs.keys(), self.env.realm.players.entities.keys())

      for step in range(10):
         entity_locations = [
             [ev.base.r.val, ev.base.c.val, e] for e, ev in self.env.realm.players.entities.items()
         ] + [
             [ev.base.r.val, ev.base.c.val, e] for e, ev in self.env.realm.npcs.entities.items()
         ]

         for player_id, player_obs in obs.items():
            self._validate_tiles(player_obs, self.env.realm)
            self._validate_entitites(
                player_id, player_obs, self.env.realm, entity_locations)
            self._validate_inventory(player_id, player_obs, self.env.realm)
            self._validate_market(player_obs, self.env.realm)
         obs, _, _, _ = self.env.step({})

   def _validate_tiles(self, obs, realm: Realm):
      for tile_obs in obs["Tile"]["Continuous"]:
         tile = realm.map.tiles[int(tile_obs[2]), int(tile_obs[3])]
         self.assertListEqual(list(tile_obs),
                              [tile.nEnts.val, tile.index.val, tile.r.val, tile.c.val])

   def _validate_entitites(self, player_id, obs, realm: Realm, entity_locations: List[List[int]]):
      observed_entities = set()

      for entity_obs in obs["Entity"]["Continuous"]:

         if entity_obs[0] == 0:
            continue
         entity: Entity = realm.entity(entity_obs[1])

         observed_entities.add(entity.entID)

         self.assertListEqual(list(entity_obs), [
             1,
             entity.entID,
             entity.attackerID.val,
             entity.base.level.val,
             entity.base.item_level.val,
             entity.base.comm.val,
             entity.base.population.val,
             entity.base.r.val,
             entity.base.c.val,
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
          realm.players[player_id].inventory._item_references,
          obs["Item"]["Continuous"]
      )

   def _validate_market(self, obs, realm: Realm):
      self._validate_items(
          realm.exchange.item_listings.values(),
          obs["Market"]["Continuous"]
      )

   def _validate_items(self, item_refs, item_obs):
      assert len(item_refs) == len(item_obs)
      for ob, item in zip(item_obs, item_refs):
         self.assertListEqual(list(ob), [
             item.instanceID,
             item.index.val,
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
         ], f"Mismatch for Item {item.instanceID}")


if __name__ == '__main__':
    unittest.main()
