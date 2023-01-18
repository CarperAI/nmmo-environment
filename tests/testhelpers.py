from pdb import set_trace as T

import numpy as np

import nmmo

from scripted import baselines

def serialize_actions(env: nmmo.Env, actions, debug=True):
    atn_copy = {}
    for entID in list(actions.keys()):
        if entID not in env.realm.players:
            if debug:
                print("invalid player id", entID)
            continue

        ent = env.realm.players[entID]

        atn_copy[entID] = {}
        for atn, args in actions[entID].items():
            atn_copy[entID][atn] = {}
            drop = False
            for arg, val in args.items():
                if arg.argType == nmmo.action.Fixed:
                    atn_copy[entID][atn][arg] = arg.edges.index(val)
                elif arg == nmmo.action.Target:
                    lookup = env.action_lookup[entID]['Entity']
                    if val.entID not in lookup:
                        if debug:
                            print("invalid target", entID, lookup, val.entID)
                        drop = True
                        continue
                    atn_copy[entID][atn][arg] = lookup.index(val.entID)
                elif atn in (nmmo.action.Sell, nmmo.action.Use, nmmo.action.Give) and arg == nmmo.action.Item:
                    if val not in ent.inventory._item_references:
                        if debug:
                            itm_list = [type(itm) for itm in ent.inventory._item_references]
                            print("invalid item to sell/use/give", entID, itm_list, type(val))
                        drop = True
                        continue
                    if type(val) == nmmo.systems.item.Gold:
                        if debug:
                            print("cannot sell/use/give gold", entID, itm_list, type(val))
                        drop = True
                        continue
                    atn_copy[entID][atn][arg] = [e for e in ent.inventory._item_references].index(val)
                elif atn == nmmo.action.Buy and arg == nmmo.action.Item:
                    if val not in env.realm.exchange.dataframeVals:
                        if debug:
                            itm_list = [type(itm) for itm in env.realm.exchange.dataframeVals]
                            print("invalid item to buy (not listed in the exchange)", itm_list, type(val))
                        drop = True
                        continue
                    atn_copy[entID][atn][arg] = env.realm.exchange.dataframeVals.index(val)
                else:
                    # scripted ais have not bought any stuff
                    assert False, f'Argument {arg} invalid for action {atn}'

            # Cull actions with bad args
            if drop and atn in atn_copy[entID]:
                del atn_copy[entID][atn]

    return atn_copy


# this function can be replaced by assertDictEqual
# but might be still useful for debugging
def are_actions_equal(source_atn, target_atn, debug=True):
    
    # compare the numbers and player ids
    player_src = list(source_atn.keys())
    player_tgt = list(target_atn.keys())
    if player_src != player_tgt:
        if debug:
            print("players don't match")
        return False

    # for each player, compare the actions
    for entID in player_src:
        atn1 = source_atn[entID]
        atn2 = target_atn[entID]

        if list(atn1.keys()) != list(atn2.keys()):
            if debug:
                print("action keys don't match. player:", entID)
            return False

        for atn, args in atn1.items():
            if atn2[atn] != args:
                if debug:
                    print("action args don't match. player:", entID, ", action:", atn)
                return False

    return True


# this function CANNOT be replaced by assertDictEqual
def are_observations_equal(source_obs, target_obs, debug=True):

    keys_src = list(source_obs.keys())
    keys_obs = list(target_obs.keys())
    if keys_src != keys_obs:
        if debug:
            print("observation keys don't match")
        return False

    for k in keys_src:
        ent_src = source_obs[k]
        ent_tgt = target_obs[k]
        if list(ent_src.keys()) != list(ent_tgt.keys()):
            if debug:
                print("entities don't match. key:", k)
            return False
        
        obj = ent_src.keys()
        for o in obj:
            obj_src = ent_src[o]
            obj_tgt = ent_tgt[o]
            if list(obj_src) != list(obj_tgt):
                if debug:
                    print("objects don't match. key:", k, ', obj:', o)
                return False

            attrs = list(obj_src)
            for a in attrs:
                attr_src = obj_src[a]
                attr_tgt = obj_tgt[a]

                if np.sum(attr_src != attr_tgt) > 0:
                    if debug:
                        print("attributes don't match. key:", k, ', obj:', o, ', attr:', a)
                    return False

    return True


