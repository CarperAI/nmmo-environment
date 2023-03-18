# pylint: disable=unnecessary-pass
from typing import List

from nmmo.task.task import PredicateTask
from nmmo.systems import skill as Skill
from nmmo.lib.material import Material


class Timer(PredicateTask):
  def __init__(self, num_tick: int):
    super().__init__(num_tick)
    self.num_tick = num_tick

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


# CHECK ME: maybe this should be the default task?
class LiveLong(Timer):
  def __call__(self, team_gs, ent_id):
    """True if the health of agent (ent_id) is greater than 0.
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    agent = team_gs.entity_or_none(ent_id)
    if agent:
      return agent.time_alive >= self.num_tick

    return False


# each agent is rewarded if the alive teammate is greater than min_size
class TeamSizeGE(PredicateTask): # greater than or equal to
  def __init__(self, num_agent: int):
    super().__init__(num_agent)
    self.num_agent = num_agent

  def __call__(self, team_gs, ent_id):
    """True if the number of alive teammates is greater than or equal to min_size.
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    if team_gs.pop_id in team_gs.alive_all:
      return len(team_gs.alive_all[team_gs.pop_id]) >= self.num_agent

    return False


class ProtectAgent(PredicateTask):
  def __init__(self, agents: List[int]):
    super().__init__(agents)
    self.agents = agents

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class SearchTile(PredicateTask):
  def __init__(self, tile_type: Material):
    super().__init__(tile_type)
    self.tile_type = tile_type

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class TeamSearchTile(SearchTile):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class SearchAgent(PredicateTask):
  def __init__(self, obj_agent: int):
    super().__init__(obj_agent)
    self.obj_agent = obj_agent

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class TeamSearchAgent(SearchAgent):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class GotoTile(PredicateTask):
  def __init__(self, row: int, col: int):
    super().__init__(row, col)
    self.coord = (row, col)

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class TeamOccupyTile(GotoTile):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class Travel(PredicateTask):
  def __init__(self, dist: int):
    super().__init__(dist)
    self.dist = dist

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class TeamTravel(Travel):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class StayCloseTo(PredicateTask):
  def __init__(self, obj_agent:int, dist: int):
    super().__init__(obj_agent, dist)
    self.obj_agent = obj_agent
    self.dist = dist

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class TeamStayClose(PredicateTask):
  def __init__(self, dist: int):
    super().__init__(dist)
    self.dist = dist

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class AttainSkill(PredicateTask):
  def __init__(self, skill: Skill.Skill, level: int):
    super().__init__(skill, level)
    self.skill = skill
    self.level = level

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class TeamAttainSkill(PredicateTask):
  def __init__(self, skill: Skill.Skill, level: int, num_agent: int):
    super().__init__(skill, level)
    self.skill = skill
    self.level = level
    self.num_agent = num_agent

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class DestroyAgent(PredicateTask):
  def __init__(self, agents: List[int]):
    super().__init__(agents)
    self.agents = agents

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class EliminateFoe(PredicateTask):
  def __init__(self, teams: List[int]):
    super().__init__(teams)
    self.teams = teams

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


#######################################
# Event-log based predicates
#######################################


class ScoreHit(PredicateTask):
  def __init__(self, combat_style: Skill.Skill, count: int):
    super().__init__(combat_style, count)
    self.combat_style = combat_style
    self.count = count

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass


class ScoreKill(PredicateTask):
  def __init__(self, teams: List[int], num_kill: int):
    super().__init__(teams, num_kill)
    self.teams = teams
    self.num_kill = num_kill

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass


class TeamScoreKill(ScoreKill):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass
