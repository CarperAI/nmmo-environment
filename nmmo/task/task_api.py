from typing import Dict, List
import json

from pettingzoo.utils.env import AgentID

import nmmo
from nmmo.task.game_state import TeamGameState, GameStateGenerator
from nmmo.task.predicate import Predicate


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
# TODO(kywch): consider removing the tight coupling between policy - team
class TeamHelper:
  def __init__(self, agents: List[int], num_teams: int) -> None:
    assert len(agents) % num_teams == 0
    self.team_size = len(agents) // num_teams
    self._team_to_ent, self._ent_to_team = self._map_ent_team(agents, num_teams)

  def _map_ent_team(self, agents, num_teams):
    _team_to_ent = {}
    _ent_to_team = {}
    for ent_id in agents:
      # to assigne agent 1 to team 0, and so forth
      pop_id = (ent_id - 1) % num_teams
      _ent_to_team[ent_id] = pop_id
      if pop_id in _team_to_ent:
        _team_to_ent[pop_id].append(ent_id)
      else:
        _team_to_ent[pop_id] = [ent_id]

    return _team_to_ent, _ent_to_team

  def team(self, pop_id: int) -> Team:
    assert pop_id in self._team_to_ent, "Wrong pop_id"
    return Team(f"Team.{pop_id}", self._team_to_ent[pop_id])

  def own_team(self, ent_id: int) -> Team:
    assert ent_id in self._ent_to_team, "Wrong ent_id"
    pop_id = self._ent_to_team[ent_id]
    return Team(f"Team.{pop_id}", self._team_to_ent[pop_id])

  def left_team(self, ent_id: int) -> Team:
    assert ent_id in self._ent_to_team, "Wrong ent_id"
    pop_id = (self._ent_to_team[ent_id] - 1) % len(self._team_to_ent)
    return Team(f"Team.{pop_id}", self._team_to_ent[pop_id])

  def right_team(self, ent_id: int) -> Team:
    assert ent_id in self._ent_to_team, "Wrong ent_id"
    pop_id = (self._ent_to_team[ent_id] + 1) % len(self._team_to_ent)
    return Team(f"Team.{pop_id}", self._team_to_ent[pop_id])

  def all(self) -> Team:
    return Team("All", list(self._ent_to_team.keys()))


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
    self._ent_to_task: Dict[int, List[Task]] = {} # reverse map
    self._ent_to_team: Dict[int, int] = {}

    # game state generator
    self.gs_gen: GameStateGenerator = None
    self.team_gs = None

  def _map_entity_task(self, tasks: List[Task]):
    self._tasks = tasks
    self._ent_to_task = {}
    for tsk in self._tasks:
      for ent_id in tsk.agents:
        if ent_id in self._ent_to_task:
          self._ent_to_task[ent_id].append(tsk)
        else:
          self._ent_to_task[ent_id] = [tsk]

  # pylint: disable=arguments-renamed
  def reset(self, tasks: List[Task],
            map_id=None, seed=None, options=None):
    gym_obs = super().reset(map_id, seed, options)

    self.gs_gen = GameStateGenerator(self.realm, self.config)
    self._ent_to_team = self.gs_gen.ent_to_team
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
      pop_id = self._ent_to_team[agent_id]

      assert agent.population == pop_id, "Inconsistent team assignment. Check TeamHelper"
      infos[agent_id] = { 'population': agent.population, 'task': {} }

      # CHECK ME: some agents may not have a assinged task. is it ok?
      if agent_id in self._ent_to_task:
        for tsk in self._ent_to_task[agent_id]:
          rew = tsk.reward(self.team_gs[pop_id], agent_id)
          rewards[agent_id] += rew
          infos[agent_id]['task'].update({ tsk.name: rew })

    return rewards, infos
