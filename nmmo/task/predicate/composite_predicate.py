#pylint: disable=invalid-name, unused-argument, no-value-for-parameter
from nmmo.task.predicate.core import predicate, OR
from nmmo.task.predicate.base_predicate import CanSeeAgent
from nmmo.task.group import Group
from nmmo.task.game_state import GameState

@predicate
def CanSeeGroup(gs: GameState,
                subject: Group,
                target: Group):
  """ Returns True iff subject can see any of target
  """
  return OR(*(CanSeeAgent(subject, agent) for agent in target.agents))
