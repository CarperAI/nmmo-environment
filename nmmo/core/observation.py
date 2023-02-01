from functools import lru_cache
from types import SimpleNamespace

import numpy as np

from nmmo.core.tile import TileState
from nmmo.entity.entity import EntityState
from nmmo.systems.item import ItemState


class Observation:
  def __init__(self,
    config,
    agent_id: int,
    tiles,
    entities,
    inventory,
    market) -> None:

    self.config = config
    self.agent_id = agent_id

    self.tiles = tiles[0:config.MAP_N_OBS]

    entities = entities[0:config.PLAYER_N_OBS]
    self.entities = SimpleNamespace(
        values = entities,
        ids = entities[:,EntityState.State.attr_name_to_col["id"]])

    if config.ITEM_SYSTEM_ENABLED:
      inventory = inventory[0:config.ITEM_N_OBS]
      self.inventory = SimpleNamespace(
        values = inventory,
        ids = inventory[:,ItemState.State.attr_name_to_col["id"]])
    else:
      assert inventory.size == 0

    if config.EXCHANGE_SYSTEM_ENABLED:
      market = market[0:config.EXCHANGE_N_OBS]
      self.market = SimpleNamespace(
        values = market,
        ids = market[:,ItemState.State.attr_name_to_col["id"]])
    else:
      assert market.size == 0

  # pylint: disable=method-cache-max-size-none
  @lru_cache(maxsize=None)
  def tile(self, r_delta, c_delta):
    '''Return the array object corresponding to a nearby tile

    Args:
        r_delta: row offset from current agent
        c_delta: col offset from current agent

    Returns:
        Vector corresponding to the specified tile
    '''
    agent = self.agent()
    r_cond = (self.tiles[:,TileState.State.attr_name_to_col["row"]] == agent.row + r_delta)
    c_cond = (self.tiles[:,TileState.State.attr_name_to_col["col"]] == agent.col + c_delta)
    return TileState.parse_array(self.tiles[r_cond & c_cond][0])

  # pylint: disable=method-cache-max-size-none
  @lru_cache(maxsize=None)
  def entity(self, entity_id):
    rows = self.entities.values[self.entities.ids == entity_id]
    if rows.size == 0:
      return None
    return EntityState.parse_array(rows[0])

  # pylint: disable=method-cache-max-size-none
  @lru_cache(maxsize=None)
  def agent(self):
    return self.entity(self.agent_id)

  def to_gym(self):
    '''Convert the observation to a format that can be used by OpenAI Gym'''

    gym_obs = {
      "Tile": np.vstack([
        self.tiles,
        np.zeros((self.config.MAP_N_OBS - self.tiles.shape[0], self.tiles.shape[1]))
      ]),
      "Entity": np.vstack([
        self.entities.values, np.zeros((
          self.config.PLAYER_N_OBS - self.entities.values.shape[0],
          self.entities.values.shape[1]))
      ]),
    }

    if self.config.ITEM_SYSTEM_ENABLED:
      gym_obs["Inventory"] = np.vstack([
        self.inventory.values, np.zeros((
          self.config.ITEM_N_OBS - self.inventory.values.shape[0],
          self.inventory.values.shape[1]))
      ])

    if self.config.EXCHANGE_SYSTEM_ENABLED:
      gym_obs["Market"] = np.vstack([
        self.market.values, np.zeros((
          self.config.EXCHANGE_N_OBS - self.market.values.shape[0],
          self.market.values.shape[1]))
      ])

    return gym_obs
