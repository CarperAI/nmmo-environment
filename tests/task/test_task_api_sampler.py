import logging
import unittest

from tests.testhelpers import ScriptedAgentTestConfig

import nmmo

# pylint: disable=import-error
from nmmo.task import sampler
from nmmo.task.task_api import TeamHelper, Team, Task, TaskWrapper
from nmmo.task.predicate import Predicate
from nmmo.task.game_state import TeamGameState
import nmmo.task.base_predicate
from nmmo.systems import item as Item
from nmmo.io import action as Action


class Success(Predicate):
  def __call__(self, team_gs: TeamGameState, ent_id: int) -> bool:
    """Always true"""
    return True

class Failure(Predicate):
  def __call__(self, team_gs: TeamGameState, ent_id: int) -> bool:
    """Always false"""
    return False

class FakeTask(Predicate):
  def __init__(self, param1: int, param2: Item.Item, param3: Action.Style) -> None:
    super().__init__(param1, param2, param3)
    self._param1 = param1
    self._param2 = param2
    self._param3 = param3

  def __call__(self, team_gs: TeamGameState, ent_id: int) -> bool:
    return False


class MockGameState(TeamGameState):
  def __init__(self):
    # pylint: disable=super-init-not-called
    self.cache_result = {}

  def is_member(self, ent_id): # pylint: disable=unused-argument
    return True


class TestTaskAPI(unittest.TestCase):

  def test_operators(self):
    # pylint: disable=unsupported-binary-operation,invalid-unary-operand-type

    mock_gs = MockGameState()
    test_ent = 1

    # AND (&), OR (|), NOT (~), IMPLY (>>)
    task1 = Success() & Failure() & Success()
    self.assertFalse(task1(mock_gs, test_ent))

    task2 = Success() | Failure() | Success()
    self.assertTrue(task2(mock_gs, test_ent))

    task3 = Success() &  ~ Failure() & Success()
    self.assertTrue(task3(mock_gs, test_ent))

    task4 = Success() >> Success()
    self.assertTrue(task4(mock_gs, test_ent))

    task5 = Success() >> ~ Success()
    self.assertFalse(task5(mock_gs, test_ent))

    task6 = (Failure() >> Failure()) & Success()
    self.assertTrue(task6(mock_gs, test_ent))

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

    team_helper = TeamHelper(list(range(1, config.PLAYER_N+1)), len(config.PLAYERS))

    # agents' population should match team_helper team id
    for ent_id, ent in env.realm.players.items():
      # pylint: disable=protected-access
      self.assertEqual(team_helper._ent_to_team[ent_id], ent.population)

  def test_team_assignment(self):
    task_force =  Team("Foo", [1, 2, 8, 9])

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

    rand_sampler.sample(max_clauses=4, max_clause_size=3, not_p=0.5)

  def test_default_sampler(self):
    pass

  def test_completed_tasks_in_info(self):
    config = ScriptedAgentTestConfig()
    env = TaskWrapper(config)

    # some team helper maybe necessary
    team_helper = TeamHelper( list(range(1, config.PLAYER_N+1)), len(config.PLAYERS))
    tasks = [
      Task( Success(), team_helper.all() ),
      Task( Failure(), team_helper.team(1) ),
      Task( FakeTask(1, Item.Ration, Action.Melee), team_helper.team(2) )
    ]

    env.reset(tasks)
    _, _, _, infos = env.step({})
    logging.info(infos)

    # agent 2 should have been assigned Success() and Failure() but not FakeTask()
    self.assertEqual(infos[2]['task'][Success().name], 1)
    self.assertEqual(infos[2]['task'][Failure().name], 0)
    self.assertTrue(FakeTask(1, Item.Ration, Action.Melee).name not in infos[2]['task'])

    # agent 3 should have been assigned FakeTask(), which is always False (0)
    self.assertEqual(infos[3]['task'][FakeTask(1, Item.Ration, Action.Melee).name], 0)


if __name__ == '__main__':
  unittest.main()
