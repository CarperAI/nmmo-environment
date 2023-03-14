# pylint: disable=redefined-outer-name,super-init-not-called

import logging
import unittest

import nmmo
from nmmo.task import task, sampler
import nmmo.task.base_predicate
from nmmo.core.realm import Realm
from nmmo.systems import item as Item
from nmmo.io import action as Action

from testhelpers import ScriptedAgentTestConfig
from scripted.baselines import Sleeper


class Success(task.PredicateTask):
  def evaluate(self, team_gs: task.TeamGameState, ent_id: int) -> bool:
    """Always true"""
    return True

class Failure(task.PredicateTask):
  def evaluate(self, team_gs: task.TeamGameState, ent_id: int) -> bool:
    """Always false"""
    return False

class FakeTask(task.PredicateTask):
  def __init__(self, param1: int, param2: Item.Item, param3: Action.Style) -> None:
    super().__init__(param1, param2, param3)
    self._param1 = param1
    self._param2 = param2
    self._param3 = param3

  def evaluate(self, team_gs: task.TeamGameState, ent_id: int) -> bool:
    return False

config = ScriptedAgentTestConfig()
class MockRealm(Realm):
  pass

class MockGameState(task.TeamGameState):
  def __init__(self):
    pass

realm = MockRealm(config)
team_gs = MockGameState()
ent_id = 0

class TestTaskAPI(unittest.TestCase):

  def test_operators(self):
    # AND (&), OR (|), NOT (~), IMPLY (>>)
    self.assertFalse(task.AND(Success(), Failure(), Success()).evaluate(team_gs, ent_id))
    self.assertFalse((Success() & Failure() & Success()).evaluate(team_gs, ent_id))

    self.assertTrue(task.OR(Success(), Failure(), Success()).evaluate(team_gs, ent_id))
    self.assertTrue((Success() | Failure() | Success()).evaluate(team_gs, ent_id))
    
    self.assertTrue(task.AND(Success(), task.NOT(Failure()), Success()).evaluate(team_gs, ent_id))
    self.assertTrue(task.AND(Success(), ~Failure(), Success()).evaluate(team_gs, ent_id))

    self.assertTrue(task.IMPLY(Success(), Success()).evaluate(team_gs, ent_id))
    self.assertFalse(task.IMPLY(Success(), Failure()).evaluate(team_gs, ent_id))
    self.assertTrue(task.IMPLY(Failure(), Success()).evaluate(team_gs, ent_id))
    self.assertTrue((Failure() >> Success()).evaluate(team_gs, ent_id))

  def test_task_name(self):
    success = Success()
    failure = Failure()
    fake_task = FakeTask(1, Item.Hat, Action.Melee)
    combination = (success & ~ (failure | fake_task)) | (failure >> fake_task)
    
    self.assertEqual(combination.name, 
      'OR(AND(Success,NOT(OR(Failure,FakeTask_1_Hat_Melee))),IMPLY(Failure->FakeTask_1_Hat_Melee))')

  def test_team_helper(self):
    config = ScriptedAgentTestConfig()
    env = nmmo.Env(config)
    env.reset()

    team_helper = task.TeamHelper(list(range(1, config.PLAYER_N+1)), len(config.PLAYERS))

    # agents' population should match team_helper team id
    for ent_id, ent in env.realm.players.items():
      self.assertEqual(team_helper._ent2team[ent_id], ent.population)

  def test_task_force(self):
    task_force =  task.TaskForce("Foo", [1, 2, 8, 9])

    self.assertEqual(task_force.member(2).name, "Foo.2")
    self.assertEqual(task_force.member(2).agents, [8])

    # don't allow member of one-member team
    self.assertEqual(task_force.member(2).member(0).name, task_force.member(2).name)

  def test_random_task_sampler(self):
    rand_sampler = sampler.RandomTaskSampler()

    rand_sampler.add_task_spec(Success)
    rand_sampler.add_task_spec(Failure)
    rand_sampler.add_task_spec(FakeTask, [
      [Item.Hat, Item.Top, Item.Bottom],
      [1, 5, 10],
      [0.1, 0.2, 0.3, 0.4]
    ])

    test = rand_sampler.sample(max_clauses=4, max_clause_size=3, not_p=0.5)

  def test_default_sampler(self):
    pass

  def test_completed_tasks_in_info(self):
    config = ScriptedAgentTestConfig()
    env = task.TaskWrapper(config)

    # some team helper maybe necessary
    team_helper = task.TeamHelper( list(range(1, config.PLAYER_N+1)), len(config.PLAYERS))
    missions = [
      task.Mission( Success(), team_helper.all() ),
      task.Mission( Failure(), team_helper.team(1) ),
      task.Mission( FakeTask(1, Item.Ration, Action.Melee), team_helper.team(2) )
    ]

    env.reset(missions)
    _, _, _, infos = env.step({})
    logging.info(infos)

    # agent 2 should have been assigned Success() and Failure() but not FakeTask()
    self.assertEqual(infos[2]['mission'][Success().name], 1)
    self.assertEqual(infos[2]['mission'][Failure().name], 0)
    self.assertTrue(FakeTask(1, Item.Ration, Action.Melee).name not in infos[2]['mission'])

    # agent 3 should have been assigned FakeTask(), which is always False (0)
    self.assertEqual(infos[3]['mission'][FakeTask(1, Item.Ration, Action.Melee).name], 0)


if __name__ == '__main__':
  unittest.main()
