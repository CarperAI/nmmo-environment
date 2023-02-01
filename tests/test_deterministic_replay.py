# pylint: disable=all

# TODO: This test is currently broken, and needs to be fixed

# from pdb import set_trace as T
# import unittest
# from tqdm import tqdm

# import pickle, os, glob
# import random

# import nmmo

# from testhelpers import TestEnv, TestConfig, serialize_actions, are_observations_equal

# TEST_HORIZON = 50
# LOCAL_REPLAY = 'tests/replay_local.pickle'

# def load_replay_file(replay_file):
#    # load the pickle file
#    with open(replay_file, 'rb') as handle:
#       ref_data = pickle.load(handle)

#       print('[TestDetReplay] Loading the existing replay file with seed', ref_data['seed'])
#       seed = ref_data['seed']
#       config = ref_data['config']
#       init_obs = ref_data['init_obs']
#       actions = ref_data['actions']
#       final_obs = ref_data['final_obs']
#       final_npcs = ref_data['final_npcs']

#    return seed, config, init_obs, actions, final_obs, final_npcs


# def generate_replay_file(replay_file, test_horizon):
#    # generate the new data with a new env
#    seed = random.randint(0, 10000)
#    print('[TestDetReplay] Creating a new replay file with seed', seed)
#    config = TestConfig()
#    env_src = TestEnv(config, seed)
#    init_obs = env_src.reset()

#    actions = []
#    print('Running', test_horizon, 'tikcs')
#    for t in tqdm(range(test_horizon)):
#       actions.append(serialize_actions(env_src, env_src.actions))
#       nxt_obs, _, _, _ = env_src.step({})
#    final_obs = nxt_obs
#    final_npcs = {}
#    for nid, npc in list(env_src.realm.npcs.items()):
#       final_npcs[nid] = npc.packet()
#       del final_npcs[nid]['alive'] # to use the same 'are_observations_equal' function

#    # save to the file
#    with open(replay_file, 'wb') as handle:
#       ref_data = {}
#       ref_data['version'] = nmmo.__version__ # just in case
#       ref_data['seed'] = seed
#       ref_data['config'] = config
#       ref_data['init_obs'] = init_obs
#       ref_data['actions'] = actions
#       ref_data['final_obs'] = final_obs
#       ref_data['final_npcs'] = final_npcs

#       pickle.dump(ref_data, handle)

#    return seed, config, init_obs, actions, final_obs, final_npcs


# class TestDeterministicReplay(unittest.TestCase):
#    @classmethod
#    def setUpClass(cls):
#       """
#          First, check if there is a replay file on the repo, the name of which must start with 'replay_repo_'
#             If there is one, use it.

#          Second, check if there a local replay file, which should be named 'replay_local.pickle'
#             If there is one, use it. If not create one.

#          TODO: allow passing a different replay file
#       """
#       # first, look for the repo replay file
#       replay_files = glob.glob(os.path.join('tests', 'replay_repo_*.pickle'))
#       if replay_files:
#          # there may be several, but we only take the first one [0]
#          cls.seed, cls.config, cls.init_obs_src, cls.actions, cls.final_obs_src, cls.final_npcs_src = load_replay_file(replay_files[0])
#       else:
#          # if there is no repo replay file, then go with the default local file
#          if os.path.exists(LOCAL_REPLAY):
#             cls.seed, cls.config, cls.init_obs_src, cls.actions, cls.final_obs_src, cls.final_npcs_src = load_replay_file(LOCAL_REPLAY)
#          else:
#             cls.seed, cls.config, cls.init_obs_src, cls.actions, cls.final_obs_src, cls.final_npcs_src = generate_replay_file(LOCAL_REPLAY, TEST_HORIZON)
#       cls.horizon = len(cls.actions)

#       print('[TestDetReplay] Setting up the replication env with seed', cls.seed)
#       env_rep = TestEnv(cls.config, seed=cls.seed)
#       cls.init_obs_rep = env_rep.reset()
#       print('Running', cls.horizon, 'tikcs')
#       for t in tqdm(range(cls.horizon)):
#          nxt_obs_rep, _, _, _ = env_rep.step(cls.actions[t])
#       cls.final_obs_rep = nxt_obs_rep
#       npcs_rep = {}
#       for nid, npc in list(env_rep.realm.npcs.items()):
#          npcs_rep[nid] = npc.packet()
#          del npcs_rep[nid]['alive'] # to use the same 'are_observations_equal' function
#       cls.final_npcs_rep = npcs_rep

#    def test_compare_init_observations(self):
#       self.assertTrue(are_observations_equal(self.init_obs_src, self.init_obs_rep))

#    def test_compare_final_observations(self):
#       self.assertTrue(are_observations_equal(self.final_obs_src, self.final_obs_rep))

#    def test_compare_final_npcs(self):
#       self.assertTrue(are_observations_equal(self.final_npcs_src, self.final_npcs_rep))


# if __name__ == '__main__':
#    unittest.main()

