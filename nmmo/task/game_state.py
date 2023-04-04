from __future__ import annotations
from typing import Dict, List, Tuple, MutableMapping
from dataclasses import dataclass
from copy import deepcopy

import numpy as np

from nmmo.core.config import Config
from nmmo.core.realm import Realm
from nmmo.core.observation import Observation
from nmmo.task.group import Group

from nmmo.entity.entity import EntityState
from nmmo.systems.item import ItemState
from nmmo.core.tile import TileState

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

  def get_subject_view(self, subject: Group):
    return GroupView(self, subject)

class ArrayView:
  def __init__(self,
               name: str,
               gs: GameState,
               subject: Group,
               arr: np.ndarray):
    assert name in ['item','tile']
    self._name = name
    self._mapping = None
    if name == 'item':
      self._mapping = ItemAttr
    elif name == 'tile':
      self._mapping = TileAttr
    self._gs = gs
    self._subject = subject
    self._arr = arr

  def __getattr__(self, attr) -> np.ndarray:
    k = (self._subject, self._name+'_'+attr)
    if not k in self._gs.cache_result:
      self._gs.cache_result[k] = self._arr[:, self._mapping[attr]]
    return self._gs.cache_result[k]

class GroupObsView:
  def __init__(self, gs: GameState, subject: Group):
    self._gs = gs

    valid_agents = filter(lambda eid: eid in gs.env_obs,subject.agents)
    self._obs = [gs.env_obs[ent_id] for ent_id in valid_agents]
    self._subject = subject

    #tiles = np.array([])
    #if len(self._obs) > 0:
    #  print([o.tiles.shape for o in self._obs])
    #  tiles = np.stack([o.tiles for o in self._obs])
    #self.tile = ArrayView('tile', gs, subject, tiles)

class GroupView:
  def __init__(self, gs: GameState, subject: Group):
    self._gs = gs
    self._subject = subject
    self._sbj_ent = gs.where_in_id('entity', subject.agents)
    self._sbj_item = gs.where_in_id('item', subject.agents)

    self.item = ArrayView('item', gs, subject, self._sbj_item)
    self.obs = GroupObsView(gs, subject)

  def __getattribute__(self, attr):
    if attr in ['_gs','_subject','_sbj_ent','_sbj_item', 'item', 'obs']:
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
      else:
        v = object.__getattribute__(self, attr)
      self._gs.cache_result[k] = v
      return v
    except AttributeError:
      # View behavior
      return object.__getattribute__(self._gs,attr)


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
