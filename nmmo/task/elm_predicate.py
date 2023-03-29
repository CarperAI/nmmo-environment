# WIP
# pylint: skip-file
# pylint: disable=wildcard-import, unused-wildcard-import, unused-import
# High level definition

import numpy as np
from numpy import count_nonzero as count
import inspect
import re
from typing import Dict

from nmmo.task.predicate import *
from nmmo.task.base_predicate import *
from nmmo.task.gold_predicate import *
from nmmo.task.item_predicate import *
from nmmo.task.event_predicate import *
from nmmo.systems import item as Item

class TaskForce:
  def __init__(self, group: Group):
    self._group = group
    self._gs = None
    self._sd = None
  
  def update(self, gs: GameState):
    self._gs = gs
    self._sd = gs.get_subject_view(self._group)

  def __hash__(self) -> int:
    return self._group.__hash__()
  
  def __getattr__(self, attr):
    return self._sd.__getattribute__(attr)

class TaskForceManager:
  def __init__(self, 
               team_helper: TeamHelper,
               policy_id: int) -> None:
    self._th = team_helper
    self._pid = policy_id
    self._gs = None
    self._observers: Dict[TaskForce, TaskForce] = {}

  def register_task_force(self, tf: TaskForce):
    self._observers[tf] = tf

  def set_policy_id(self, policy_id: int):
    self._pid = policy_id

  def update(self, gs: GameState):
    if self._gs is None or self._gs.current_tick != gs.current_tick:
      self._gs = gs
      for tf in self._observers.values():
        tf.update(self._gs)

  @property
  def team(self):
    tf = TaskForce(self, self._th.team(self._pid))
    if tf in self._observers:
      return self._observers[tf]
    self.register_task_force(tf)
    return tf
  
  @property
  def all(self):
    tf = TaskForce(self, self._th.all())
    if tf in self._observers:
      return self._observers[tf]
    self.register_task_force(tf)
    return tf
  
  @property 
  def random(self):
    # Returns a random task force
    all_agents =self._th.all().agents
    tf = TaskForce(np.random.choice(all_agents,
                          size=np.random.randint(1,len(all_agents))))
    if tf in self._observers:
      return self._observers[tf]
    self.register_task_force(tf)
    return tf
  
  @property
  def remaining(self):
    # Agents not split into a task force yet
    raise NotImplementedError
  
  def partition(self, N):
    # Split all agents into N (nearly) equal groups
    raise NotImplementedError

class FunctionPredicate(Predicate):
  def __init__(self, tfm: TaskForceManager, fn: function):
    self._fn = fn
    self._tfm = tfm
  
  def __call__(self, gs: GameState) -> bool:
    self._tfm.update(gs)
    return self._fn()

  @property
  def description(self) -> Dict:
    try:
      desc = self._desc(inspect.getsource(self._fn))
    except OSError:
      desc = self._desc("User defined function")
    return desc
  
###########################################
# Tasks

def elm_preprocess(task: str):
  return re.sub("FP(","FunctionPredicate(task_force_manager, lambda: ")

d1 = '''
def dummy_task(task_force_manager: TaskForceManager):
  g0 = task_force_manager.team
  g1 = task_force_manager.all

  p0 = HoardGold(subject=g0, amount=50)
  p1 = FP(all(g1.health > 0))
  p3 = OwnItem(subject=g0,
               item=Item.Pickaxe,
               level=5,
               quantity=3)

  return {
    g0: p1 & (p0 >> p3)
  }
'''

# To

def dummy_task_one(tfm: TaskForceManager):
  g0 = tfm.team()
  g1 = tfm.all()

  p0 = HoardGold(subject=g0, amount=50)
  p1 = FunctionPredicate(tfm, lambda: all(g1.health > 0))
  p3 = OwnItem(subject=g0,
               item=Item.Pickaxe,
               level=5,
               quantity=3)

  return p1 & (p0 >> p3)

d2 = '''
def elm_fully_equipped(task_force_manager: TaskForceManager):
  g0 = task_force_manager.team

  p0 = OwnItem(subject=g0,
               item=Item.Hat,
               quantity=1,
               level=1)
  p1 = OwnItem(subject=g0,
               item=Item.Top,
               quantity=1,
               level=1)
  p3 = OwnItem(subject=g0,
               item=Item.Bottom,
               quantity=1,
               level=1)
  t3 = OwnItem(subject=g0,
               item=Item.Weapon,
               quantity=1,
               level=1)

  return {
    g0: p1 & p3 & t3 & p4
  }
'''

d3 = '''
def hide_and_seek(task_force_manager: TaskForceManager):
  hide = task_force_manager.random
  seek = task_force_manager.random

  p0 = ~CanSeeAgent(seek, hide)
  p1 = CanSeeAgent(seek, hide)

  return {
    hide: p0,
    seek: p1
  }
'''

d4 = '''
def chicken(task_force_manager: TaskForceManager):
  g0,g1 = task_force_manager.partition(2)

  p0 = FP(count(g0.alive < g1.alive))
  p1 = FP(count(g1.alive < g0.alive))

  return {
    g0: p0,
    g1: p1
  }
'''

d5 = '''
def economy(task_force_manager: TaskForceManager):
  teams = task_force_manager.partition(5)
  tasks = \{\}
  for team in teams:
    tasks[team] = HoardGold(team, 3000)
  return tasks
'''

# tfm = TaskForceManager(team_helper, 0)
# 
# task = dummy_task(TaskForceManager(th,....))