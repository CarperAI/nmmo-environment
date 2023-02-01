# pylint: disable=all

# TODO: This test is currently broken. It needs to be fixed.

# from pdb import set_trace as T
# import unittest
# from tqdm import tqdm
# import numpy as np
# import random

# import nmmo

# from scripted import baselines

# from testhelpers import TestEnv, TestConfig, serialize_actions, are_observations_equal

# # 30 seems to be enough to test variety of agent actions
# TEST_HORIZON = 30
# RANDOM_SEED = random.randint(0, 10000)

# def serialize_actions(realm, actions, debug=True):
#     atn_copy = {}
#     for ent_id in list(actions.keys()):
#         if ent_id not in realm.players:
#             if debug:
#                 print("invalid player id", ent_id)
#             continue

#         ent = realm.players[ent_id]

#         atn_copy[ent_id] = {}
#         for atn, args in actions[ent_id].items():
#             atn_copy[ent_id][atn] = {}
#             drop = False
#             for arg, val in args.items():
#                 if arg.argType == nmmo.action.Fixed:
#                     atn_copy[ent_id][atn][arg] = arg.edges.index(val)
#                 elif arg == nmmo.action.Target:
#                     if val.ent_id not in ent.targets:
#                         if debug:
#                             print("invalid target", ent_id, ent.targets, val.ent_id)
#                         drop = True
#                         continue
#                     atn_copy[ent_id][atn][arg] = ent.targets.index(val.ent_id)
#                 elif atn in (nmmo.action.Sell, nmmo.action.Use, nmmo.action.Give) and arg == nmmo.action.Item:
#                     if val not in ent.inventory._item_references:
#                         if debug:
#                             itm_list = [type(itm) for itm in ent.inventory._item_references]
#                             print("invalid item to sell/use/give", ent_id, itm_list, type(val))
#                         drop = True
#                         continue
#                     if type(val) == nmmo.systems.item.Gold:
#                         if debug:
#                             print("cannot sell/use/give gold", ent_id, itm_list, type(val))
#                         drop = True
#                         continue
#                     atn_copy[ent_id][atn][arg] = [e for e in ent.inventory._item_references].index(val)
#                 elif atn == nmmo.action.Buy and arg == nmmo.action.Item:
#                     if val not in realm.exchange.listings:
#                     if val not in realm.exchange.listings:
#                         if debug:
#                             itm_list = [type(itm) for itm in realm.exchange.listings]
#                             itm_list = [type(itm) for itm in realm.exchange.listings]
#                             print("invalid item to buy (not listed in the exchange)", itm_list, type(val))
#                         drop = True
#                         continue
#                     atn_copy[ent_id][atn][arg] = realm.exchange.listings.index(val)
#                     atn_copy[ent_id][atn][arg] = realm.exchange.listings.index(val)
#                 else:
#                     # scripted ais have not bought any stuff
#                     assert False, f'Argument {arg} invalid for action {atn}'

#             # Cull actions with bad args
#             if drop and atn in atn_copy[ent_id]:
#                 del atn_copy[ent_id][atn]

#     return atn_copy

# # this function can be replaced by assertDictEqual
# # but might be still useful for debugging
# def are_actions_equal(source_atn, target_atn, debug=True):

#     # compare the numbers and player ids
#     player_src = list(source_atn.keys())
#     player_tgt = list(target_atn.keys())
#     if player_src != player_tgt:
#         if debug:
#             print("players don't match")
#         return False

#     # for each player, compare the actions
#     for ent_id in player_src:
#         atn1 = source_atn[ent_id]
#         atn2 = target_atn[ent_id]

#         if list(atn1.keys()) != list(atn2.keys()):
#             if debug:
#                 print("action keys don't match. player:", ent_id)
#             return False

#         for atn, args in atn1.items():
#             if atn2[atn] != args:
#                 if debug:
#                     print("action args don't match. player:", ent_id, ", action:", atn)
#                 return False

#     return True

# # this function CANNOT be replaced by assertDictEqual
# def are_observations_equal(source_obs, target_obs, debug=True):

#     keys_src = list(source_obs.keys())
#     keys_obs = list(target_obs.keys())
#     if keys_src != keys_obs:
#         if debug:
#             print("observation keys don't match")
#         return False

