import unittest

# pylint: disable=import-error
from testhelpers import ScriptedAgentTestConfig, provide_item
#from testhelpers import change_spawn_pos

from scripted import baselines

from nmmo.entity.entity import EntityState
from nmmo.systems import item as Item
from nmmo.systems import skill as Skill
from nmmo.lib import material as Material

from nmmo.task.task_api import Task, TaskWrapper, TeamHelper
import nmmo.task.base_predicate as bp
import nmmo.task.item_predicate as ip
import nmmo.task.gold_predicate as gp


# TODO: complete all tests and remove the below line
# pylint: disable=unnecessary-pass,unused-variable

class TestBasePredicate(unittest.TestCase):
  # pylint: disable=protected-access

  def _get_taskenv(self, test_tasks):
    config = ScriptedAgentTestConfig()

    # make two teams: team sleeper, team meander
    config.PLAYERS = [baselines.Sleeper, baselines.Meander]
    config.PLAYER_N = 6
    config.IMMORTAL = True

    team_helper = TeamHelper(list(range(1, config.PLAYER_N+1)), len(config.PLAYERS))
    tasks = [ Task(t, team_helper.all()) for t in test_tasks ]

    env = TaskWrapper(config)
    env.reset(tasks)

    return env

  def test_live_long_team_size_protect_timer(self):
    tick_success = 10
    team_size_ge = 2
    tick_timer = 9
    death_note = [1, 2, 3]
    test_tasks = [bp.LiveLong(tick_success), bp.TeamSizeGE(team_size_ge),
                  bp.ProtectAgent([3]), # 3 gets killed, so fail
                  bp.ProtectAgent([3, 4]), # 3 gets killed, so fail
                  bp.ProtectAgent([4]), # 4 is alive, so success
                  bp.Timer(tick_timer)]

    env = self._get_taskenv(test_tasks)

    for _ in range(tick_success - 1):
      _, rewards, _, infos = env.step({})

    # Tick 9: no agent has lived 10 ticks, so LiveLong = False
    #   But no agent has died, so TeamSizeGE = True
    for ent_id in env.realm.players.spawned:
      self.assertEqual(rewards[ent_id], 5)
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name], 0) # LiveLong
      self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], 1) # TeamSizeGE
      self.assertEqual(infos[ent_id]['task'][test_tasks[-1].name], 1) # Timer
      for tid in range(2, 5): # 3 ProtectAgent tasks -- all are alive
        self.assertEqual(infos[ent_id]['task'][test_tasks[tid].name], 1) # ProtectAgent

    # kill agents 1-3
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

      else:
        if env.realm.players[ent_id].population == 0: # team 0: only agent 5 is alive
          self.assertEqual(rewards[ent_id], 2)
          self.assertEqual(infos[ent_id]['task'][test_tasks[0].name], 1) # LiveLong
          self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], 0) # TeamSizeGE

        else: # team 1: agents 4 and 6 are alive
          self.assertEqual(rewards[ent_id], 3)
          self.assertEqual(infos[ent_id]['task'][test_tasks[0].name], 1) # LiveLong
          self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], 1) # TeamSizeGE

        # ProtectAgent tasks: team/self doesn't matter when evaluating
        self.assertEqual(infos[ent_id]['task'][test_tasks[2].name], 0) # 3 -> Fail
        self.assertEqual(infos[ent_id]['task'][test_tasks[3].name], 0) # 3,4 -> Fail
        self.assertEqual(infos[ent_id]['task'][test_tasks[4].name], 1) # 4 -> Success
        self.assertEqual(infos[ent_id]['task'][test_tasks[5].name], 0) # Timer -> Fail

    # DONE

  def test_search_tile_and_team(self): # SearchTile, TeamSearchTile
    agent_target = Material.Water
    team_target = Material.Forest
    test_tasks = [bp.SearchTile(agent_target), bp.TeamSearchTile(team_target)]

    env = self._get_taskenv(test_tasks)

    _, rewards, _, infos = env.step({})

    # The result of TeamSearchTile should be cached
    #   the below line access the results of team 0, TeamSearchTile (<- test_tasks[1])
    #  env.team_gs[0].cache_result[test_tasks[1].name]

    pass

  def test_search_agent_and_team(self): # SearchAgent, TeamSearchAgent
    search_target = 1
    test_tasks = [bp.SearchAgent(search_target), bp.TeamSearchAgent(search_target)]

    env = self._get_taskenv(test_tasks)

    # We may want to control the agent's location
    # to place one in and out of other visual field
    #   use change_spawn_pos to set the pos
    #   then run env.obs = env._compute_observations()

    _, rewards, _, infos = env.step({})

    # check the cached results of TeamSearchAgent

    pass

  def test_goto_tile_and_occupy(self): # GotoTile, TeamOccupyTile
    target_tile = (10, 10)
    test_tasks = [bp.GotoTile(*target_tile), bp.TeamOccupyTile(*target_tile)]

    env = self._get_taskenv(test_tasks)

    # use change_spawn_pos to create various success/failure conditions

    _, rewards, _, infos = env.step({})

    # check the cached results of TeamOccupyTile

    pass

  def test_travel_and_team(self): # GoDistance, TeamGoDistance
    agent_dist = 5
    team_dist = 10
    test_tasks = [bp.GoDistance(agent_dist), bp.TeamGoDistance(team_dist)]

    env = self._get_taskenv(test_tasks)

    # use change_spawn_pos to create various success/failure conditions

    _, rewards, _, infos = env.step({})

    # check the cached results of TeamGoDistance

    pass

  def test_stay_close_and_team(self): # StayCloseTo, TeamStayClose
    goal_dist = 5
    test_tasks = [bp.StayCloseTo(1, goal_dist), bp.TeamStayClose(goal_dist)]

    env = self._get_taskenv(test_tasks)

    # use change_spawn_pos to create various success/failure conditions

    _, rewards, _, infos = env.step({})

    # check the cached results of TeamStayClose

    pass

  def test_attain_skill_and_team(self): # AttainSkill, TeamAttainSkill
    goal_level = 5
    test_tasks = [bp.AttainSkill(Skill.Melee, goal_level),
                  bp.AttainSkill(Skill.Range, goal_level),
                  bp.TeamAttainSkill(Skill.Fishing, goal_level, 1),
                  bp.TeamAttainSkill(Skill.Carving, goal_level, 2)]

    env = self._get_taskenv(test_tasks)

    # update skill level, like:
    #   env.realm.players[ent_id].skills.range.level.update()
    #  then env.obs = env._compute_observations()

    _, rewards, _, infos = env.step({})

    # check the cached results of TeamAttainSkill

    pass


  def test_destroy_agent_and_eliminate(self): # DestroyAgent, EliminateFoe
    # CHECK ME: To properly test this, we may need 3 teams

    target_agents = [1]
    target_teams = [-3, 1] # npcs pop: -1,-2,-3
    test_tasks = [bp.DestroyAgent([]), # empty agents should always fail
                  bp.DestroyAgent(target_agents),
                  bp.EliminateFoe(target_teams),
                  bp.EliminateFoe()] # empty teams become Eliminate all foes

    env = self._get_taskenv(test_tasks)

    _, rewards, _, infos = env.step({})

    # check the cached results of DestroyAgent, EliminateFoe

    pass

  def test_inventory_space_lt_not(self): # InventorySpaceLT
    # also test NOT InventorySpaceLT
    target_space = 3
    test_tasks = [ip.InventorySpaceLT(target_space),
                  ~ip.InventorySpaceLT(target_space)]

    env = self._get_taskenv(test_tasks)

    _, rewards, _, infos = env.step({})

    pass


  def test_own_equip_item_team(self): # OwnItem, EquipItem, TeamOwnItem
    # ration, level 2, quantity 3 (non-stackable)
    # ammo level 2, quantity 3 (stackable, equipable)
    goal_level = 2
    goal_quantity = 3
    team_quantity = 5
    test_tasks = [ip.OwnItem(Item.Ration, goal_level, goal_quantity),
                  ip.OwnItem(Item.Scrap, goal_level, goal_quantity),
                  ip.EquipItem(Item.Scrap, goal_level),
                  ip.TeamOwnItem(Item.Ration, quantity=team_quantity),
                  ip.TeamOwnItem(Item.Scrap, level=1, quantity=5)]

    env = self._get_taskenv(test_tasks)

    # set the level, so that agents 4-6 can equip the scrap
    equip_scrap = [4, 5, 6]
    for ent_id in equip_scrap:
      env.realm.players[ent_id].skills.melee.level.update(6) # melee skill level=6

    # pylint: disable=multiple-statements
    # provide items
    ent_id = 1; provide_item(env.realm, ent_id, Item.Ration, level=1, quantity=4)
    ent_id = 2; provide_item(env.realm, ent_id, Item.Ration, level=4, quantity=1)
    ent_id = 3; provide_item(env.realm, ent_id, Item.Ration, level=3, quantity=3)
    ent_id = 4; provide_item(env.realm, ent_id, Item.Scrap, level=1, quantity=4)
    ent_id = 5; provide_item(env.realm, ent_id, Item.Scrap, level=4, quantity=1)

    # agent 6 equips the scrap to satisfy EquipItem task
    ent_id = 6; target_item = Item.Scrap(env.realm, level=2, quantity=4)
    env.realm.players[ent_id].inventory.receive(target_item)
    target_item.use(env.realm.players[ent_id])

    env.obs = env._compute_observations()

    _, rewards, _, infos = env.step({})

    for ent_id in env.realm.players:
      self.assertEqual(rewards[ent_id], int(ent_id in [3, 6]) + int(ent_id == 6) + 1)
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name],
                       int(ent_id == 3)) # OwnItem: Ration, level=>2, quantity=>3
      self.assertEqual(infos[ent_id]['task'][test_tasks[1].name],
                       int(ent_id == 6)) # OwnItem: Scrap, level=>2, quantity>=3
      self.assertEqual(infos[ent_id]['task'][test_tasks[2].name],
                       int(ent_id == 6)) # EquipItem: Scrap, level>=2
      self.assertEqual(infos[ent_id]['task'][test_tasks[3].name],
                       int(ent_id in [1, 3, 5])) # TeamOwnItem: Ration, any lvl, q>=5
      self.assertEqual(infos[ent_id]['task'][test_tasks[4].name],
                       int(ent_id in [2, 4, 6])) # TeamOwnItem: Scrap, lvl>=1, q>=5

    # DONE

  def test_team_fully_armed(self):
    goal_level = 5
    goal_agent = 2
    test_tasks = [ip.TeamFullyArmed(Skill.Range, goal_level, goal_agent)]

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
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name],
                       int(pop_id == 1))

    # DONE


  def test_hoard_gold_and_team(self): # HoardGold, TeamHoardGold
    agent_gold_goal = 10
    team_gold_goal = 30
    test_tasks = [gp.HoardGold(agent_gold_goal), gp.TeamHoardGold(team_gold_goal)]

    env = self._get_taskenv(test_tasks)

    # give gold to agents 1-3
    gold_struck = [1, 2, 3]
    for ent_id in gold_struck:
      env.realm.players[ent_id].gold.update(ent_id * 10)
    env.obs = env._compute_observations()

    _, rewards, _, infos = env.step({})

    for ent_id in env.realm.players:
      agent_success = int(ent_id in gold_struck)
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name], agent_success) # HoardGold

      if env.realm.players[ent_id].population == 0: # team 0: team goal met 10 + 30 >= 30
        self.assertEqual(rewards[ent_id], 1 + agent_success) # team goal met
        self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], 1) # TeamHoardGold

      else: # team 1: team goal NOT met, 20 < 30
        self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], 0) # TeamHoardGold

    # DONE


if __name__ == '__main__':
  unittest.main()
