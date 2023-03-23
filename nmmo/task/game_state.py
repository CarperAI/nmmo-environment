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
class TeamGameState:
  tick: int
  config: Config
  pop_id: int
  spawn_pos: Dict[int, Tuple[int, int]] # ent_id: (row, col)

  alive_agents: List # of alive agents' ent_id
  alive_byteam: Dict # all alive agents' ent_id and pop_id

  env_obs: Dict[int, Observation] # only include obs from own team

  entity_cols: Dict # attr2col
  entity_data: np.ndarray # Entity ds table, has only team members

  item_cols: Dict
  item_data: np.ndarray # Item ds table, has only team members

  tile_cols: Dict

  cache_result: Dict # cache for result of team task evaluation

  # add extra info that is not in the datastore (e.g., spawn pos)
  # add helper functions below

  def is_member(self, ent_id):
    return ent_id in self.spawn_pos

  def entity_or_none(self, ent_id):
    flt_ent = self.entity_data[:,self.entity_cols['id']] == ent_id
    if np.any(flt_ent):
      return EntityState.parse_array(self.entity_data[flt_ent][0])

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
    self.ent_to_team: Dict[int, int] = {} # key: ent_id, val: pop_id
    # key: pop_id, val: spawn_pos dict -- ent_id: (row, col)
    self.team_to_ent: Dict[int, Dict[int, Tuple[int, int]]] = {}

    # TODO(kywch): get the ent_to_group mapping from Team/GroupEnv
    for ent_id, ent in realm.players.items():
      self.ent_to_team[ent_id] = ent.population
      if ent.population in self.team_to_ent:
        # since this is __init__, ent.pos is the spawn pos
        self.team_to_ent[ent.population].update({ent_id: ent.pos})
      else:
        self.team_to_ent[ent.population] = {ent_id: ent.pos}

  def generate(self, realm: Realm, env_obs: Dict[int, Observation]) -> Dict[int, TeamGameState]:
    team_gs = {}

    # get all alive entities
    entity_all = EntityState.Query.table(realm.datastore).astype(np.int32)
    ent_cols = EntityState.State.attr_name_to_col

    # CHECK_ME: Entity ds should have the latest alive agents info
    alive_byteam = {}
    alive_agents = list(entity_all[:,ent_cols["id"]])
    g = npi.group_by(entity_all[:,ent_cols["population_id"]])
    for pop_id, ents in zip(*g(entity_all[:,ent_cols["id"]])):
      alive_byteam[int(pop_id)] = ents

    item_all = ItemState.Query.table(realm.datastore).astype(np.int32)
    item_cols = ItemState.State.attr_name_to_col

    tile_cols = TileState.State.attr_name_to_col

    # CHECK ME: what gets return for eliminated teams? killed agents?
    for pop_id, spawn_pos in self.team_to_ent.items():
      flt_ent = entity_all[:,ent_cols['population_id']] == pop_id
      flt_item = np.isin(item_all[:,item_cols['owner_id']], list(spawn_pos.keys()))

      team_gs[pop_id] = TeamGameState(
        tick = realm.tick,
        config = self.config,
        pop_id = int(pop_id),
        spawn_pos = spawn_pos,
        alive_agents = alive_agents,
        alive_byteam = alive_byteam,
        env_obs = { ent_id: env_obs[ent_id]
                    for ent_id in spawn_pos.keys() if ent_id in env_obs },
        entity_cols = ent_cols,
        entity_data = entity_all[flt_ent],
        item_cols = item_cols,
        item_data = item_all[flt_item],
        tile_cols = tile_cols,
        cache_result = {}
      )

    return team_gs
