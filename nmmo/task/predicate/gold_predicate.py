#pylint: disable=invalid-name, unused-argument
from nmmo.task.predicate import Predicate
from nmmo.task.predicate.core import predicate
from nmmo.task.group import Group
from nmmo.task.game_state import GameState

class GoldPredicate(Predicate):
  # pylint: disable=abstract-method
  def __init__(self, subject: Group, amount: int):
    super().__init__(subject, amount)
    self._amount = amount

@predicate
def HoardGold(gs: GameState,
              subject:Group,
              amount: int):
  """True iff the summed gold of all teammate is greater than or equal to amount.
  """
  return subject.gold.sum() >= amount

#######################################
# Event-log based predicates
#######################################

class EarnGold(GoldPredicate):
  def _evaluate(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class SpendGold(GoldPredicate):
  def _evaluate(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class MakeProfit(GoldPredicate):
  def _evaluate(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError
