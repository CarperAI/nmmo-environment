from dataclasses import dataclass
from copy import deepcopy
from typing import Dict, List, Tuple
import json

import numpy as np
import numpy_indexed as npi

from pettingzoo.utils.env import AgentID

import nmmo
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

  # - add extra info that is not in the datastore (e.g., spawn pos)
  # - would IS_WITHIN, TICK, COUNT_DOWN be good here?

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
    self.ent2team: Dict[int, int] = {} # key: ent_id, val: pop_id
    # key: pop_id, val: spawn_pos dict -- ent_id: (row, col)
    self.team2ent: Dict[int, Dict[int, Tuple[int, int]]] = {}

    for ent_id, ent in realm.players.items():
      self.ent2team[ent_id] = ent.population
      if ent.population in self.team2ent:
        # since this is __init__, ent.pos is the spawn pos
        self.team2ent[ent.population].update({ent_id: ent.pos})
      else:
        self.team2ent[ent.population] = {ent_id: ent.pos}

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
    for pop_id, spawn_pos in self.team2ent.items():
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

  # TODO(kywch)
  # most entity/item info can be retrieved from the datastore, but some won't.
  # in that case, we need a simple dataclass to pass remaining info


class Predicate:
  def __init__(self, *args):
    self.name = self._task_name(args)

  def _task_name(self, args):
    tmp_list = [self.__class__.__name__]
    for arg in args:
      if isinstance(arg, type): # class
        # str(arg) gives something like:
        # "<class 'nmmo.systems.item.Ration'>", "<class 'nmmo.io.action.Melee'>"
        tmp_list.append(str(arg)[1:-2].rsplit('.', maxsplit=1)[-1])
      elif "object at" in str(arg):
        tmp_list.append(str(arg).split(' object', maxsplit=1)[0].split('.')[-1])
      elif arg is None:
        tmp_list.append('Any')
      else:
        tmp_list.append(str(arg))
    return '_'.join(tmp_list).replace(' ', '')

  # pylint: disable=inconsistent-return-statements
  def __call__(self, team_gs: TeamGameState, ent_id: int) -> bool:
    """One should describe the code how evaluation is done.
       LLM wiil use it to produce goal embedding, which will be
       used by the RL agent to produce action.
    """
    # base predicates will use super().evaluate(team_gs, ent_id) to check
    # if the provided ent_id can access team_gs
    assert team_gs.is_member(ent_id), \
      "The entity must be in the team to access the provided team gs"

    # check if the cached result is available, and if so return it
    if self.name in team_gs.cache_result:
      return team_gs.cache_result[self.name]

  def _desc(self, class_type):
    return {
      "type": class_type,
      "name": self.name,
      "evaluate": self.__call__.__doc__
    }

  def description(self) -> Dict:
    return self._desc("Predicate")

  def __and__(self, other):
    return AND(self,other)
  def __or__(self, other):
    return OR(self,other)
  def __invert__(self):
    return NOT(self)
  def __rshift__(self,other):
    return IMPLY(self,other)


class AND(Predicate):
  def __init__(self, *tasks: Predicate):
    super().__init__()
    assert len(tasks) > 0
    self._tasks = tasks

    # the name is AND(task1,task2,task3)
    self.name = 'AND(' + ','.join([t.name for t in self._tasks]) + ')'

  def __call__(self, team_gs: TeamGameState, ent_id: int) -> bool:
    """True if all _tasks are evaluated to be True.
       Otherwise false."""
    super().__call__(team_gs, ent_id)
    return all(t(team_gs, ent_id) for t in self._tasks)

  def description(self) -> Dict:
    desc = self._desc("Conjunction")
    desc.update({ 'desc_child': ["AND"] + [t.description() for t in self._tasks] })
    return desc

class OR(Predicate):
  def __init__(self, *tasks: Predicate):
    super().__init__()
    assert len(tasks) > 0
    self._tasks = tasks

    # the name is OR(task1,task2,task3,...)
    self.name = 'OR(' + ','.join([t.name for t in self._tasks]) + ')'

  def __call__(self, team_gs: TeamGameState, ent_id: int) -> bool:
    """True if any of _tasks is evaluated to be True.
       Otherwise false."""
    super().__call__(team_gs, ent_id)
    return any(t(team_gs, ent_id) for t in self._tasks)

  def description(self) -> Dict:
    desc = self._desc("Disjunction")
    desc.update({ 'desc_child': ["OR"] + [t.description() for t in self._tasks] })
    return desc

class NOT(Predicate):
  def __init__(self, task: Predicate):
    super().__init__()
    self._task = task

    # the name is NOT(task)
    self.name = f'NOT({self._task.name})'

  def __call__(self, team_gs: TeamGameState, ent_id: int) -> bool:
    """True if _task is evaluated to be False.
       Otherwise true."""
    super().__call__(team_gs, ent_id)
    return not self._task(team_gs, ent_id)

  def description(self) -> Dict:
    desc = self._desc("Negation")
    desc.update({ 'desc_child': ["NOT", self._task.description()] })
    return desc

class IMPLY(Predicate):
  def __init__(self, p: Predicate, q: Predicate):
    super().__init__()
    self._p = p
    self._q = q

    # the name is IMPLY(p->q)
    self.name = f'IMPLY({self._p.name}->{self._q.name})'

  def __call__(self, team_gs: TeamGameState, ent_id: int) -> bool:
    """False if _p is true and _q is false.
       Otherwise true."""
    super().__call__(team_gs, ent_id)
    if self._p(team_gs, ent_id):
      return self._q(team_gs, ent_id)

    return True

  def description(self) -> Dict:
    desc = self._desc("Conditional")
    desc.update({ 'desc_child': ["IMPLY"] + [t.description() for t in [self._p, self._q]] })
    return desc


class Team:
  def __init__(self, name: str, agents: List[int]) -> None:
    assert len(agents) > 0, "Team must have at least one agent"
    self.name = name
    self._agents = agents

  @property
  def agents(self) ->  List[int]:
    return self._agents

  def description(self) -> Dict:
    return {
      "type": "Team",
      "name": self.name,
      "agents": self._agents
    }

  def member(self, member):
    assert member < len(self._agents)

    if len(self._agents) == 1:
      return self

    # returning a team of one
    return Team(f"{self.name}.{member}", [self._agents[member]])


# CHECK ME: this should produce the same map as the env realm spawn
class TeamHelper:
  def __init__(self, agents: List[int], num_teams: int) -> None:
    assert len(agents) % num_teams == 0
    self.team_size = len(agents) // num_teams
    self._team2ent, self._ent2team = self._map_ent_team(agents, num_teams)

  def _map_ent_team(self, agents, num_teams):
    _team2ent = {}
    _ent2team = {}
    for ent_id in agents:
      # to assigne agent 1 to team 0, and so forth
      pop_id = (ent_id - 1) % num_teams
      _ent2team[ent_id] = pop_id
      if pop_id in _team2ent:
        _team2ent[pop_id].append(ent_id)
      else:
        _team2ent[pop_id] = [ent_id]

    return _team2ent, _ent2team

  def team(self, pop_id: int) -> Team:
    assert pop_id in self._team2ent, "Wrong pop_id"
    return Team(f"Team.{pop_id}", self._team2ent[pop_id])

  def own_team(self, ent_id: int) -> Team:
    assert ent_id in self._ent2team, "Wrong ent_id"
    pop_id = self._ent2team[ent_id]
    return Team(f"Team.{pop_id}", self._team2ent[pop_id])

  def left_team(self, ent_id: int) -> Team:
    assert ent_id in self._ent2team, "Wrong ent_id"
    pop_id = (self._ent2team[ent_id] - 1) % len(self._team2ent)
    return Team(f"Team.{pop_id}", self._team2ent[pop_id])

  def right_team(self, ent_id: int) -> Team:
    assert ent_id in self._ent2team, "Wrong ent_id"
    pop_id = (self._ent2team[ent_id] + 1) % len(self._team2ent)
    return Team(f"Team.{pop_id}", self._team2ent[pop_id])

  def all(self) -> Team:
    return Team("All", list(self._ent2team.keys()))


