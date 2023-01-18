from pdb import set_trace as T
from typing import List, Dict
import nmmo
from nmmo.core.observation import Observation
from nmmo.lib.datastore.numpy_datastore import NumpyDatastore
from nmmo.lib.datastore.datastore import ResultSet
import numpy as np
from nmmo.io.stimulus import Serialized

class NMMODatastore(NumpyDatastore):
  def __init__(self, config) -> None:
    super().__init__()
    self.config = config

    # Register all the objects defined in Serialized
    for (object_type,), entity in Serialized:
      if entity.enabled(config):
        self.register_object_type(object_type, [
          c for (c,), _ in entity])

    self._entity_location_cols = [
      self._tables["Entity"]._cols["R"],
      self._tables["Entity"]._cols["C"]]
    self._tile_location_cols = [
      self._tables["Tile"]._cols["R"],
      self._tables["Tile"]._cols["C"]]
    self._entity_id_col = self._tables["Entity"]._cols["ID"]
    self._item_owner_col = self._tables["Item"]._cols["Owner"]

  def create_object(self, serialized_type):
    o = super().create_object(serialized_type.__name__)
    # TODO: datastore object shouldn't need a reference to config
    o.config = self.config
    return o

  # xcxc clean up access to columns
  def observations(self, players: List) -> Dict[int, Observation]:
    obs = {}

    player_ids = [p.datastore_object.id for p in players]
    player_rows = self.table("Entity").get(player_ids)

    market = self.table("Item").where_eq(Serialized.Item.ForSale, 1)

    for player_row in player_rows.values:
      player_id = int(player_row[self._entity_id_col])

      visible_entities = self.table("Entity").window(
        *self._entity_location_cols, *player_row[self._entity_location_cols], self.config.PLAYER_VISION_RADIUS
      )
      visible_tiles = self.table("Tile").window(
        *self._tile_location_cols, *player_row[self._entity_location_cols], self.config.PLAYER_VISION_RADIUS
      )
      
      inventory = self.table("Item").where_eq(
        Serialized.Item.Owner.__name__, player_id)

      obs[player_id] = Observation(
        self.config, player_id,
        visible_tiles, visible_entities, inventory, market)

    return obs