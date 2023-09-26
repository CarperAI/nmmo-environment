import unittest

import copy
import nmmo
from scripted.baselines import Sleeper

HORIZON = 32


class TestTileProperty(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.config = nmmo.config.Default()
    cls.config.PLAYERS = [Sleeper]
    # so that fish and herb are not depleted
    cls.config.PROFESSION_FISH_RESPAWN = 1
    cls.config.PROFESSION_HERB_RESPAWN = 1
    env = nmmo.Env(cls.config)
    env.reset()
    cls.start = copy.deepcopy(env.realm)
    for _ in range(HORIZON):
      env.step({})
    cls.end = copy.deepcopy(env.realm)

  # Test immutable invariants assumed for certain optimizations
  def test_fixed_habitability_passability(self):
    # Used in optimization with habitability lookup table
    start_habitable = [tile.habitable for tile in self.start.map.tiles.flatten()]
    end_habitable = [tile.habitable for tile in self.end.map.tiles.flatten()]
    self.assertListEqual(start_habitable, end_habitable)

    # Used in optimization that caches the result of A*
    start_passable = [tile.impassible for tile in self.start.map.tiles.flatten()]
    end_passable = [tile.impassible for tile in self.end.map.tiles.flatten()]
    self.assertListEqual(start_passable, end_passable)

  def test_consumables_disable_config(self):
    # The default is PROFESSION_DISABLE_CONSUMABLES = False
    map_size = self.config.MAP_SIZE
    for r in range(map_size):
      for c in range(map_size):
        tile = self.end.map.tiles[r, c]
        # check the end state of these tiles
        if tile.material.tex in ["herb", "fish"]:
          self.assertFalse(tile.depleted)
          self.assertNotEqual(tile.material.respawn, 0)

    # With PROFESSION_DISABLE_CONSUMABLES = True,
    # the initial state of fish and herb tiles is deplete and respawn = 0
    self.config.PROFESSION_DISABLE_CONSUMABLES = True
    env = nmmo.Env(self.config)
    env.reset()
    for _ in range(HORIZON):
      env.step({})

    for r in range(map_size):
      for c in range(map_size):
        tile = env.realm.map.tiles[r, c]
        # check the end state of these tiles
        if tile.material.tex in ["herb", "fish"]:
          self.assertTrue(tile.depleted)
          self.assertEqual(tile.material.respawn, 0)
          self.assertNotEqual(tile.state.index, tile.material.index)

if __name__ == '__main__':
  unittest.main()
