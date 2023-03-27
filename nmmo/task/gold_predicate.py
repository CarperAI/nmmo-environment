from nmmo.task.predicate import Predicate, Group
from nmmo.task.game_state import GameState


class GoldPredicate(Predicate):
  def __init__(self, subject: Group, amount: int):
    super().__init__(subject, amount)
    self._amount = amount


class HoardGold(GoldPredicate):
  def __call__(self, gs: GameState):
    """True if the summed gold of all teammate is greater than or equal to _amount.
       Otherwise false
    """
    sbj_data = gs.where_in_id('entity', self.subject)

    return sum(sbj_data[:, gs.entity_cols['gold']]) >= self._amount


#######################################
# Event-log based predicates
#######################################

class EarnGold(GoldPredicate):
  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class SpendGold(GoldPredicate):
  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class MakeProfit(GoldPredicate):
  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError
