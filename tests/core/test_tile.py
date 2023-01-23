import unittest
import nmmo
from nmmo.core.tile import Tile, TileState
from nmmo.lib.datastore.numpy_datastore import NumpyDatastore
from nmmo.lib import material

class MockRealm:
  def __init__(self):
    self.datastore = NumpyDatastore()
    self.datastore.register_object_type("Tile", TileState._num_attributes)
    self.config = nmmo.config.Small()

class MockEntity():
  def __init__(self, id):
    self.entID = id

class TestTile(unittest.TestCase):
  def test_tile(self):
    mock_realm = MockRealm()
    tile = Tile(mock_realm, 10, 20)
    
    tile.reset(material.Forest, nmmo.config.Small())

    self.assertEqual(tile.r.val, 10)
    self.assertEqual(tile.c.val, 20)
    self.assertEqual(tile.material_id.val, material.Forest.index)

    tile.addEnt(MockEntity(1))
    tile.addEnt(MockEntity(2))
    self.assertCountEqual(tile.entities.keys(), [1, 2])
    tile.delEnt(1)
    self.assertCountEqual(tile.entities.keys(), [2])

    tile.harvest(True)
    self.assertEqual(tile.depleted, True)
    self.assertEqual(tile.material_id.val, material.Scrub.index)

if __name__ == '__main__':
    unittest.main()