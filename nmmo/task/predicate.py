from typing import Dict, List, Tuple, Iterable
from collections import OrderedDict

from nmmo.task.game_state import GameState


# TODO(kywch): Revisit Team and re-evaluate if putting it here makes sense
# NOTE: changed Team to Group, to be more general
class Group:
  def __init__(self, agents:Iterable[int], name:str=None):
    assert len(agents) > 0, "Team must have at least one agent"
    self.name = name if name else f"Agent{str(agents).replace(' ', '')}"
    # Remove duplicates
    self._agents = tuple(OrderedDict.fromkeys(agents).keys())
    if not isinstance(self._agents,Tuple):
      self._agents = (self._agents,)

  @property
  def agents(self) -> Tuple[int]:
    return self._agents

  def __contains__(self, ent_id: int):
    return ent_id in self._agents

  def __len__(self):
    return len(self._agents)
  
  def __hash__(self):
    return self._agents.__hash__()

  def description(self) -> Dict:
    return {
      "type": "Group",
      "name": self.name,
      "agents": self._agents
    }

  def member(self, member):
    assert member < len(self._agents)

    if len(self._agents) == 1:
      return self

    # returning a group of one
    return Group((self._agents[member],), f"{self.name}.{member}")


# TODO(kywch): consider removing the tight coupling between policy - team
#   Currently, this should produce the same map as the env realm spawn
#   However, this may change later.
class TeamHelper:
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


class Predicate:
  # Predicate: states something about the subject
  def __init__(self, subject:Group, *args):
    assert len(subject) > 0, "There must be at least one agent in subject."
    self._name = self._task_name(subject, args)
    self._subject = subject.agents

  @property
  def name(self):
    return self._name

  @property
  def subject(self) -> List[int]:
    return self._subject

  def _task_name(self, subject:Group, args):
    tmp_list = [self.__class__.__name__]
    if subject:
      tmp_list.append(subject.name.replace('Agent','Subject'))

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

  def __call__(self, gs: GameState) -> bool:
    """One should describe the code how evaluation is done.
       LLM might use it to produce goal embedding, which will be
       used by the RL agent to produce action.
    """
    raise NotImplementedError

  def _desc(self, class_type):
    return {
      "type": class_type,
      "name": self.name,
      "evaluate": self.__call__.__doc__
    }

  @property
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
    # pylint: disable=super-init-not-called
    assert len(tasks) > 0
    self._tasks = tasks

    # the name is AND(task1,task2,task3)
    self._name = 'AND(' + ','.join([t.name for t in self._tasks]) + ')'

  def __call__(self, gs: GameState) -> bool:
    """True if all _tasks are evaluated to be True.
       Otherwise false."""
    return all(t(gs) for t in self._tasks)

  @property
  def description(self) -> Dict:
    desc = self._desc("Conjunction")
    desc.update({ 'desc_child': ["AND"] + [t.description for t in self._tasks] })
    return desc

class OR(Predicate):
  def __init__(self, *tasks: Predicate):
    # pylint: disable=super-init-not-called
    assert len(tasks) > 0
    self._tasks = tasks

    # the name is OR(task1,task2,task3,...)
    self._name = 'OR(' + ','.join([t.name for t in self._tasks]) + ')'

  def __call__(self, gs: GameState) -> bool:
    """True if any of _tasks is evaluated to be True.
       Otherwise false."""
    return any(t(gs) for t in self._tasks)

  @property
  def description(self) -> Dict:
    desc = self._desc("Disjunction")
    desc.update({ 'desc_child': ["OR"] + [t.description for t in self._tasks] })
    return desc

class NOT(Predicate):
  def __init__(self, task: Predicate):
    # pylint: disable=super-init-not-called
    self._task = task

    # the name is NOT(task)
    self._name = f'NOT({self._task.name})'

  def __call__(self, gs: GameState) -> bool:
    """True if _task is evaluated to be False.
       Otherwise true."""
    return not self._task(gs)

  @property
  def description(self) -> Dict:
    desc = self._desc("Negation")
    desc.update({ 'desc_child': ["NOT", self._task.description] })
    return desc

class IMPLY(Predicate):
  def __init__(self, p: Predicate, q: Predicate):
    # pylint: disable=super-init-not-called
    self._p = p
    self._q = q

    # the name is IMPLY(p->q)
    self._name = f'IMPLY({self._p.name}->{self._q.name})'

  def __call__(self, gs: GameState) -> bool:
    """False if _p is true and _q is false.
       Otherwise true."""
    if self._p(gs):
      return self._q(gs)

    return True

  @property
  def description(self) -> Dict:
    desc = self._desc("Conditional")
    desc.update({ 'desc_child': ["IMPLY"] + [t.description for t in [self._p, self._q]] })
    return desc


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
    for ent_id in assignee.agents:
      self.append(ent_id, (task, reward))
