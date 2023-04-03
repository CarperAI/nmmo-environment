#pylint: disable=invalid-name
import numpy as np
from numpy import count_nonzero as count

from nmmo.task.predicate import Predicate
from nmmo.task.predicate.core import predicate
from nmmo.task.group import Group
from nmmo.task.game_state import GameState, TileAttr
from nmmo.systems import skill as Skill
from nmmo.lib.material import Material
from nmmo.lib import utils

class TickGE(Predicate):
  # TickGE does not have subject
  # pylint: disable=super-init-not-called
  def __init__(self, num_tick: int):
    super().__init__(num_tick)
    self._num_tick = num_tick

  def __call__(self, gs: GameState):
    """True if the current tick is greater than or equal to the specified num_tick.
       Otherwise false.
    """
    return gs.current_tick >= self._num_tick

class CanSeeTile(Predicate):
  def __init__(self, subject: Group, tile_type: Material):
    super().__init__(subject, tile_type)
    self.subject = subject
    self._tile_type = tile_type.index

  def __call__(self, gs: GameState):
    """True if the self.tile_type is within the subjects' tile obs.
       Otherwise false.
    """
    result = False

    for ent_id in self.subject.agents:
      if ent_id in gs.env_obs:
        tile_obs = gs.env_obs[ent_id].tiles[:, TileAttr['material_id']]
        if self._tile_type in tile_obs:
          result = True
          break

    return result

@predicate
def StayAlive(subject: Group):
  """True iff all subjects are alive.
  """
  return count(subject.health > 0) == len(subject)

@predicate
def AllDead(subject: Group):
  """True iff all subjects are dead.
  """
  return count(subject.health) == 0

@predicate
def OccupyTile(subject: Group,
               row: int,
               col: int):
  """True if any subject agent is on the desginated tile.
  """
  return np.any((subject.row == row) & (subject.col == col))

@predicate
def AllMembersWithinRange(subject: Group,
                          dist: int):
  """True if the max l-inf distance of teammates is 
         less than or equal to self.dist
  """
  return max(subject.row.max()-subject.row.min(),
      subject.col.max()-subject.col.min()) <= dist

class CanSeeAgent(Predicate):
  def __init__(self, subject: Group, target: int):
    super().__init__(subject, target)
    self.subject = subject
    self._target = target # ent_id

  def __call__(self, gs: GameState):
    """True if self.obj_agent is present in the subjects' entities obs.
       Otherwise false.
    """
    result = False

    for ent_id in self.subject.agents:
      if ent_id in gs.env_obs:
        if self._target in gs.env_obs[ent_id].entities.ids:
          result = True
          break

    return result


class DistanceTraveled(Predicate):
  def __init__(self, subject: Group, dist: int):
    super().__init__(subject, dist)
    self.subject = subject
    self._dist = dist

  def __call__(self, gs: GameState):
    """True if the summed l-inf distance between each agent's current pos and spawn pos
        is greater than or equal to the specified _dist.
       Otherwise false.
    """
    sd = gs.get_subject_view(self.subject)
    r = sd.row
    c = sd.col
    dists = utils.linf(list(zip(r,c)),[gs.spawn_pos[id_] for id_ in sd.id])
    return dists.sum() >= self._dist

class AttainSkill(Predicate):
  def __init__(self, subject: Group, skill: Skill.Skill, level: int, num_agent: int):
    super().__init__(subject, skill, level, num_agent)
    self.subject = subject
    self._skill = skill.__name__.lower()
    self._level = level
    self._num_agent = num_agent

  def __call__(self, gs: GameState):
    """True if the number of agents having self._skill level GE self._level
        is greather than or equal to self._num_agent
       Otherwise false.
    """
    # each row represents alive agents in the team
    sd = gs.get_subject_view(self.subject)
    skill_level = sd.__getattribute__(self._skill + '_level')

    return sum(skill_level >= self._level) >= self._num_agent
