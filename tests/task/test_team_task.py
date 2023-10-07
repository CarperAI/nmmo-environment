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

  def test_sample_team_tasks(self):
    self.config.TEAM_TASK_EPISODE_PROB = 1  # always team-task episode
    env = nmmo.Env(self.config)
    env.reset()

    for task in env.tasks:
      self.assertEqual(task.reward_to, "team")  # all tasks are for teams
    self.assertEqual(env._provide_team_obs, True)

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


if __name__ == '__main__':
  unittest.main()
