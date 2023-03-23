# TODO: the below line will be gone after implementation
# pylint: disable=unnecessary-pass
from typing import List

from nmmo.task.predicate import Predicate
from nmmo.task.game_state import TeamGameState
from nmmo.systems import skill as Skill
from nmmo.lib.material import Material
from nmmo.lib import utils

from nmmo.entity.entity import EntityState


class Timer(Predicate):
  def __init__(self, num_tick: int):
    super().__init__(num_tick)
    self.num_tick = num_tick

  def __call__(self, team_gs: TeamGameState, ent_id):
    """True if the current tick is within the specified num_tick
       Otherwise false.
    """
    return team_gs.tick <= self.num_tick


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
class TeamSizeGE(Predicate): # greater than or equal to
  def __init__(self, num_agent: int):
    super().__init__(num_agent)
    self.num_agent = num_agent

  def __call__(self, team_gs, ent_id):
    """True if the number of alive teammates is greater than or equal to min_size.
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    if team_gs.pop_id in team_gs.alive_byteam:
      return len(team_gs.alive_byteam[team_gs.pop_id]) >= self.num_agent

    return False


class ProtectAgent(Predicate):
  def __init__(self, agents: List[int]):
    #   is this right?
    super().__init__(agents)
    self.agents = agents

  def __call__(self, team_gs, ent_id):
    """True if the specified agents (list of ent_id) are ALL alive
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)

    # cache the result
    team_gs.cache_result[self.name] = False

    # CHECK ME: should we allow empty agents?
    if len(self.agents):
      # CHECK ME: No self/foe masking for now. Do we need masking, or not at all?
      alive_target = set(self.agents).intersection(team_gs.alive_agents)

      # if all specified agents are alive, the len(intersection) should be the same
      team_gs.cache_result[self.name] = len(alive_target) == len(self.agents)

    return team_gs.cache_result[self.name]


class SearchTile(Predicate):
  def __init__(self, tile_type: Material):
    super().__init__(tile_type)
    self.tile_type = tile_type.index

  def __call__(self, team_gs: TeamGameState, ent_id):
    """True if the self.tile_type is within the agent(ent_id)'s tile obs
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    assert ent_id in team_gs.env_obs, "The agent's obs is not in team_gs.env_obs"

    # all tiles in the full visual field are in team_gs.env_obs[ent_id].tiles
    tile_obs = team_gs.env_obs[ent_id].tiles[:,team_gs.tile_cols['material_id']]

    return self.tile_type in tile_obs


class TeamSearchTile(SearchTile):
  def __call__(self, team_gs, ent_id):
    """True if the self.tile_type is within the whole team's tile obs
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)

    # cache the result
    team_gs.cache_result[self.name] = False

    for obs in team_gs.env_obs.values():
      tile_obs = obs.tiles[:,team_gs.tile_cols['material_id']]
      if self.tile_type in tile_obs:
        team_gs.cache_result[self.name] = True
        break

    return team_gs.cache_result[self.name]


class SearchAgent(Predicate):
  def __init__(self, obj_agent: int):
    super().__init__(obj_agent)
    self.obj_agent = obj_agent

  def __call__(self, team_gs: TeamGameState, ent_id):
    """True if self.obj_agent is present in the agent(ent_id)'s entities obs
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    assert ent_id in team_gs.env_obs, "The agent's obs is not in team_gs.env_obs"

    # all entities within ent_id's visual field
    entities = team_gs.env_obs[ent_id].entities.ids

    return self.obj_agent in entities


class TeamSearchAgent(SearchAgent):
  def __call__(self, team_gs, ent_id):
    """True if self.obj_agent is present in the team's entities obs
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)

    # cache the result
    team_gs.cache_result[self.name] = False

    for obs in team_gs.env_obs.values():
      if self.obj_agent in obs.entities.ids:
        team_gs.cache_result[self.name] = True
        break

    return team_gs.cache_result[self.name]


class GotoTile(Predicate):
  def __init__(self, row: int, col: int):
    super().__init__(row, col)
    # CHECK ME: the specified row, col should be habitable
    #  otherwise, this goal cannot be reached
    self.row = row
    self.col = col

  def __call__(self, team_gs, ent_id):
    """True if the agent is on the designated tile. 
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    agent = team_gs.entity_or_none(ent_id)
    if agent:
      return (agent.row == self.row) & (agent.col == self.col)

    return False


class TeamOccupyTile(GotoTile):
  def __call__(self, team_gs, ent_id):
    """True if any agent in the team is on the desginated tile
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)

    # cache the result
    team_gs.cache_result[self.name] = False

    for i in range(team_gs.entity_data.shape[0]):
      entity = EntityState.parse_array(team_gs.entity_data[i])
      if (entity.row == self.row) & (entity.col == self.col):
        team_gs.cache_result[self.name] = True
        break

    return team_gs.cache_result[self.name]


