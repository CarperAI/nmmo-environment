#pylint: disable=invalid-name, unused-argument
import numpy as np
from numpy import count_nonzero as count

from nmmo.task.predicate import Predicate
from nmmo.task.predicate.core import predicate
from nmmo.task.group import Group
from nmmo.task.game_state import GameState
from nmmo.systems.skill import Skill
from nmmo.lib.material import Material
from nmmo.lib import utils

@predicate
def TickGE(gs: GameState,
           num_tick: int):
  """True if the current tick is greater than or equal to the specified num_tick.
  """
  return gs.current_tick >= num_tick

@predicate
def CanSeeTile(gs: GameState,
               subject: Group,
               tile_type: Material):
  return any(tile_type.index in t for t in subject.obs.tile.material_id)

@predicate
def StayAlive(gs: GameState,
              subject: Group):
  """True iff all subjects are alive.
  """
  return count(subject.health > 0) == len(subject)

@predicate
def AllDead(gs: GameState,
            subject: Group):
  """True iff all subjects are dead.
  """
  return count(subject.health) == 0

@predicate
def OccupyTile(gs: GameState,
               subject: Group,
               row: int,
               col: int):
  """True if any subject agent is on the desginated tile.
  """
  return np.any((subject.row == row) & (subject.col == col))

@predicate
def AllMembersWithinRange(gs: GameState,
                          subject: Group,
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

  def _evaluate(self, gs: GameState):
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

@predicate
def DistanceTraveled(gs: GameState,
                     subject: Group,
                     dist: int):
  """True if the summed l-inf distance between each agent's current pos and spawn pos
        is greater than or equal to the specified _dist.
  """
  r = subject.row
  c = subject.col
  dists = utils.linf(list(zip(r,c)),[gs.spawn_pos[id_] for id_ in subject.agents])
  return dists.sum() >= dist

@predicate
def AttainSkill(gs: GameState,
                subject: Group,
                skill: Skill,
                level: int,
                num_agent: int):
  """True if the number of agents having self._skill level GE self._level
        is greather than or equal to self._num_agent
  """
  skill_level = getattr(subject,skill.__name__.lower() + '_level')
  return sum(skill_level >= level) >= num_agent
