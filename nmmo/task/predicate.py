from typing import Dict

from nmmo.task.game_state import TeamGameState


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