class GoDistance(Predicate):
  def __init__(self, dist: int):
    super().__init__(dist)
    self.dist = dist

  def __call__(self, team_gs, ent_id):
    """True if the l-inf distance between the agent's current pos and spawn pos
        is greater than or equal to the specified dist.
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    agent = team_gs.entity_or_none(ent_id)
    if agent:
      curr_pos = (agent.row, agent.col)
      return utils.linf(curr_pos, team_gs.spawn_pos[ent_id]) >= self.dist

    return False


class TeamGoDistance(GoDistance):
  def __call__(self, team_gs, ent_id):
    """True if the summed l-inf distance between each agent's current pos and spawn pos
        is greater than or equal to the specified dist.
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)

    # cache the result
    team_gs.cache_result[self.name] = False

    sum_dist = 0
    for i in range(team_gs.entity_data.shape[0]):
      mate = EntityState.parse_array(team_gs.entity_data[i])
      curr_pos = (mate.row, mate.col)
      sum_dist += utils.linf(curr_pos, team_gs.spawn_pos[mate.id])

    team_gs.cache_result[self.name] = sum_dist >= self.dist

    return team_gs.cache_result[self.name]


class StayCloseTo(Predicate):
  def __init__(self, obj_agent:int, dist: int):
    super().__init__(obj_agent, dist)
    self.obj_agent = obj_agent
    self.dist = dist

  def __call__(self, team_gs, ent_id):
    """True if the distance between self.obj_agent and ent_id is 
        less than or equal to self.dist
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    assert ent_id in team_gs.env_obs, "The agent's obs is not in team_gs.env_obs"

    # the target is None if it is outside ent's visual field
    target = team_gs.env_obs[ent_id].entity(self.obj_agent)
    agent = team_gs.entity_or_none(ent_id)

    if target and agent: # both are present
      target_pos = (target.row, target.col)
      curr_pos = (agent.row, agent.col)

      return utils.linf(target_pos, curr_pos) <= self.dist

    return False


class TeamStayClose(Predicate):
  def __init__(self, dist: int):
    super().__init__(dist)
    self.dist = dist

  def __call__(self, team_gs, ent_id):
    """True if the max l-inf distance of teammates is 
         less than or equal to self.dist
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)

    # cache the result
    team_gs.cache_result[self.name] = False

    rows = team_gs.entity_data[:,team_gs.entity_cols['row']]
    cols = team_gs.entity_data[:,team_gs.entity_cols['col']]

    # compare the outer most coordinates of all teammates
    team_gs.cache_result[self.name] = \
      max(max(rows)-min(rows), max(cols)-min(cols)) <= self.dist

    return team_gs.cache_result[self.name]


def skill_to_str(skill: Skill.Skill):
  # str(skill) looks like "<class 'nmmo.systems.skill.Melee'>"
  #  this function turns it to 'melee'
  return str(skill)[1:-2].rsplit('.', maxsplit=1)[-1].lower()

class AttainSkill(Predicate):
  def __init__(self, skill: Skill.Skill, level: int):
    super().__init__(skill, level)
    self.skill = skill_to_str(skill)
    self.level = level

  def __call__(self, team_gs, ent_id):
    """True if the agent's (ent_id) level of specifiled self.skill is
        greather than or equal to self.level
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    agent = team_gs.entity_or_none(ent_id)
    if agent:
      return getattr(agent, self.skill + '_level') >= self.level

    return False


class TeamAttainSkill(Predicate):
  def __init__(self, skill: Skill.Skill, level: int, num_agent: int):
    super().__init__(skill, level, num_agent)
    self.skill = skill_to_str(skill)
    self.level = level
    self.num_agent = num_agent

  def __call__(self, team_gs, ent_id):
    """True if the number of agents having self.skill level GE self.level
        is greather than or equal to self.num_agent
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)

    # cache the result
    team_gs.cache_result[self.name] = False

    # each row represents alive agents in the team
    skill_level = team_gs.entity_data[:,team_gs.entity_cols[self.skill + '_level']]

    team_gs.cache_result[self.name] = sum(skill_level >= self.level) >= self.num_agent

    return team_gs.cache_result[self.name]


class DestroyAgent(Predicate):
  def __init__(self, agents: List[int]):
    super().__init__(agents)
    self.agents = agents

  def __call__(self, team_gs, ent_id):
    """True if the specified agents (list of ent_id) are ALL dead
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)

    # cache the result
    team_gs.cache_result[self.name] = False

    # CHECK ME: should we allow empty agents?
    if len(self.agents):
      alive_target = set(self.agents).intersection(team_gs.alive_agents)

      # if all specified agents are alive, the len(intersection) should be the same
      team_gs.cache_result[self.name] = len(alive_target) == 0

    return team_gs.cache_result[self.name]


class EliminateFoe(Predicate):
  def __init__(self, teams:List[int]=None):
    super().__init__(teams)
    self.teams = teams

  def __call__(self, team_gs, ent_id):
    """True if the specified teams are ALL eliminated
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)

    # cache the result
    team_gs.cache_result[self.name] = True

    if self.teams is None or len(self.teams) == 0:
      teams = list(team_gs.alive_byteam.keys())
      alive_teams = [pop_id for pop_id in teams if pop_id >= 0 and
                     pop_id != team_gs.pop_id] # exclude npcs and self
      team_gs.cache_result[self.name] = len(alive_teams) == 0

    else:
      for pop_id in self.teams:
        # CHECK ME: assuming alive_byteam[pop_id] is empty, if pop_id is eliminated
        if pop_id in team_gs.alive_byteam:
          team_gs.cache_result[self.name] = False
          break

    return team_gs.cache_result[self.name]


#######################################
# Event-log based predicates
#######################################


class ScoreHit(Predicate):
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


class ScoreKill(Predicate):
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