#     for k in keys_src:
#         ent_src = source_obs[k]
#         ent_tgt = target_obs[k]
#         if list(ent_src.keys()) != list(ent_tgt.keys()):
#             if debug:
#                 print("entities don't match. key:", k)
#             return False

#         obj = ent_src.keys()
#         for o in obj:
#             obj_src = ent_src[o]
#             obj_tgt = ent_tgt[o]
#             if list(obj_src) != list(obj_tgt):
#                 if debug:
#                     print("objects don't match. key:", k, ', obj:', o)
#                 return False

#             attrs = list(obj_src)
#             for a in attrs:
#                 attr_src = obj_src[a]
#                 attr_tgt = obj_tgt[a]

#                 if np.sum(attr_src != attr_tgt) > 0:
#                     if debug:
#                         print("attributes don't match. key:", k, ', obj:', o, ', attr:', a)
#                     return False

#     return True


# class TestEnv(nmmo.Env):
#     '''
#         EnvTest step() bypasses some differential treatments for scripted agents
#         To do so, actions of scripted must be serialized using the serialize_actions function above
#     '''
#     __test__ = False

#     def __init__(self, config=None, seed=None):
#         assert config.EMULATE_FLAT_OBS == False, 'EMULATE_FLAT_OBS must be FALSE'
#         assert config.EMULATE_FLAT_ATN == False, 'EMULATE_FLAT_ATN must be FALSE'
#         super().__init__(config, seed)

#     def step(self, actions):
#         assert self.initialized, 'step before reset'

#         # if actions are empty, then skip below to proceed with self.actions
#         # if actions are provided,
#         #   forget self.actions and preprocess the provided actions
#         if actions != {}:
#             self.actions = {}
#             for ent_id in list(actions.keys()):
#                 if ent_id not in self.realm.players:
#                     continue

#                 ent = self.realm.players[ent_id]

#                 if not ent.alive:
#                     continue

#                 self.actions[ent_id] = {}
#                 for atn, args in actions[ent_id].items():
#                     self.actions[ent_id][atn] = {}
#                     drop = False
#                     for arg, val in args.items():
#                         if arg.argType == nmmo.action.Fixed:
#                             self.actions[ent_id][atn][arg] = arg.edges[val]
#                         elif arg == nmmo.action.Target:
#                             if val >= len(ent.targets):
#                                 drop = True
#                                 continue
#                             targ = ent.targets[val]
#                             self.actions[ent_id][atn][arg] = self.realm.entity(targ)
#                         elif atn in (nmmo.action.Sell, nmmo.action.Use, nmmo.action.Give) and arg == nmmo.action.Item:
#                             if val >= len(ent.inventory.items):
#                                 drop = True
#                                 continue
#                             itm = [e for e in ent.inventory.items][val]
#                             if type(itm) == nmmo.systems.item.Gold:
#                                 drop = True
#                                 continue
#                             self.actions[ent_id][atn][arg] = itm
#                         elif atn == nmmo.action.Buy and arg == nmmo.action.Item:
#                             if val >= len(self.realm.exchange.item_listings):
#                             if val >= len(self.realm.exchange.item_listings):
#                                 drop = True
#                                 continue
#                             itm = self.realm.exchange.dataframeVals[val]
#                             self.actions[ent_id][atn][arg] = itm
#                         elif __debug__: #Fix -inf in classifier and assert err on bad atns
#                             assert False, f'Argument {arg} invalid for action {atn}'

#                     # Cull actions with bad args
#                     if drop and atn in self.actions[ent_id]:
#                         del self.actions[ent_id][atn]

#         #Step: Realm, Observations, Logs
#         self.dead    = self.realm.step(self.actions)
#         self.actions = {}
#         self.obs     = {}
#         infos        = {}

#         obs, rewards, dones, self.raw = {}, {}, {}, {}
#         for ent_id, ent in self.realm.players.items():
#             ob = self.realm.datastore.observations([ent])
#             self.obs[ent_id] = ob

#             # Generate decisions of scripted agents and save these to self.actions
#             if ent.agent.scripted:
#                 atns = ent.agent(ob[ent_id])
#                 for atn, args in atns.items():
#                     for arg, val in args.items():
#                         atns[atn][arg] = arg.deserialize(self.realm, ent, val)
#                 self.actions[ent_id] = atns

#             # also, return below for the scripted agents
#             obs[ent_id]     = ob
#             rewards[ent_id], infos[ent_id] = self.reward(ent)
#             dones[ent_id]   = False

