from __future__ import annotations
from typing import Dict, List, Union, Tuple
from functools import reduce
from abc import ABC, abstractmethod
from pettingzoo.utils.env import AgentID

import nmmo
from nmmo.task.game_state import GameStateGenerator
from nmmo.task.predicate import Predicate
from nmmo.task.group import Group
from nmmo.task.game_state import GameState

class Task(ABC):
  def __init__(self, assignee: Group):
    self._assignee = assignee

  @property
  def assignee(self):
    return self._assignee

  @abstractmethod
  def rewards(self, gs: GameState) -> Tuple[Dict[int, float], Dict[int, Dict]]:
    """ Returns a mapping from ent_id to rewards and infos for all 
    entities in assignee
    """
    raise NotImplementedError

class PredicateTask(Task, ABC):
  def __init__(self,
               assignee: Group,
               predicate: Predicate):
    super().__init__(assignee)
    self._predicate = predicate

  def evaluate(self, gs: GameState) -> float:
    name = self._predicate.name
    cache = gs.cache_result
    if name not in cache:
      cache[name] = self._predicate(gs)
    return cache[name]

class Once(PredicateTask):
  def __init__(self,
               assignee: Group,
               predicate: Predicate,
               reward = 1):
    super().__init__(assignee, predicate)
    self._reward = reward
    self._completed = False

  def rewards(self, gs: GameState):
    rewards = {int(ent_id): 0 for ent_id in self._assignee}
    infos = {int(ent_id): {self._predicate.name: self.evaluate(gs)}
             for ent_id in self._assignee}
    if not self._completed and self.evaluate(gs):
      self._completed = True
      rewards = {int(ent_id): self._reward for ent_id in self._assignee}
    return rewards, infos

class Repeat(PredicateTask):
  def __init__(self,
               assignee: Group,
               predicate: Predicate,
               reward = 1):
    super().__init__(assignee, predicate)
    self._reward = reward

  def rewards(self, gs: GameState):
    rewards = {int(ent_id): 0 for ent_id in self._assignee}
    infos = {int(ent_id): {self._predicate.name: self.evaluate(gs)}
             for ent_id in self._assignee}
    if self.evaluate(gs):
      rewards = {int(ent_id): self._reward for ent_id in self._assignee}
    return rewards, infos

class MultiTask(Task):
  def __init__(self,
               *tasks: Union[Tuple[Task, float], Task]):
    assert len(tasks) > 0
    self._tasks = [t if isinstance(t, Tuple) else (t,1) for t in tasks]
    super().__init__(reduce(lambda a,b: a.union(b),
                            [task[0].assignee for task in self._tasks]))

  def rewards(self, gs: GameState) -> Dict[int, float]:
    rewards = {}
    infos = {}
    for task, weight in self._tasks:
      task_reward, task_infos = task.rewards(gs)
      for ent_id, reward in task_reward.items():
        rewards[ent_id] = rewards.get(ent_id,0) + reward * weight
      for ent_id, info in task_infos.items():
        if not ent_id in infos:
          infos[ent_id] = {}
        infos[ent_id] = {**infos[ent_id], **info}

    return rewards, infos

################################################
# Environment Wrapper
# Eventually should replace env.py once stable
# TODO(mark) Syllabus

# pylint: disable=abstract-method
class TaskEnv(nmmo.Env):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.task: Task = None
    self.gs_gen: GameStateGenerator = None

    self.reset()

  def change_task(self, new_task: Task):
    self.task = new_task
    self.reset()

  # pylint: disable=arguments-renamed
  def reset(self,
            map_id=None,
            seed=None,
            options=None):
    gym_obs = super().reset(map_id, seed, options)
    self.gs_gen = GameStateGenerator(self.realm, self.config)
    return gym_obs

  def _encode_goal(self):
    raise NotImplementedError

  def _compute_rewards(self, agents: List[AgentID], dones: Dict[AgentID, bool]):
    infos = {}
    game_state = self.gs_gen.generate(self.realm, self.obs)

    rewards = {eid: 0 for eid in agents}
    task_rewards, task_infos = self.task.rewards(game_state)
    for eid, reward in task_rewards.items():
      rewards[eid] = reward
    for eid in dones:
      rewards[eid] = -1 #TODO(mark) should this be 0 instead

    for eid in agents:
      infos[eid] = {}
      infos[eid]['task'] = {}
      if eid in task_infos:
        infos[eid]['task'] = task_infos[eid]

    return rewards, infos
