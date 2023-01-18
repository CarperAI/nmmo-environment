from functools import lru_cache
from nmmo.io.stimulus import Serialized
from nmmo.lib.datastore.datastore import ResultSet

class Observation:
  def __init__(self,
    config,
    agent_id: int,
    tiles: ResultSet, 
    entities: ResultSet,
    inventory: ResultSet,
    market: ResultSet) -> None:

    self.config = config
    self.agent_id = agent_id
    self.tiles = tiles
    self.entities = entities
    self.inventory = inventory
    self.market = market
  
  @lru_cache(maxsize=None)
  def tile(self, rDelta, cDelta):
    '''Return the array object corresponding to a nearby tile
    
    Args:
        rDelta: row offset from current agent
        cDelta: col offset from current agent

    Returns:
        Vector corresponding to the specified tile
    '''
    agent_c = self.agent().attribute(Serialized.Entity.C)
    agent_r = self.agent().attribute(Serialized.Entity.R)
    return self.tiles.where_eq(
      Serialized.Tile.C, agent_c + cDelta).where_eq(
      Serialized.Tile.R, agent_r + rDelta)

  @lru_cache(maxsize=None)
  def entity(self, entity_id):
    return self.entities.where_eq(Serialized.Entity.ID, entity_id)

  @lru_cache(maxsize=None)
  def agent(self):
    return self.entity(self.agent_id)

  def to_gym_obs(self):
    '''Convert the observation to a format that can be used by OpenAI Gym'''
    return {
      "Tile": {
        "Continuous": self.tiles.values[:,1:]
      },
      "Entity": {
        "Continuous": self.entities.values[:,1:]
      },
      "Item": {
        "Continuous": self.inventory.values[:,1:]
      },
      "Market": {
        "Continuous": self.market.values[:,1:]
      }
    }