class Task:
  def __init__(self, goal_fn, assignee: Team,
               reward = 1, name = None, **kwargs):
    assert callable(goal_fn), "Goal eval function goal_fn must be callable"
    self._goal_fn = goal_fn
    self._assignee = assignee
    self._reward = reward
    self._num_reached = 0
    self._kwargs = kwargs

    # used in env.step() info
    # if the goal is a propositional combination of predicates,
    # then for readability, it'd be good to provide a short name
    if name:
      self.name = name
    elif isinstance(goal_fn, Predicate):
      self.name = goal_fn.name
    else:
      self.name = goal_fn.__name__

  # reward() may use count_down timer
  def reward(self, team_gs: TeamGameState, ent_id: int) -> float:
    """Assignee (ent_id) gets reward whenever the goal is reached.
       Whether the goal is reached is evaluated by the goal's evaluate method.
    """
    assert ent_id in self._assignee.agents, "Agent is not on this task"
    if self._goal_fn(team_gs, ent_id):
      self._num_reached += 1
      return self._reward

    return 0

  @property
  def agents(self):
    return self._assignee.agents

  def _fn_desc(self, fn):
    return {
      "type": "EvalFunction",
      "name": fn.__name__,
      "evaluate": fn.__doc__
    }

  def description(self) -> Dict:
    return {
      "type": "Task",
      "goal": self._goal_fn.description() if isinstance(self._goal_fn, Predicate)
                else self._fn_desc(self._goal_fn),
      "assignee": self._assignee.description(),
      "reward": self.reward.__doc__,
      "kwargs": self._kwargs
    }

  def to_string(self) -> str:
    return json.dumps(self.description())


# pylint: disable=abstract-method
class TaskWrapper(nmmo.Env):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    # CHECK ME: should every agent have a task assigned?
    # {task: [ent_id, ent_id, ...]}
    self._tasks: List[Task] = []
    self._ent2task: Dict[int, List[Task]] = {} # reverse map
    self._ent2team: Dict[int, int] = {}

    # game state generator
    self.gs_gen: GameStateGenerator = None
    self.team_gs = None

  def _map_entity_task(self, tasks: List[Task]):
    self._tasks = tasks
    self._ent2task = {}
    for tsk in self._tasks:
      for ent_id in tsk.agents:
        if ent_id in self._ent2task:
          self._ent2task[ent_id].append(tsk)
        else:
          self._ent2task[ent_id] = [tsk]

  # pylint: disable=arguments-renamed
  def reset(self, tasks: List[Task],
            map_id=None, seed=None, options=None):
    gym_obs = super().reset(map_id, seed, options)

    self.gs_gen = GameStateGenerator(self.realm, self.config)
    self._ent2team = self.gs_gen.ent2team
    self._map_entity_task(tasks)

    return gym_obs

  def _compute_rewards(self, agents: List[AgentID], dones: Dict[AgentID, bool]):
    '''Computes the reward for the specified agent'''
    infos = {}
    rewards = { eid: -1 for eid in dones }

    self.team_gs = self.gs_gen.generate(self.realm, self.obs)

    for agent_id in agents:
      infos[agent_id] = {}
      agent = self.realm.players.get(agent_id)

      # CHECK ME: can we trust dead agents are not in the agents list?
      if agent is None:
        # assert agent is not None, f'Agent {agent_id} not found'
        rewards[agent_id] = -1
        continue

      rewards[agent_id] = 0
      pop_id = self._ent2team[agent_id]

      assert agent.population == pop_id, "Inconsistent team assignment. Check TeamHelper"
      infos[agent_id] = { 'population': agent.population, 'task': {} }

      # CHECK ME: some agents may not have a assinged task. is it ok?
      if agent_id in self._ent2task:
        for tsk in self._ent2task[agent_id]:
          rew = tsk.reward(self.team_gs[pop_id], agent_id)
          rewards[agent_id] += rew
          infos[agent_id]['task'].update({ tsk.name: rew })

    return rewards, infos
