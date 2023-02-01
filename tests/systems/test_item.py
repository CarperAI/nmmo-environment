import unittest
import nmmo
from nmmo.lib.datastore.numpy_datastore import NumpyDatastore
from nmmo.systems.item import Hat, ItemState
import numpy as np

class MockRealm:
  def __init__(self):
    self.config = nmmo.config.Default()
    self.datastore = NumpyDatastore()
    self.items = {}
    self.datastore.register_object_type("Item", ItemState.State.num_attributes)

class TestItem(unittest.TestCase):
  def test_item(self):
    realm = MockRealm()

    hat_1 = Hat(realm, 1)
    self.assertEqual(hat_1.type_id.val, Hat.ITEM_TYPE_ID)
    self.assertEqual(hat_1.level.val, 1)
    self.assertEqual(hat_1.mage_defense.val, 10)

    hat_2 = Hat(realm, 10)
    self.assertEqual(hat_2.level.val, 10)
    self.assertEqual(hat_2.melee_defense.val, 100)

    self.assertDictEqual(realm.items, {hat_1.id.val: hat_1, hat_2.id.val: hat_2})

  def test_owned_by(self):
    realm = MockRealm()

    hat_1 = Hat(realm, 1)
    hat_2 = Hat(realm, 10)

    hat_1.owner_id.update(1)
    hat_2.owner_id.update(1)

    np.testing.assert_array_equal(
      ItemState.Query.owned_by(realm.datastore, 1)[:,0], 
      [hat_1.id.val, hat_2.id.val])

    self.assertEqual(Hat.Query.owned_by(realm.datastore, 2).size, 0)

if __name__ == '__main__':
    unittest.main()