from typing import Dict, List, Tuple

from pettingzoo.utils.env import AgentID

import nmmo
from nmmo.task.game_state import GameStateGenerator
from nmmo.task.predicate import Predicate


# TODO(kywch): how to divide the task system, into core vs. wrapper, etc.?
#  We will address this once the task wrapper is stable
# pylint: disable=abstract-method
class TaskWrapper(nmmo.Env):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    # CHECK ME: should every agent have a task assigned?

    # TODO(kywch): make "task_assignment" Dict more flexible, perhaps programmable by ELM
    # task_assignment = {
    #   agent1: [(task1, 1), (task2, -1)],
    #   agent2: [(task1, -1), (task3, 2)] }
    self._task_assignment: Dict[int, List[Tuple[Predicate, int]]] = None

    # game state generator
    self.gs_gen: GameStateGenerator = None
    self.game_state = None

  # pylint: disable=arguments-renamed
  def reset(self, task_assignment: Dict[int, List[Tuple[Predicate, int]]],
            map_id=None, seed=None, options=None):
    gym_obs = super().reset(map_id, seed, options)

    self.gs_gen = GameStateGenerator(self.realm, self.config)
    self._task_assignment = task_assignment

    return gym_obs

  def _compute_rewards(self, agents: List[AgentID], dones: Dict[AgentID, bool]):
    '''Computes the reward for the specified agent'''
    infos = {}
    rewards = { eid: -1 for eid in dones }

    self.game_state = self.gs_gen.generate(self.realm, self.obs)

    for agent_id in agents:
      infos[agent_id] = {}
      agent = self.realm.players.get(agent_id)

      # if agent is None, we assume that it's dead
      if agent is None:
        # assert agent is not None, f'Agent {agent_id} not found'
        rewards[agent_id] = -1
        continue

      rewards[agent_id] = 0
      infos[agent_id] = { 'task': {} }

      # CHECK ME: some agents may not have a assigned task. is it ok?
      if agent_id in self._task_assignment:
        for task, at_stake in self._task_assignment[agent_id]:
          assert callable(task), "Provided task is not callable"
          if isinstance(task, Predicate):
            task_name = task.name
          else:
            # CHECK ME: for a callable function, would this be enough?
            task_name = task.__name__

          # cache the results if not already
          if task_name not in self.game_state.cache_result:
            # CHECK ME: if task name happens to be the same, it will have the same results
            #   This won't be a problem for the predicates and their propositional combination
            #   However, if there are different task fns with the same name, it'd be a problem
            self.game_state.cache_result[task_name] = task(self.game_state)

          rew = self.game_state.cache_result[task_name] * at_stake
          rewards[agent_id] += rew

          infos[agent_id]['task'].update({ task_name: rew })

    return rewards, infos