class TestEnv(nmmo.Env):
    '''
        EnvTest step() bypasses some differential treatments for scripted agents
        To do so, actions of scripted must be serialized using the serialize_actions function above
    '''
    __test__ = False

    def __init__(self, config=None, seed=None):
        assert config.EMULATE_FLAT_OBS == False, 'EMULATE_FLAT_OBS must be FALSE'
        assert config.EMULATE_FLAT_ATN == False, 'EMULATE_FLAT_ATN must be FALSE'
        super().__init__(config, seed)

    def step(self, actions):
        assert self.has_reset, 'step before reset'

        # if actions are empty, then skip below to proceed with self.actions
        # if actions are provided, 
        #   forget self.actions and preprocess the provided actions
        if actions != {}:
            self.actions = {}
            for entID in list(actions.keys()):
                if entID not in self.realm.players:
                    continue

                ent = self.realm.players[entID]

                if not ent.alive:
                    continue

                self.actions[entID] = {}
                for atn, args in actions[entID].items():
                    self.actions[entID][atn] = {}
                    drop = False
                    for arg, val in args.items():
                        if arg.argType == nmmo.action.Fixed:
                            self.actions[entID][atn][arg] = arg.edges[val]
                        elif arg == nmmo.action.Target:
                            targ = self.action_lookup[entID]['Entity'][val]
                            #TODO: find a better way to err check for dead/missing agents
                            try:
                                self.actions[entID][atn][arg] = self.realm.entity(targ)
                            except:
                                del self.actions[entID][atn]
                        elif atn in (nmmo.action.Sell, nmmo.action.Use, nmmo.action.Give) and arg == nmmo.action.Item:
                            if val >= len(ent.inventory.dataframeKeys):
                                drop = True
                                continue
                            itm = [e for e in ent.inventory._item_references][val]
                            if type(itm) == nmmo.systems.item.Gold:
                                drop = True
                                continue
                            self.actions[entID][atn][arg] = itm
                        elif atn == nmmo.action.Buy and arg == nmmo.action.Item:
                            if val >= len(self.realm.exchange.dataframeKeys):
                                drop = True
                                continue
                            itm = self.realm.exchange.dataframeVals[val]
                            self.actions[entID][atn][arg] = itm
                        elif __debug__: #Fix -inf in classifier and assert err on bad atns
                            assert False, f'Argument {arg} invalid for action {atn}'

                    # Cull actions with bad args
                    if drop and atn in self.actions[entID]:
                        del self.actions[entID][atn]

        #Step: Realm, Observations, Logs
        self.dead    = self.realm.step(self.actions)
        self.actions = {}
        self.obs     = {}
        infos        = {}

        rewards, dones, self.raw = {}, {}, {}
        obs, self.action_lookup = self.realm.dataframe.get(self.realm.players)
        for entID, ent in self.realm.players.items():
            ob = obs[entID] 
            self.obs[entID] = ob

            # Generate decisions of scripted agents and save these to self.actions
            if ent.agent.scripted:
                atns = ent.agent(ob)
                for atn, args in atns.items():
                    for arg, val in args.items():
                        atns[atn][arg] = arg.deserialize(self.realm, ent, val)
                self.actions[entID] = atns

            # also, return below for the scripted agents
            obs[entID]     = ob
            rewards[entID], infos[entID] = self.reward(ent)
            dones[entID]   = False

        self.log_env()
        for entID, ent in self.dead.items():
            self.log_player(ent)

        self.realm.exchange.step()

        for entID, ent in self.dead.items():
            #if ent.agent.scripted:
            #    continue
            rewards[ent.entID], infos[ent.entID] = self.reward(ent)

            dones[ent.entID] = False #TODO: Is this correct behavior?

            #obs[ent.entID]     = self.dummy_ob

        #Pettingzoo API
        self.agents = list(self.realm.players.keys())

        self.obs = obs
        return obs, rewards, dones, infos


class TestConfig(nmmo.config.Small, nmmo.config.AllGameSystems):
    
    __test__ = False

    RENDER = False
    SPECIALIZE = True
    PLAYERS = [
            baselines.Fisher, baselines.Herbalist, baselines.Prospector, baselines.Carver, baselines.Alchemist,
            baselines.Melee, baselines.Range, baselines.Mage]
