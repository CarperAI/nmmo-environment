from functools import lru_cache
from types import SimpleNamespace
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
    self.tiles = tiles

    self.entities = SimpleNamespace(
      values = entities,
      ids = entities[:,EntityState._attr_name_to_col["id"]])

    self.inventory = SimpleNamespace(
      values = inventory,
      ids = inventory[:,ItemState._attr_name_to_col["id"]])

    self.market = SimpleNamespace(
      values = market,
      ids = market[:,ItemState._attr_name_to_col["id"]])

  @lru_cache(maxsize=None)
  def tile(self, rDelta, cDelta):
    '''Return the array object corresponding to a nearby tile
    
    Args:
        rDelta: row offset from current agent
        cDelta: col offset from current agent

    Returns:
        Vector corresponding to the specified tile
    '''
    agent = self.agent()
    r_cond = (self.tiles[:,TileState._attr_name_to_col["r"]] == agent.r + rDelta)
    c_cond = (self.tiles[:,TileState._attr_name_to_col["c"]] == agent.c + cDelta)
    return TileState.parse_array(self.tiles[r_cond & c_cond][0])

  @lru_cache(maxsize=None)
  def entity(self, entity_id):
    rows = self.entities.values[self.entities.ids == entity_id]
    if rows.size == 0:
      return None
    return EntityState.parse_array(rows[0])

  @lru_cache(maxsize=None)
  def agent(self):
    return self.entity(self.agent_id)

  def to_gym(self):
    '''Convert the observation to a format that can be used by OpenAI Gym'''
    return {
      "Tile": self.tiles,
      "Entity": self.entities.values,
      "Inventory": self.inventory.values,
      "Market": self.market.values,
    }