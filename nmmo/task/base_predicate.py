import numpy as np

from nmmo.task.predicate import Predicate, Group
from nmmo.task.game_state import GameState
from nmmo.systems import skill as Skill
from nmmo.lib.material import Material
from nmmo.lib import utils

from nmmo.entity.entity import EntityState
from nmmo.core.tile import TileState

EntityAttr = EntityState.State.attr_name_to_col
TileAttr = TileState.State.attr_name_to_col


class TickGE(Predicate):
  # TickGE does not have subject
  # pylint: disable=super-init-not-called
  def __init__(self, num_tick: int):
    self._name = self._make_name(None, [num_tick])
    self._num_tick = num_tick

  def __call__(self, gs: GameState):
    """True if the current tick is greater than or equal to the specified num_tick.
       Otherwise false.
    """
    return gs.current_tick >= self._num_tick


class StayAlive(Predicate):
  def __call__(self, gs: GameState):
    """True if all subjects (self._agents) are alive.
       Otherwise false.
    """
    alive_subject = set(self.subject).intersection(gs.alive_agents)

    # if all specified agents are alive, the len(intersection) should be the same
    return len(alive_subject) == len(self.subject)


class AllDead(Predicate):
  def __call__(self, gs: GameState):
    """True if all subjects (self._agents) are dead.
       Otherwise false.
    """
    alive_subject = set(self.subject).intersection(gs.alive_agents)
    return len(alive_subject) == 0


class CanSeeTile(Predicate):
  def __init__(self, subject: Group, tile_type: Material):
    super().__init__(subject, tile_type)
    self._tile_type = tile_type.index

  def __call__(self, gs: GameState):
    """True if the self.tile_type is within the subjects' tile obs.
       Otherwise false.
    """
    result = False

    for ent_id in self.subject:
      if ent_id in gs.env_obs:
        tile_obs = gs.env_obs[ent_id].tiles[:, TileAttr['material_id']]
        if self._tile_type in tile_obs:
          result = True
          break

    return result


class CanSeeAgent(Predicate):
  def __init__(self, subject: Group, target: int):
    super().__init__(subject, target)
    self._target = target # ent_id

  def __call__(self, gs: GameState):
    """True if self.obj_agent is present in the subjects' entities obs.
       Otherwise false.
    """
    result = False

    for ent_id in self.subject:
      if ent_id in gs.env_obs:
        if self._target in gs.env_obs[ent_id].entities.ids:
          result = True
          break

    return result


class OccupyTile(Predicate):
  def __init__(self, subject: Group, row: int, col: int):
    super().__init__(subject, row, col)
    self._row = row
    self._col = col

    # TODO(kywch): this may need a count-down timer to support
    #   a game like: Hold the center for 100 ticks

  def __call__(self, gs: GameState):
    """True if any subject agent is on the desginated tile.
       Otherwise false.
    """
    sbj_data = gs.where_in_id('entity', self.subject)
    flt_row = sbj_data[:, EntityAttr['row']] == self._row
    flt_col = sbj_data[:, EntityAttr['col']] == self._col

    return np.any(flt_row & flt_col)


class DistanceTraveled(Predicate):
  def __init__(self, subject: Group, dist: int):
    super().__init__(subject, dist)
    self._dist = dist

  def __call__(self, gs: GameState):
    """True if the summed l-inf distance between each agent's current pos and spawn pos
        is greater than or equal to the specified _dist.
       Otherwise false.
    """
    sum_dist = 0
    sbj_data = gs.where_in_id('entity', self.subject)
    for i in range(sbj_data.shape[0]):
      mate = EntityState.parse_array(sbj_data[i])
      curr_pos = (mate.row, mate.col)
      sum_dist += utils.linf(curr_pos, gs.spawn_pos[mate.id])

    return sum_dist >= self._dist


class AllMembersWithinRange(Predicate):
  def __init__(self, subject: Group, dist: int):
    super().__init__(subject, dist)
    self._dist = dist

  def __call__(self, gs: GameState):
    """True if the max l-inf distance of teammates is 
         less than or equal to self.dist
       Otherwise false.
    """
    sbj_data = gs.where_in_id('entity', self.subject)
    rows = sbj_data[:, EntityAttr['row']]
    cols = sbj_data[:, EntityAttr['col']]

    # compare the outer most coordinates of all teammates
    return max(max(rows)-min(rows), max(cols)-min(cols)) <= self._dist


class AttainSkill(Predicate):
  def __init__(self, subject: Group, skill: Skill.Skill, level: int, num_agent: int):
    super().__init__(subject, skill, level, num_agent)
    self._skill = skill.__name__.lower()
    self._level = level
    self._num_agent = num_agent

  def __call__(self, gs: GameState):
    """True if the number of agents having self._skill level GE self._level
        is greather than or equal to self._num_agent
       Otherwise false.
    """
    # each row represents alive agents in the team
    sbj_data = gs.where_in_id('entity', self.subject)
    skill_level = sbj_data[:, EntityAttr[self._skill + '_level']]

    return sum(skill_level >= self._level) >= self._num_agent
