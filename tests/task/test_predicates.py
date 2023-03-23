import unittest

from tests.testhelpers import ScriptedAgentTestConfig, provide_item, change_spawn_pos

from scripted.baselines import Sleeper

from nmmo.entity.entity import EntityState
from nmmo.systems import item as Item
from nmmo.systems import skill as Skill
from nmmo.lib import material as Material

# pylint: disable=import-error
from nmmo.task.task_api import Task, TaskWrapper, TeamHelper
import nmmo.task.base_predicate as bp
import nmmo.task.item_predicate as ip
import nmmo.task.gold_predicate as gp

class TestBasePredicate(unittest.TestCase):
  # pylint: disable=protected-access,invalid-name

  def _get_taskenv(self,
                   test_tasks,
                   agents=[Sleeper, Sleeper],
                   grass_map=False):

    config = ScriptedAgentTestConfig()

    # two Sleeper teams, 3 agents each by default
    config.PLAYERS = agents
    config.PLAYER_N = 6
    config.IMMORTAL = True

    team_helper = TeamHelper(list(range(1, config.PLAYER_N+1)), len(config.PLAYERS))
    tasks = [ Task(t, team_helper.all()) for t in test_tasks ]

    env = TaskWrapper(config)
    env.reset(tasks)

    if grass_map:
      MS = env.config.MAP_SIZE
      # Change entire map to grass to become habitable
      for i in range(MS):
        for j in range(MS):
          tile = env.realm.map.tiles[i,j]
          tile.material = Material.Grass
          tile.material_id.update(2)
          tile.state = Material.Grass(env.config)

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
    agent_target = Material.Forest
    team_target = Material.Water
    test_tasks = [bp.SearchTile(agent_target), bp.TeamSearchTile(team_target)]

    # setup env with all grass map
    env = self._get_taskenv(test_tasks, grass_map=True)

    # Two corners to the target materials
    MS = env.config.MAP_SIZE
    tile = env.realm.map.tiles[0,MS-2]
    tile.material = Material.Forest
    tile.material_id.update(4)

    tile = env.realm.map.tiles[MS-1,0]
    tile.material = Material.Water
    tile.material_id.update(1)

    # All agents to one corner
    for ent_id in env.realm.players:
      change_spawn_pos(env.realm,ent_id,(0,0))

    # Team one to forest, team two to water
    change_spawn_pos(env.realm,1,(0,MS-2)) # agent 1, team 0, forest
    change_spawn_pos(env.realm,2,(MS-2,0)) # agent 2, team 1, water

    env.obs = env._compute_observations()
    _, _, _, infos = env.step({})

    for ent_id in env.realm.players:
      team_id = infos[ent_id]['population']
      # SearchTile_Forest: True for agent 1 only
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name], int(ent_id == 1))
      # TeamSearchTile_Water: True for team 1
      self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], int(team_id == 1))
      # TeamSearchTile_Water: check cached results
      self.assertEqual(env.team_gs[team_id].cache_result[test_tasks[1].name], team_id == 1)

    # DONE

  def test_search_agent_and_team(self): # SearchAgent, TeamSearchAgent
    search_target = 1
    test_tasks = [bp.SearchAgent(search_target), bp.TeamSearchAgent(search_target)]

    agents = [Sleeper, Sleeper, Sleeper] # need 3 teams
    env = self._get_taskenv(test_tasks, agents=agents, grass_map=True)

    # All agents to one corner
    for ent_id in env.realm.players:
      change_spawn_pos(env.realm,ent_id,(0,0))

    # Teleport agents 1 and 2 to the same tile in the opposite corner
    MS = env.config.MAP_SIZE
    change_spawn_pos(env.realm,1,(MS-2,MS-2))
    change_spawn_pos(env.realm,2,(MS-2,MS-2))

    env.obs = env._compute_observations()
    _, _, _, infos = env.step({})

    for ent_id in env.realm.players:
      team_id = infos[ent_id]['population']
      # SearchAgent_1: True for agents 1 and 2, false for others
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name], int(ent_id in [1,2]))
      # TeamSearchAgent_1 : True for team 0 (a1, a4) and team 1 (a2, a5)
      self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], int(team_id in [0,1]))
      # TeamSearchAgent_1: check cached results
      self.assertEqual(env.team_gs[team_id].cache_result[test_tasks[1].name], team_id in [0,1])

    # DONE

  def test_goto_tile_and_occupy(self): # GotoTile, TeamOccupyTile
    target_tile = (30, 30)
    test_tasks = [bp.GotoTile(*target_tile), bp.TeamOccupyTile(*target_tile)]

    # make all tiles habitable
    env = self._get_taskenv(test_tasks, grass_map=True)

    # All agents to one corner
    for ent_id in env.realm.players:
      change_spawn_pos(env.realm,ent_id,(0,0))

    change_spawn_pos(env.realm,1,target_tile)
    change_spawn_pos(env.realm,2,(target_tile[0],target_tile[1]-1))

    _, _, _, infos = env.step({})

    for ent_id in env.realm.players:
      team_id = infos[ent_id]['population']
      # GotoTile_30_30: True for agent 1 only
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name], int(ent_id == 1))
      # TeamOccupyTile_30_30: True for team 0
      self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], int(team_id == 0))
      # TeamOccupyTile_30_30: check cached results
      self.assertEqual(env.team_gs[team_id].cache_result[test_tasks[1].name], team_id == 0)

    # DONE

  def test_travel_and_team(self): # GoDistance, TeamGoDistance
    agent_dist = 5
    team_dist = 10
    test_tasks = [bp.GoDistance(agent_dist), bp.TeamGoDistance(team_dist)]

    # since moving agents to places, all tile must be habitable
    env = self._get_taskenv(test_tasks, grass_map=True)

    _, _, _, infos = env.step({})
    
    # one cannot accomplish these goals in the first tick
    for ent_id in env.realm.players:
      for task in test_tasks:
        self.assertEqual(infos[ent_id]['task'][task.name], 0)
    for team_id in [0, 1]:
      self.assertEqual(env.team_gs[team_id].cache_result[test_tasks[1].name], False)

    # Move a bit away
    travel_agent = 1
    spawn_pos = (env.realm.players[travel_agent].row.val, 
                 env.realm.players[travel_agent].col.val)
    change_spawn_pos(env.realm, travel_agent, (spawn_pos[0]+5,spawn_pos[1]+6))

    _,_,_, infos = env.step({})

    # agent 1 moved more than 5, so success
    for ent_id in env.realm.players:
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name], int(ent_id == 1))
      # all should fail TeamGoDistance_10 
      self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], 0)
    for team_id in [0, 1]:
      self.assertEqual(env.team_gs[team_id].cache_result[test_tasks[1].name], False)

    # Move far away
    change_spawn_pos(env.realm, travel_agent, (spawn_pos[0],spawn_pos[1]+10))
    _,_,_, infos = env.step({})

    # agent 1 moved more than 10, so TeamGoDistance_10 is also success for team 0 
    for ent_id in env.realm.players:
      team_id = infos[ent_id]['population']
      # GoDistance_5 is true for agent 1 only
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name], int(ent_id == 1))
      # TeamGoDistance_10 is also success for team 0 
      self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], int(team_id == 0))
      # TeamGoDistance_10: check cache
      self.assertEqual(env.team_gs[team_id].cache_result[test_tasks[1].name], team_id == 0)

    # DONE

  def test_stay_close_and_team(self): # StayCloseTo, TeamStayClose
    agent_target = 1
    goal_dist = 1
    team_dist = 5
    test_tasks = [bp.StayCloseTo(agent_target, goal_dist), bp.TeamStayClose(team_dist)]

    # since moving agents to places, all tile must be habitable
    env = self._get_taskenv(test_tasks, grass_map=True)

    MS = env.config.MAP_SIZE

    # team 0: staying within goal_dist
    change_spawn_pos(env.realm, 1, (MS//2, MS//2))
    change_spawn_pos(env.realm, 3, (MS//2-1, MS//2)) # also StayCloseTo a1 = True
    change_spawn_pos(env.realm, 5, (MS//2-5, MS//2))

    # team 1: staying goal_dist+1 apart
    change_spawn_pos(env.realm, 2, (MS//2+1, MS//2)) # also StayCloseTo a1 = True
    change_spawn_pos(env.realm, 4, (MS//2+5, MS//2))
    change_spawn_pos(env.realm, 6, (MS//2+8, MS//2))

    _, _, _, infos = env.step({})

    for ent_id in env.realm.players:
      team_id = infos[ent_id]['population']
      # StayCloseTo_1_1 is True for agents 1, 2, 3
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name], int(ent_id in [1, 2, 3]))
      # TeamStayClose_5 is success for team 0
      self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], int(team_id == 0))
      # TeamStayClose_5: check cache
      self.assertEqual(env.team_gs[team_id].cache_result[test_tasks[1].name], team_id == 0)

    # DONE

  def test_attain_skill_and_team(self): # AttainSkill, TeamAttainSkill
    goal_level = 5
    test_tasks = [bp.AttainSkill(Skill.Melee, goal_level),
                  bp.AttainSkill(Skill.Range, goal_level),
                  bp.TeamAttainSkill(Skill.Fishing, goal_level, 1),
                  bp.TeamAttainSkill(Skill.Carving, goal_level, 2)]

    env = self._get_taskenv(test_tasks)

    # satisfy AttainSkill_Range_5 for a1, TeamAttainSkill_Fishing_5_1 for team 0
    env.realm.players[1].skills.melee.level.update(goal_level-1)
    env.realm.players[1].skills.range.level.update(goal_level)
    env.realm.players[1].skills.fishing.level.update(goal_level)
    env.realm.players[1].skills.carving.level.update(goal_level)
    # satisfy TeamAttainSkill_Carving_5_2 for team 1
    env.realm.players[2].skills.carving.level.update(goal_level)
    env.realm.players[4].skills.carving.level.update(goal_level+2)
    env.obs = env._compute_observations()

    _, _, _, infos = env.step({})

    for ent_id in env.realm.players:
      team_id = infos[ent_id]['population']
      # AttainSkill_Melee_5 is false for all
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name], 0)
      # AttainSkill_Range_5 is true for agent 1 only
      self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], int(ent_id == 1))
      # TeamAttainSkill_Fishing_5_1 is true for team 0
      self.assertEqual(infos[ent_id]['task'][test_tasks[2].name], int(team_id == 0))
      # TeamAttainSkill_Fishing_5_1: cache check
      self.assertEqual(env.team_gs[team_id].cache_result[test_tasks[2].name], team_id == 0)
      # TeamAttainSkill_Carving_5_2 is true for team 1
      self.assertEqual(infos[ent_id]['task'][test_tasks[3].name], team_id == 1)
      # TeamAttainSkill_Carving_5_2: check cache
      self.assertEqual(env.team_gs[team_id].cache_result[test_tasks[3].name], team_id == 1)

    # DONE

  def test_destroy_agent_and_eliminate(self): # DestroyAgent, EliminateFoe
    target_agents = [1]
    target_teams = [-3, 1] # npcs pop: -1,-2,-3
    test_tasks = [bp.DestroyAgent([]), # empty agents should always fail
                  bp.DestroyAgent(target_agents),
                  bp.EliminateFoe(target_teams),
                  bp.EliminateFoe()] # empty teams become Eliminate all foes

    agents = [Sleeper, Sleeper, Sleeper] # make three teams
    env = self._get_taskenv(test_tasks, agents=agents)

    _, reward, _, infos = env.step({})

    # all alive & no goal has been reached, so reward = 0 for all
    for ent_id in env.realm.players:
      self.assertEqual(reward[ent_id], 0)

    env.realm.players[1].resources.health.update(0) # kill agent
    
    _, _, _, infos = env.step({})

    for ent_id in env.realm.players:
      # DestroyAgent_[1] is True for all
      self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], 1)
      # other tasks are false for all
      for tid in [0, 2, 3]:
        self.assertEqual(infos[ent_id]['task'][test_tasks[tid].name], 0)

    # kill entire first team and npcs
    for player in env.realm.players.values():
      if player.population == 1: # team 1 only
        player.resources.health.update(0)
    for npc in env.realm.npcs.values():
      if npc.population == -3: # team -3 only
        npc.resources.health.update(0)

    _, _, _, infos = env.step({})

    for ent_id in env.realm.players:
      # DestroyAgent_[] is False for all remaining
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name], 0)
      # DestroyAgent_[1] is True for all
      self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], 1)
      # EliminateFoe_[-3,1] is True for all
      self.assertEqual(infos[ent_id]['task'][test_tasks[2].name], 1)
      # EliminateFoe_Any is False because two teams remain
      self.assertEqual(infos[ent_id]['task'][test_tasks[3].name], 0)

    # kill agent 4 and eliminate team 0
    env.realm.players[4].resources.health.update(0)

    _, _, _, infos = env.step({})

    for ent_id in env.realm.players:
      # the same as before
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name],0)
      self.assertEqual(infos[ent_id]['task'][test_tasks[1].name],1)
      self.assertEqual(infos[ent_id]['task'][test_tasks[2].name],1)
      # only team-2 reamins, so success
      self.assertEqual(infos[ent_id]['task'][test_tasks[3].name],1)

    # DONE

  def test_inventory_space_lt_not(self): # InventorySpaceGE
    # also test NOT InventorySpaceGE
    target_space = 3
    test_tasks = [ip.InventorySpaceGE(target_space),
                  ~ip.InventorySpaceGE(target_space)]

    env = self._get_taskenv(test_tasks)

    capacity = env.realm.players[1].inventory.capacity
    provide_item(env.realm, 1, Item.Ration, level=1, quantity=capacity-target_space)
    _, _, _, infos = env.step({})
    assert env.realm.players[1].inventory.space >= target_space
    self.assertEqual(infos[1]['task'][test_tasks[0].name],1) # 9 rations, 3 space, True
    self.assertEqual(infos[1]['task'][test_tasks[1].name],0)

    provide_item(env.realm, 1, Item.Ration, level=1, quantity=1)
    _, _, _, infos = env.step({})
    assert env.realm.players[1].inventory.space < target_space
    self.assertEqual(infos[1]['task'][test_tasks[0].name],0) # 10 rations, 2 space, False
    self.assertEqual(infos[1]['task'][test_tasks[1].name],1)

    # DONE

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
      team_id = infos[ent_id]['population']
      self.assertEqual(rewards[ent_id], int(ent_id in [3, 6]) + int(ent_id == 6) + 1)
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name],
                       int(ent_id == 3)) # OwnItem: Ration, level=>2, quantity=>3
      self.assertEqual(infos[ent_id]['task'][test_tasks[1].name],
                       int(ent_id == 6)) # OwnItem: Scrap, level=>2, quantity>=3
      self.assertEqual(infos[ent_id]['task'][test_tasks[2].name],
                       int(ent_id == 6)) # EquipItem: Scrap, level>=2
      # TeamOwnItem: Ration, any lvl, q>=5, True for team 0
      self.assertEqual(infos[ent_id]['task'][test_tasks[3].name], int(team_id == 0))
      self.assertEqual(env.team_gs[team_id].cache_result[test_tasks[3].name], team_id == 0)
      # TeamOwnItem: Scrap, lvl>=1, q>=5, True for team 1
      self.assertEqual(infos[ent_id]['task'][test_tasks[4].name], int(team_id == 1)) 
      self.assertEqual(env.team_gs[team_id].cache_result[test_tasks[4].name], team_id == 1)

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
      team_id = infos[ent_id]['population']
      # team 1 (a2, a4, a6) satisfied the goal
      self.assertEqual(rewards[ent_id], int(team_id == 1))
      self.assertEqual(infos[ent_id]['task'][test_tasks[0].name], int(team_id == 1))
      self.assertEqual(env.team_gs[team_id].cache_result[test_tasks[0].name], team_id == 1)

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

      if infos[ent_id]['population'] == 0: # team 0: team goal met 10 + 30 >= 30
        self.assertEqual(rewards[ent_id], 1 + agent_success) # team goal met
        self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], 1) # TeamHoardGold

      else: # team 1: team goal NOT met, 20 < 30
        self.assertEqual(infos[ent_id]['task'][test_tasks[1].name], 0) # TeamHoardGold

    # DONE


if __name__ == '__main__':
  unittest.main()
