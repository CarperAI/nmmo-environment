# pylint: disable=no-member
import numpy as np
import nmmo

HORIZON = 16

config = nmmo.config.Default()
env = nmmo.integrations.CleanRLEnv(config, seed=42)
actions =  [ { e: env.action_space(1).sample()
               for e in range(1, config.PLAYER_N+1) }
            for _ in range(HORIZON) ]

np.save('actions.npy', actions)
