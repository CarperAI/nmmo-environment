# pylint: disable=all

# import numpy as np

# import nmmo

# from scripted import baselines

# def serialize_actions(env: nmmo.Env, actions, debug=True):
#     atn_copy = {}
#     for ent_id in list(actions.keys()):
#         if ent_id not in env.realm.players:
#             if debug:
#                 print("invalid player id", ent_id)
#             continue

#         ent = env.realm.players[ent_id]

#         atn_copy[ent_id] = {}
#         for atn, args in actions[ent_id].items():
#             atn_copy[ent_id][atn] = {}
#             drop = False
#             for arg, val in args.items():
#                 if arg.argType == nmmo.action.Fixed:
#                     atn_copy[ent_id][atn][arg] = arg.edges.index(val)
#                 elif arg == nmmo.action.Target:
#                     lookup = env.action_lookup[ent_id]['Entity']
#                     if val.ent_id not in lookup:
#                         if debug:
#                             print("invalid target", ent_id, lookup, val.ent_id)
#                         drop = True
#                         continue
#                     atn_copy[ent_id][atn][arg] = lookup.index(val.ent_id)
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
#                     if val not in env.realm.exchange.dataframeVals:
#                         if debug:
#                             itm_list = [type(itm) for itm in env.realm.exchange.dataframeVals]
#                             print("invalid item to buy (not listed in the exchange)", itm_list, type(val))
#                         drop = True
#                         continue
#                     atn_copy[ent_id][atn][arg] = env.realm.exchange.dataframeVals.index(val)
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
#         assert self.has_reset, 'step before reset'

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
#                             targ = self.action_lookup[ent_id]['Entity'][val]
#                             #TODO: find a better way to err check for dead/missing agents
#                             try:
#                                 self.actions[ent_id][atn][arg] = self.realm.entity(targ)
#                             except:
#                                 del self.actions[ent_id][atn]
#                         elif atn in (nmmo.action.Sell, nmmo.action.Use, nmmo.action.Give) and arg == nmmo.action.Item:
#                             if val >= len(ent.inventory.dataframeKeys):
#                                 drop = True
#                                 continue
#                             itm = [e for e in ent.inventory._item_references][val]
#                             if type(itm) == nmmo.systems.item.Gold:
#                                 drop = True
#                                 continue
#                             self.actions[ent_id][atn][arg] = itm
#                         elif atn == nmmo.action.Buy and arg == nmmo.action.Item:
#                             if val >= len(self.realm.exchange.dataframeKeys):
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

#         rewards, dones, self.raw = {}, {}, {}
#         obs, self.action_lookup = self.realm.dataframe.get(self.realm.players)
#         for ent_id, ent in self.realm.players.items():
#             ob = obs[ent_id]
#             self.obs[ent_id] = ob

#             # Generate decisions of scripted agents and save these to self.actions
#             if ent.agent.scripted:
#                 atns = ent.agent(ob)
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
