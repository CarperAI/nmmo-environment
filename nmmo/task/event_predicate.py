from nmmo.task.predicate import Predicate, Group
from nmmo.task.game_state import GameState

from nmmo.systems import skill as Skill

#######################################
# Event-log based predicates
#######################################

class CountEvent(Predicate):
  # pylint: disable=abstract-method
  def __init__(self, subject: Group, count: int):
    super().__init__(subject, count)
    self._count = count


class EatFood(CountEvent):
  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class DrinkWater(CountEvent):
  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class GiveItem(CountEvent):
  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class DestroyItem(CountEvent):
  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class GiveGold(CountEvent):
  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class ScoreHit(Predicate):
  def __init__(self, subject: Group, combat_style: Skill.Skill, count: int):
    super().__init__(subject, combat_style, count)
    self._combat_style = combat_style
    self._count = count

  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class ScoreKill(Predicate):
  def __init__(self, subject: Group, num_kill: int):
    super().__init__(subject, num_kill)
    self._num_kill = num_kill

  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError
