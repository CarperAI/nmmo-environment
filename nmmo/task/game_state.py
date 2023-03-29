from __future__ import annotations
from typing import Dict, List, Tuple, MutableMapping, TYPE_CHECKING
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

if TYPE_CHECKING:
  from nmmo.task.predicate import Group

EntityAttr = EntityState.State.attr_name_to_col
ItemAttr = ItemState.State.attr_name_to_col
TileAttr = TileState.State.attr_name_to_col

@dataclass(frozen=True) # make gs read-only, except cache_result
class GameState:
  current_tick: int
  config: Config
  spawn_pos: Dict[int, Tuple[int, int]] # ent_id: (row, col) of all spawned agents

  alive_agents: List # of alive agents' ent_id (for convenience)
  env_obs: Dict[int, Observation] # env passes the obs of only alive agents

  entity_data: np.ndarray # a copied, whole Entity ds table
  item_data: np.ndarray # a copied, whole Item ds table

  cache_result: MutableMapping # cache for general memoization
  # add helper functions below
  def entity_or_none(self, ent_id):
    flt_ent = self.entity_data[:, EntityAttr['id']] == ent_id
    if np.any(flt_ent):
      return EntityAttr.parse_array(self.entity_data[flt_ent][0])

    return None

  def where_in_id(self, data_type, subject: List[int]):
    if data_type == 'entity':
      flt_idx = np.in1d(self.entity_data[:, EntityAttr['id']], subject)
      return self.entity_data[flt_idx]

    if data_type == 'item':
      flt_idx = np.in1d(self.item_data[:, ItemAttr['owner_id']], subject)
      return self.item_data[flt_idx]

    return None

  def group_by(self, flt_data, grpby_col, sum_col=0):
    # if sum_col = 0, this fn acts as COUNT, otherwise SUM
    g = npi.group_by(flt_data[:, grpby_col])
    result = {}
    for k, v in zip(*g(flt_data[:, sum_col])):
      if sum_col:
        result[k] = sum(v)
      else:
        result[k] = len(v)
    return result

  def get_subject_view(self, subject: Group):
    return GroupView(self, subject)

class GroupView:
  def __init__(self, gs: GameState, subject: Group):
    self._gs = gs
    self._subject = subject
    self._sbj_ent = gs.where_in_id('entity', subject)
    self._sbj_item = gs.where_in_id('item', subject)

  def __getattribute__(self, attr):
    if attr in ['_gs','_subject','_sbj_ent','_sbj_item']:
      return object.__getattribute__(self,attr)

    # Cached optimization
    k = (self._subject, attr)
    if k in self._gs.cache_result:
      return self._gs.cache_result[k]

    try:
      # Get property
      v = None
      if attr in EntityAttr.keys():
        v = self._sbj_ent[:, EntityAttr[attr]]
      elif attr in ItemAttr.keys():
        v = self._sbj_item[:, ItemAttr[attr]]
      else:
        v = object.__getattribute__(self, attr)
      self._gs.cache_result[k] = v
      return v
    except AttributeError:
      # View behavior
      return object.__getattribute__(self._gs,attr)

  @property
  def item_id(self):
    # id is a namespace clash between item and entity
    return self._sbj_ent[:, self._gs.item_cols['id']]

  # TODO(mark)
    # We can use this to lazily compute computationally intensive
    # Properties such as grouping information etc

class GameStateGenerator:
  def __init__(self, realm: Realm, config: Config):
    self.config = deepcopy(config)
    self.spawn_pos: Dict[int, Tuple[int, int]] = {}

    for ent_id, ent in realm.players.items():
      self.spawn_pos.update( {ent_id: ent.pos} )

  def generate(self, realm: Realm, env_obs: Dict[int, Observation]) -> GameState:
    # copy the datastore, by running astype
    entity_all = EntityState.Query.table(realm.datastore).astype(np.int16)

    return GameState(
      current_tick = realm.tick,
      config = self.config,
      spawn_pos = self.spawn_pos,
      alive_agents = list(entity_all[:, EntityAttr["id"]]),
      env_obs = env_obs,
      entity_data = entity_all,
      item_data = ItemState.Query.table(realm.datastore).astype(np.int16),
      cache_result = {}
    )
