from pdb import set_trace as T
from typing import List
import nmmo
from nmmo.lib.datastore.numpy_datastore import NumpyDatastore
import numpy as np


class NMMODatastore(NumpyDatastore):
  def __init__(self, config) -> None:
    super().__init__()
    self.config = config
    for (object_type,), entity in nmmo.io.stimulus.Serialized:
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
    self._item_for_sale_col = self._tables["Item"]._cols["ForSale"]

  def create_object(self, serialized_type):
    o = super().create_object(serialized_type.__name__)
    # TODO: datastore object shouldn't need a reference to config
    o.config = self.config
    return o

  def dataframe(self, players: List):
    obs = {}

    player_ids = [p.datastore_object.id for p in players]
    player_rows = self.get("Entity", player_ids)

    market_rows = self._tables["Item"].where_eq(self._item_for_sale_col, 1)

    for player_row in player_rows:
      player_id = int(player_row[self._entity_id_col])

      visible_entities = self._tables["Entity"].window(
        *self._entity_location_cols, *player_row[self._entity_location_cols], self.config.PLAYER_VISION_RADIUS
      )
      visible_tiles = self._tables["Tile"].window(
        *self._tile_location_cols, *player_row[self._entity_location_cols], self.config.PLAYER_VISION_RADIUS
      )
      
      inventory = self._tables["Item"].where_eq(self._item_owner_col, player_id)

      obs[player_id] = {
        "Entity": {
          "Continuous": visible_entities
        },
        "Tile": {
          "Continuous": visible_tiles
        },
        "Item": {
          "Continuous": inventory
        },
        "Market": {
          "Continuous": market_rows
        }
      }

    return obs