#         self.log_env()
#         for ent_id, ent in self.dead.items():
#             self.log_player(ent)

#         self.realm.exchange.step()

#         for ent_id, ent in self.dead.items():
#             #if ent.agent.scripted:
#             #    continue
#             rewards[ent.ent_id], infos[ent.ent_id] = self.reward(ent)

#             dones[ent.ent_id] = False #TODO: Is this correct behavior?

#             #obs[ent.ent_id]     = self.dummy_ob

#         #Pettingzoo API
#         self.agents = list(self.realm.players.keys())

#         self.obs = obs
#         return obs, rewards, dones, infos


# class TestConfig(nmmo.config.Small, nmmo.config.AllGameSystems):

#     __test__ = False

#     RENDER = False
#     SPECIALIZE = True
#     PLAYERS = [
#             baselines.Fisher, baselines.Herbalist, baselines.Prospector, baselines.Carver, baselines.Alchemist,
#             baselines.Melee, baselines.Range, baselines.Mage]


# class TestDeterminism(unittest.TestCase):
#     @classmethod
#     def setUpClass(cls):
#         cls.horizon = TEST_HORIZON
#         cls.rand_seed = RANDOM_SEED
#         cls.config = TestConfig()

#         print('[TestDeterminism] Setting up the reference env with seed', cls.rand_seed)
#         env_src = TestEnv(cls.config, seed=cls.rand_seed)
#         actions_src = []
#         cls.init_obs_src = env_src.reset()
#         print('Running', cls.horizon, 'tikcs')
#         for t in tqdm(range(cls.horizon)):
#             actions_src.append(serialize_actions(env_src, env_src.actions))
#             nxt_obs_src, _, _, _ = env_src.step({})
#         cls.final_obs_src = nxt_obs_src
#         cls.actions_src = actions_src
#         npcs_src = {}
#         for nid, npc in list(env_src.realm.npcs.items()):
#             npcs_src[nid] = npc.packet()
#             del npcs_src[nid]['alive'] # to use the same 'are_observations_equal' function
#         cls.final_npcs_src = npcs_src

#         print('[TestDeterminism] Setting up the replication env with seed', cls.rand_seed)
#         env_rep = TestEnv(cls.config, seed=cls.rand_seed)
#         actions_rep = []
#         cls.init_obs_rep = env_rep.reset()
#         print('Running', cls.horizon, 'tikcs')
#         for t in tqdm(range(cls.horizon)):
#             actions_rep.append(serialize_actions(env_rep, env_rep.actions))
#             nxt_obs_rep, _, _, _ = env_rep.step({})
#         cls.final_obs_rep = nxt_obs_rep
#         cls.actions_rep = actions_rep
#         npcs_rep = {}
#         for nid, npc in list(env_rep.realm.npcs.items()):
#             npcs_rep[nid] = npc.packet()
#             del npcs_rep[nid]['alive'] # to use the same 'are_observations_equal' function
#         cls.final_npcs_rep = npcs_rep

#     def test_func_are_observations_equal(self):
#         # are_observations_equal CANNOT be replaced with assertDictEqual
#         self.assertTrue(are_observations_equal(self.init_obs_src, self.init_obs_src))
#         self.assertTrue(are_observations_equal(self.final_obs_src, self.final_obs_src))
#         #self.assertDictEqual(self.final_obs_src, self.final_obs_src)

#     def test_func_are_actions_equal(self):
#         # are_actions_equal can be replaced with assertDictEqual
#         for t in range(len(self.actions_src)):
#             #self.assertTrue(are_actions_equal(self.actions_src[t], self.actions_src[t]))
#             self.assertDictEqual(self.actions_src[t], self.actions_src[t])

#     def test_compare_initial_observations(self):
#         self.assertTrue(are_observations_equal(self.init_obs_src, self.init_obs_rep))

#     def test_compare_actions(self):
#         for t in range(len(self.actions_src)):
#             self.assertDictEqual(self.actions_src[t], self.actions_rep[t])

#     def test_compare_final_observations(self):
#         self.assertTrue(are_observations_equal(self.final_obs_src, self.final_obs_rep))

#     def test_compare_final_npcs(self)        :
#         self.assertTrue(are_observations_equal(self.final_npcs_src, self.final_npcs_rep))


# if __name__ == '__main__':
#     unittest.main()
