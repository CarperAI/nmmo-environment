import unittest

# pylint: disable=import-error
from testhelpers import ScriptedAgentTestConfig
from scripted import baselines

from nmmo.task import task
import nmmo.task.base_predicate as predicate
from nmmo.entity.entity import EntityState
from nmmo.systems import item as Item
from nmmo.io import action as Action


class TestBasePredicate(unittest.TestCase):
  # pylint: disable=protected-access

  def _get_taskenv(self, test_tasks):
    config = ScriptedAgentTestConfig()

    # make two teams: team sleeper, team meander
    config.PLAYERS = [baselines.Sleeper, baselines.Meander]
    config.PLAYER_N = 6
    config.IMMORTAL = True

    team_helper = task.TeamHelper(list(range(1, config.PLAYER_N+1)), len(config.PLAYERS))
    missions = [ task.Mission(t, team_helper.all()) for t in test_tasks ]

    env = task.TaskWrapper(config)
    env.reset(missions)

    return env

  def test_live_long_team_size_ge(self):
    tick_success = 10
    team_size_ge = 2
    test_tasks = [predicate.LiveLong(tick_success), predicate.TeamSizeGE(team_size_ge)]

    env = self._get_taskenv(test_tasks)

    for _ in range(tick_success - 1):
      _, rewards, _, infos = env.step({})

    # Tick 9: no agent has lived 10 ticks, so LiveLong = False
    #   But no agent has died, so TeamSizeGE = True
    for ent_id in env.realm.players.spawned:
      self.assertEqual(rewards[ent_id], 1)
      self.assertEqual(infos[ent_id]['mission'][test_tasks[0].name], 0) # LiveLong
      self.assertEqual(infos[ent_id]['mission'][test_tasks[1].name], 1) # TeamSizeGE

    # kill agents 1-3
    death_note = [1, 2, 3]
    for ent_id in death_note:
      env.realm.players[ent_id].resources.health.update(0)
    env.obs = env._compute_observations()

    # 10th tick
    _, rewards, _, infos = env.step({})

    # those who lived has reached the goal
    entities = EntityState.Query.table(env.realm.datastore)
    entities = list(entities[:, EntityState.State.attr_name_to_col['id']]) # ent_ids

    for ent_id in env.realm.players.spawned:
      if ent_id in death_note:
        # make sure that dead players not in the realm nor the datastore
        self.assertTrue(ent_id not in env.realm.players)
        self.assertTrue(ent_id not in entities)

      elif env.realm.players[ent_id].population == 0: # team 0: only agent 5 is alive
        self.assertEqual(rewards[ent_id], 1)
        self.assertEqual(infos[ent_id]['mission'][test_tasks[0].name], 1) # LiveLong
        self.assertEqual(infos[ent_id]['mission'][test_tasks[1].name], 0) # TeamSizeGE

      else: # team 1: agents 4 and 6 are alive
        self.assertEqual(rewards[ent_id], 2)
        self.assertEqual(infos[ent_id]['mission'][test_tasks[0].name], 1) # LiveLong
        self.assertEqual(infos[ent_id]['mission'][test_tasks[1].name], 1) # TeamSizeGE

    # DONE

  def test_hoard_gold_and_team(self):
    agent_gold_goal = 10
    team_gold_goal = 30
    test_tasks = [predicate.HoardGold(agent_gold_goal), predicate.TeamHoardGold(team_gold_goal)]

    env = self._get_taskenv(test_tasks)

    # give gold to agents 1-3
    gold_struck = [1, 2, 3]
    for ent_id in gold_struck:
      env.realm.players[ent_id].gold.update(ent_id * 10)
    env.obs = env._compute_observations()

    _, rewards, _, infos = env.step({})

    for ent_id in env.realm.players:
      agent_success = int(ent_id in gold_struck)
      self.assertEqual(infos[ent_id]['mission'][test_tasks[0].name], agent_success) # HoardGold

      if env.realm.players[ent_id].population == 0: # team 0: team goal met 10 + 30 >= 30
        self.assertEqual(rewards[ent_id], 1 + agent_success) # team goal met
        self.assertEqual(infos[ent_id]['mission'][test_tasks[1].name], 1) # TeamHoardGold

      else: # team 1: team goal NOT met, 20 < 30
        self.assertEqual(infos[ent_id]['mission'][test_tasks[1].name], 0) # TeamHoardGold

    # DONE

  def _provide_item(self, realm, ent_id, item, level, quantity):
    if isinstance(item, Item.Stack):
      realm.players[ent_id].inventory.receive(
        item(realm, level=level, quantity=quantity))
    else:
      for _ in range(quantity):
        realm.players[ent_id].inventory.receive(
          item(realm, level=level))

  def test_own_equip_item(self):
    # ration, level 2, quantity 3 (non-stackable)
    # ammo level 2, quantity 3 (stackable, equipable)
    goal_level = 2
    goal_quantity = 3
    test_tasks = [predicate.OwnItem(Item.Ration, goal_level, goal_quantity),
                  predicate.OwnItem(Item.Scrap, goal_level, goal_quantity),
                  predicate.EquipItem(Item.Scrap, goal_level)]

    env = self._get_taskenv(test_tasks)

    # set the level, so that agents 4-6 can equip the scrap
    equip_scrap = [4, 5, 6]
    for ent_id in equip_scrap:
      env.realm.players[ent_id].skills.melee.level.update(6) # melee skill level=6

    # pylint: disable=multiple-statements
    # provide items
    ent_id = 1; self._provide_item(env.realm, ent_id, Item.Ration, level=1, quantity=4)
    ent_id = 2; self._provide_item(env.realm, ent_id, Item.Ration, level=4, quantity=1)
    ent_id = 3; self._provide_item(env.realm, ent_id, Item.Ration, level=3, quantity=3)
    ent_id = 4; self._provide_item(env.realm, ent_id, Item.Scrap, level=1, quantity=4)
    ent_id = 5; self._provide_item(env.realm, ent_id, Item.Scrap, level=4, quantity=1)

    # agent 6 equips the scrap to satisfy EquipItem task
    ent_id = 6; target_item = Item.Scrap(env.realm, level=2, quantity=4)
    env.realm.players[ent_id].inventory.receive(target_item)
    target_item.use(env.realm.players[ent_id])

    env.obs = env._compute_observations()

    _, rewards, _, infos = env.step({})

    for ent_id in env.realm.players:
      self.assertEqual(rewards[ent_id], int(ent_id in [3, 6]) + int(ent_id == 6))
      self.assertEqual(infos[ent_id]['mission'][test_tasks[0].name],
                       int(ent_id == 3)) # OwnItem: Ration, level=>2, quantity=>3
      self.assertEqual(infos[ent_id]['mission'][test_tasks[1].name],
                       int(ent_id == 6)) # OwnItem: Scrap, level=>2, quantity>=3
      self.assertEqual(infos[ent_id]['mission'][test_tasks[2].name],
                       int(ent_id == 6)) # EquipItem: Scrap, level>=2

    # DONE

  def test_team_fully_armed(self):
    goal_level = 5
    goal_agent = 2
    test_tasks = [predicate.TeamFullyArmed(Action.Range, goal_level, goal_agent)]

    env = self._get_taskenv(test_tasks)

    # fully equip agents 4-6
    fully_equip = [4, 5, 6]
    for ent_id in fully_equip:
      env.realm.players[ent_id].skills.range.level.update(goal_level+2)
      # prepare the items
      item_list = [ itm(env.realm, goal_level) for itm in [
        Item.Hat, Item.Top, Item.Bottom, Item.Bow, Item.Shaving]]
      for itm in item_list:
        env.realm.players[ent_id].inventory.receive(itm)
        itm.use(env.realm.players[ent_id])

    env.obs = env._compute_observations()

    _, rewards, _, infos = env.step({})

    for ent_id in env.realm.players:
      pop_id = (ent_id-1) % 2 # agents 2, 4, 6 in the team 1 -> goal satisfied
      self.assertEqual(rewards[ent_id], int(pop_id == 1))
      self.assertEqual(infos[ent_id]['mission'][test_tasks[0].name],
                       int(pop_id == 1))

    # DONE


if __name__ == '__main__':
  unittest.main()
