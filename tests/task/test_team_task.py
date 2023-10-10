# pylint: disable=protected-access
import unittest

import nmmo
from nmmo.lib.team_helper import TeamHelper, TeamLoader


class TestTeamTask(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    num_teams = 16
    team_size = 8

    cls.config = nmmo.config.Small()
    cls.config.PLAYER_N = num_teams * team_size
    cls.config.TEAMS = {
      "Team" + str(i+1): [i*team_size+j+1 for j in range(team_size)]
      for i in range(num_teams)
    }
    cls.config.CURRICULUM_FILE_PATH = 'tests/task/sample_curriculum.pkl'

  def test_team_size(self):
    # raise error if PLAYER_N is not divisible by the number of teams
    self.config.PLAYER_N = 127
    self.assertRaises(AssertionError, lambda: self.config.TEAM_SIZE)

    self.config.PLAYER_N = 128
    self.assertEqual(self.config.PLAYER_N, self.config.TEAM_SIZE * len(self.config.TEAMS))
    # each team should have the same number of agents
    for team in self.config.TEAMS:
      self.assertEqual(self.config.TEAM_SIZE, len(self.config.TEAMS[team]))

  def test_team_spawn(self):
    self.config.PLAYER_LOADER = TeamLoader
    env = nmmo.Env(self.config)
    # To correctly spawn agents, config.TEAMS should contain all possible agents
    team_helper = TeamHelper(self.config.TEAMS)
    self.assertListEqual(env.possible_agents, list(team_helper.team_and_position_for_agent.keys()))

    # spawn agents
    env.reset()

    # agents in the same team should spawn together
    team_locs = {}
    for team_id, team_members in self.config.TEAMS.items():
      team_locs[team_id] = env.realm.players[team_members[0]].pos
      for agent_id in team_members:
        self.assertEqual(team_locs[team_id], env.realm.players[agent_id].pos)

    # teams should be apart from each other
    for team_a in self.config.TEAMS:
      for team_b in self.config.TEAMS:
        if team_a != team_b:
          self.assertNotEqual(team_locs[team_a], team_locs[team_b])

  def test_sample_agent_tasks(self):
    self.config.TEAM_TASK_EPISODE_PROB = 0  # always agent-task episode
    env = nmmo.Env(self.config)
    env.reset()

    for task in env.tasks:
      self.assertEqual(task.reward_to, "agent")  # all tasks are for agents
    self.assertEqual(env._provide_team_obs, False)

    # every agent is assigned a task
    self.assertEqual(len(env.possible_agents), len(env.tasks))
    # for the training tasks, the task assignee and subject should be the same
    for task in env.tasks:
      self.assertEqual(task.assignee, task.subject)

  def test_sample_team_training_tasks(self):
    self.config.TEAM_TASK_EPISODE_PROB = 1  # always team-task episode
    self.config.TEAM_BATTLE_EPISODE_PROB = 0  # no team competition
    env = nmmo.Env(self.config)
    env.reset()

    for task in env.tasks:
      self.assertEqual(task.reward_to, "team")  # all tasks are for teams
    self.assertEqual(env._provide_team_obs, True)

    # no competition mode
    self.assertEqual(env.team_battle_mode, False)
    self.assertEqual(env.battle_winners, None)

  def test_team_battle_mode(self):
    self.config.TEAM_TASK_EPISODE_PROB = 1  # always team-task episode
    self.config.TEAM_BATTLE_EPISODE_PROB = 1  # no team competition
    env = nmmo.Env(self.config)
    env.reset()

    # competition mode
    task_spec_name = env.tasks[0].spec_name
    for task in env.tasks:
      self.assertEqual(task.reward_to, "team")  # all tasks are for teams
      self.assertEqual(task.spec_name, task_spec_name)  # all tasks are the same in competition
    self.assertEqual(env._provide_team_obs, True)

    self.assertEqual(env.team_battle_mode, True)
    self.assertEqual(env.battle_winners, None)

  def test_competition_winner_one_team(self):
    self.config.TEAM_TASK_EPISODE_PROB = 1  # always team-task episode
    self.config.TEAM_BATTLE_EPISODE_PROB = 1  # no team competition
    env = nmmo.Env(self.config)
    env.reset()

    winner_team = "Team1"
    for team_id, members in env.config.TEAMS.items():
      if team_id != winner_team:
        for agent_id in members:
          env.realm.players[agent_id].resources.health.update(0)

    env.step({})
    self.assertEqual(env.battle_winners, env.config.TEAMS[winner_team])

  def test_competition_winner_task_completed(self):
    self.config.TEAM_TASK_EPISODE_PROB = 1  # always team-task episode
    self.config.TEAM_BATTLE_EPISODE_PROB = 1  # no team competition
    env = nmmo.Env(self.config)
    env.reset()

    # The first two tasks get completed
    winners = []
    for task in env.tasks[:2]:
      task._completed_tick = 1
      self.assertEqual(task.completed, True)
      winners += task.assignee

    env.step({})
    self.assertEqual(env.battle_winners, winners)

if __name__ == '__main__':
  unittest.main()
