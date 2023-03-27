from typing import Dict, List, Tuple
from dataclasses import dataclass
from copy import deepcopy

import numpy as np
import numpy_indexed as npi

from nmmo.core.config import Config
from nmmo.core.realm import Realm
from nmmo.core.observation import Observation

from nmmo.entity.entity import EntityState
from nmmo.systems.item import ItemState
from nmmo.core.tile import TileState


@dataclass
class GameState:
  tick: int
  config: Config
  spawn_pos: Dict[int, Tuple[int, int]] # ent_id: (row, col)

  alive_agents: List # of alive agents' ent_id
  env_obs: Dict[int, Observation] # this should include only alive agents

  entity_cols: Dict # attr_to_col
  entity_data: np.ndarray # a copied, whole Entity ds table

  item_cols: Dict # attr_to_col
  item_data: np.ndarray # a copied, whole Item ds table

  tile_cols: Dict

  cache_result: Dict # cache for result of Predicate results

  # add extra info that is not in the datastore (e.g., spawn pos)
  # add helper functions below

  def entity_or_none(self, ent_id):
    flt_ent = self.entity_data[:,self.entity_cols['id']] == ent_id
    if np.any(flt_ent):
      return EntityState.parse_array(self.entity_data[flt_ent][0])

    return None

  def where_in_id(self, data_type, subject: List[int]):
    if data_type == 'entity':
      flt_idx = np.in1d(self.entity_data[:,self.entity_cols['id']], subject)
      return self.entity_data[flt_idx]

    elif data_type == 'item':
      flt_idx = np.in1d(self.item_data[:,self.item_cols['owner_id']], subject)
      return self.item_data[flt_idx]

    else:
      return None

  def group_by(self, flt_data, grpby_col, sum_col=0):
    # if sum_col = 0, this fn acts as COUNT, otherwise SUM
    g = npi.group_by(flt_data[:,grpby_col])
    result = {}
    for k, v in zip(*g(flt_data[:,sum_col])):
      if sum_col:
        result[k] = sum(v)
      else:
        result[k] = len(v)
    return result


class GameStateGenerator:
  def __init__(self, realm: Realm, config: Config):
    self.config = deepcopy(config)
    self.spawn_pos: Dict[int, Tuple[int, int]] = {}

    for ent_id, ent in realm.players.items():
      self.spawn_pos.update( {ent_id: ent.pos} )

  def generate(self, realm: Realm, env_obs: Dict[int, Observation]) -> GameState:
    # copy the datastore, by running astype
    entity_all = EntityState.Query.table(realm.datastore).astype(np.int16)
    ent_cols = deepcopy(EntityState.State.attr_name_to_col)

    return GameState(
      tick = deepcopy(realm.tick),
      config = deepcopy(self.config),
      spawn_pos = deepcopy(self.spawn_pos),
      alive_agents = list(entity_all[:,ent_cols["id"]]),
      env_obs = deepcopy(env_obs),
      entity_cols = ent_cols,
      entity_data = entity_all,
      item_cols = deepcopy(ItemState.State.attr_name_to_col),
      item_data = ItemState.Query.table(realm.datastore).astype(np.int16),
      tile_cols = deepcopy(TileState.State.attr_name_to_col),
      cache_result = {}
    )
