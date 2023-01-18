# unittests for tile.py

import unittest
import nmmo
from nmmo.core.tile import Tile
from nmmo.lib.datastore.numpy_datastore import NumpyDatastore
from nmmo.lib import material

class MockRealm:
  def __init__(self):
    self.datastore = NumpyDatastore()

class MockEntity():
  def __init__(self, id):
    self.entID = id

class TestTile(unittest.TestCase):
  def test_tile(self):
    mock_realm = MockRealm()
    tile = Tile(nmmo.config.Small(), mock_realm, 10, 20)
    
    tile.reset(material.Forest, nmmo.config.Small())

    self.assertEqual(tile.r.val, 10)
    self.assertEqual(tile.c.val, 20)
    self.assertEqual(tile.entity_id.val, 0)
    self.assertEqual(tile.material_id.val, material.Forest.index)

    tile.addEnt(MockEntity(1))
    self.assertEqual(tile.entity_id.val, 1)

    with self.assertRaises(AssertionError):
      tile.addEnt(MockEntity(2))
      
    tile.delEnt(1)
    self.assertEqual(tile.entity_id.val, 0)

    tile.harvest(True)
    self.assertEqual(tile.depleted, True)
    self.assertEqual(tile.material_id.val, material.Scrub.index)


if __name__ == '__main__':
    unittest.main()