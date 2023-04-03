from typing import Dict, Tuple, List
from nmmo.task.group import Group
from nmmo.task.predicate import Predicate

class TeamHelper:
  ''' Provides a mapping from ent_id to group as equivalent to the grouping
  expected by the policy
  '''

  def __init__(self, agents: List[int], num_teams: int):
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

  def team(self, pop_id: int) -> Group:
    assert pop_id in self._team_to_ent, "Wrong pop_id"
    return Group(self._team_to_ent[pop_id], f"Team.{pop_id}")

  def own_team(self, ent_id: int) -> Group:
    assert ent_id in self._ent_to_team, "Wrong ent_id"
    pop_id = self._ent_to_team[ent_id]
    return Group(self._team_to_ent[pop_id], f"Team.{pop_id}")

  def left_team(self, ent_id: int) -> Group:
    assert ent_id in self._ent_to_team, "Wrong ent_id"
    pop_id = (self._ent_to_team[ent_id] - 1) % len(self._team_to_ent)
    return Group(self._team_to_ent[pop_id], f"Team.{pop_id}")

  def right_team(self, ent_id: int) -> Group:
    assert ent_id in self._ent_to_team, "Wrong ent_id"
    pop_id = (self._ent_to_team[ent_id] + 1) % len(self._team_to_ent)
    return Group(self._team_to_ent[pop_id], f"Team.{pop_id}")

  def all(self) -> Group:
    return Group(list(self._ent_to_team.keys()), "All")

class TaskManager:
  def __init__(self):
    # task_assignment = {
    #   agent1: [(task1, 1), (task2, -1)],
    #   agent2: [(task1, -1), (task3, 2)] }
    self._task_assignment: Dict[int, List[Tuple[Predicate, int]]] = {}

  @property
  def assigned(self):
    return self._task_assignment

  def update(self, ent_id: int, tasks: List[Tuple[Predicate, int]]):
    self._task_assignment[ent_id] = tasks

  def append(self, ent_id: int, task: Tuple[Predicate, int]):
    if ent_id in self._task_assignment:
      self._task_assignment[ent_id].append(task)
    else:
      self._task_assignment[ent_id] = [task]

  # assign task to assignees with the reward
  # NOTE: the same reward is assigned to all assignee. If one wants different reward,
  #   one should use 'update' or 'append' for individual assignee
  def assign(self, task: Predicate, assignee: Group, reward: int):
    for ent_id in assignee:
      self.append(ent_id, (task, reward))
