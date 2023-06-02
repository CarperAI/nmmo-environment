# pylint: disable=unused-import
from typing import Callable, Iterable, Dict, List, Union, Tuple
from types import FunctionType
from abc import ABC

from nmmo.task.group import Group
from nmmo.task.predicate_api import Predicate, arg_to_string
from nmmo.task.base_predicates import StayAlive

class Task(ABC):
  """ A task is used to calculate rewards for agents in assignee
      based on the predicate and game state
  """
  def __init__(self,
               eval_fn: Callable,
               assignee: Union[Iterable[int], int],
               reward_multiplier = 1.0):
    if isinstance(assignee, int):
      self._assignee = (assignee,)
    else:
      assert len(assignee) > 0, "Assignee cannot be empty"
      self._assignee = tuple(set(assignee)) # dedup
    self._eval_fn = eval_fn
    self._progress = 0.0
    self._completed = False
    self._reward_multiplier = reward_multiplier

    self.name = self._make_name(self.__class__.__name__,
                                eval_fn=eval_fn, assignee=self._assignee)

  def reset(self):
    self._progress = 0.0
    self._completed = False

  @property
  def assignee(self) -> Tuple[int]:
    return self._assignee

  @property
  def completed(self) -> bool:
    return self._completed

  @property
  def reward_multiplier(self) -> float:
    return self._reward_multiplier

  def _map_progress_to_reward(self, gs) -> float:
    """ The default reward is the diff between the old and new progress.
        Once the task is completed, no more reward is provided.

        Override this function to create a custom reward function
    """
    if self._completed:
      return 0.0

    new_progress = max(min(self._eval_fn(gs)*1.0,1.0),0.0)
    diff = new_progress - self._progress
    self._progress = new_progress
    if self._progress >= 1:
      self._completed = True

    return diff

  def compute_rewards(self, gs) -> Tuple[Dict[int, float], Dict[int, Dict]]:
    """ Environment facing API

    Returns rewards and infos for all agents in subject
    """
    reward = self._map_progress_to_reward(gs) * self._reward_multiplier
    rewards = {int(ent_id): reward for ent_id in self._assignee}
    infos = {int(ent_id): {'reward': reward, 'progress': self._progress}
             for ent_id in self._assignee}

    # NOTE: tasks do not know whether assignee agents are alive or dead
    #   so the Env must check it before filling in rewards and infos
    return rewards, infos

  def _make_name(self, class_name, **kwargs) -> str:
    name = [class_name] + \
      [f"{arg_to_string(key)}:{arg_to_string(arg)}" for key, arg in kwargs.items()]
    name = "("+'_'.join(name).replace(' ', '')+")"
    return name

  def __str__(self):
    return self.name

class OngoingTask(Task):
  def _map_progress_to_reward(self, gs) -> float:
    """Keep returning the progress reward after the task is completed.
       However, this task tracks the completion status in the same manner.
    """
    self._progress = max(min(self._eval_fn(gs)*1.0,1.0),0.0)
    if self._progress >= 1:
      self._completed = True
    return self._progress


######################################################################

def nmmo_default_task(agent_list: Iterable[int], test_mode=None) -> List[Task]:
  if test_mode is None:
    # use the full predicate system
    return [StayAlive(Group(agent_id)).create_task(task_cls=OngoingTask)
            for agent_id in agent_list]

  if test_mode == 'no_task':
    return []

  if test_mode == 'dummy_eval_fn':
    return [OngoingTask(eval_fn=make_stay_alive_eval(Group(agent_id), test_mode),
                        assignee=agent_id) for agent_id in agent_list]

  # use the function-based eval
  return [OngoingTask(eval_fn=make_stay_alive_eval(Group(agent_id)),
                      assignee=agent_id) for agent_id in agent_list]

# for speed testing, function-based eval
def make_stay_alive_eval(subject: Group, test_mode=None):
  if test_mode is None:
    def stay_alive_eval(gs):
      return all(agent_id in gs.alive_agents for agent_id in subject.agents)
  else:
    # use dummy eval function for speed testing
    def stay_alive_eval(gs):
      # pylint: disable=unused-argument
      return True

  # change function name for each agent
  return FunctionType(
    stay_alive_eval.__code__, globals(), f"StayAlive_fn_{str(subject.agents)}",
    closure=stay_alive_eval.__closure__
  )
