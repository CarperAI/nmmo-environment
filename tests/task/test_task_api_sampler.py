import logging
import unittest

from tests.testhelpers import ScriptedAgentTestConfig

import nmmo

# pylint: disable=import-error
from nmmo.task import sampler
from nmmo.task.task_api import TaskWrapper
from nmmo.task.predicate import Group, TeamHelper, Predicate
from nmmo.task.game_state import GameState

from nmmo.systems import item as Item
from nmmo.io import action as Action


class Success(Predicate):
  def __call__(self, gs: GameState) -> bool:
    """Always true"""
    return True

class Failure(Predicate):
  def __call__(self, gs: GameState) -> bool:
    """Always false"""
    return False

class FakeTask(Predicate):
  def __init__(self, subject:Group, param1: int, param2: Item.Item, param3: Action.Style) -> None:
    super().__init__(subject, param1, param2, param3)
    self._param1 = param1
    self._param2 = param2
    self._param3 = param3

  def __call__(self, gs: GameState) -> bool:
    return False


class MockGameState(GameState):
  def __init__(self):
    # pylint: disable=super-init-not-called
    pass


class TestTaskAPI(unittest.TestCase):

  def test_operators(self):
    # pylint: disable=unsupported-binary-operation,invalid-unary-operand-type

    mock_gs = MockGameState()
    subject = Group([1])

    # AND (&), OR (|), NOT (~), IMPLY (>>)
    task1 = Success(subject) & Failure(subject) & Success(subject)
    self.assertFalse(task1(mock_gs))

    task2 = Success(subject) | Failure(subject) | Success(subject)
    self.assertTrue(task2(mock_gs))

    task3 = Success(subject) &  ~ Failure(subject) & Success(subject)
    self.assertTrue(task3(mock_gs))

    task4 = Success(subject) >> Success(subject)
    self.assertTrue(task4(mock_gs))

    task5 = Success(subject) >> ~ Success(subject)
    self.assertFalse(task5(mock_gs))

    task6 = (Failure(subject) >> Failure(subject)) & Success(subject)
    self.assertTrue(task6(mock_gs))

  def test_task_name(self):

    success = Success(Group([1]))
    failure = Failure(Group([1,3]))
    fake_task = FakeTask(Group([2]), 1, Item.Hat, Action.Melee)
    combination = (success & ~ (failure | fake_task)) | (failure >> fake_task)

    self.assertEqual(combination.name,
      "OR(AND(Success_Subject(1),NOT(OR(Failure_Subject(1,3),FakeTask_Subject(2)_1_Hat_Melee))),"
      "IMPLY(Failure_Subject(1,3)->FakeTask_Subject(2)_1_Hat_Melee))")

  def test_team_helper(self):
    # TODO(kywch): This test is true now but may change later.

    config = ScriptedAgentTestConfig()
    env = nmmo.Env(config)
    env.reset()

    team_helper = TeamHelper(list(range(1, config.PLAYER_N+1)), len(config.PLAYERS))

    # agents' population should match team_helper team id
    for ent_id, ent in env.realm.players.items():
      # pylint: disable=protected-access
      self.assertEqual(team_helper._ent_to_team[ent_id], ent.population)

  def test_team_assignment(self):
    team =  Group([1, 2, 8, 9], "TeamFoo")

    self.assertEqual(team.name, 'TeamFoo')
    self.assertEqual(team.member(2).name, "TeamFoo.2")
    self.assertEqual(team.member(2).agents, [8])

    # don't allow member of one-member team
    self.assertEqual(team.member(2).member(0).name, team.member(2).name)

  def test_random_task_sampler(self):
    rand_sampler = sampler.RandomTaskSampler()

    rand_sampler.add_task_spec(Success, [[Group([1]), Group([3])]])
    rand_sampler.add_task_spec(Failure, [[Group([2]), Group([1,3])]])
    rand_sampler.add_task_spec(FakeTask, [
      [Group([1]), Group([2]), Group([1,2]), Group([3]), Group([1,3])],
      [Item.Hat, Item.Top, Item.Bottom],
      [1, 5, 10],
      [0.1, 0.2, 0.3, 0.4]
    ])

    rand_sampler.sample(max_clauses=4, max_clause_size=3, not_p=0.5)

  # def test_default_sampler(self):
  #   pass

  def test_completed_tasks_in_info(self):
    config = ScriptedAgentTestConfig()
    env = TaskWrapper(config)

    # some team helper maybe necessary
    team_helper = TeamHelper( list(range(1, config.PLAYER_N+1)), len(config.PLAYERS))

    # TODO(kywch): It's very cumbersome to define task_assignment for each agent manually
    #   We probably need a function here...
    task1 = Success(Group([1]))
    task1_dup = Success(Group([1]))
    reward1 = 1
    fake_task = FakeTask(team_helper.left_team(3), Item.Hat, 1, 0.1)
    task_assignment = {
      1: [ (task1, reward1), (Failure(Group([2])), 2), (Success(Group([2])), -1) ],
      2: [ (Success(team_helper.own_team(2)), 1), (Failure(team_helper.own_team(1)), 2),
           (Success(team_helper.team(0)), -1) ],
      3: [ (fake_task, 2), (task1_dup, 2) ] # Success(Group([1])) is defined twice
    }

    env.reset(task_assignment)
    _, _, _, infos = env.step({})
    logging.info(infos)

    # agent 1: task1 is always True, so it should be rewarded too
    self.assertEqual(infos[1]['task'][task1.name], reward1)

    # agent 2 should have been assigned Success() and Failure() but not FakeTask()
    self.assertEqual(infos[2]['task'][Success(team_helper.own_team(2)).name], 1)
    self.assertEqual(infos[2]['task'][Failure(team_helper.own_team(1)).name], 0)
    self.assertTrue(fake_task.name not in infos[2]['task'])

    # agent 3 should have been assigned FakeTask(), which is always False (0)
    self.assertEqual(infos[3]['task'][fake_task.name], 0)

    # other agents don't have any tasks assigned
    for ent_id in range(4, config.PLAYER_N+1):
      self.assertEqual(infos[ent_id]['task'], {})


if __name__ == '__main__':
  unittest.main()
