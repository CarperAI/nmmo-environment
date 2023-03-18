# TODO: the below line will be gone after implementation
# pylint: disable=unnecessary-pass
from nmmo.task.task import PredicateTask

class GoldTask(PredicateTask):
  def __init__(self, amount: int):
    super().__init__(amount)
    self.amount = amount


class HoardGold(GoldTask):
  def __call__(self, team_gs, ent_id):
    """True if the gold of agent (ent_id) is greater than or equal to min_amount.
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    agent = team_gs.entity_or_none(ent_id)
    if agent:
      return agent.gold >= self.amount

    return False


class TeamHoardGold(GoldTask):
  def __call__(self, team_gs, ent_id):
    """True if the summed gold of all teammate is greater than or equal to min_amount.
       Otherwise false
    """
    super().__call__(team_gs, ent_id)
    return sum(team_gs.entity_data[:,team_gs.entity_cols['gold']]) >= self.amount


#######################################
# Event-log based predicates
#######################################

class EarnGold(GoldTask):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass


class TeamEarnGold(GoldTask):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass


class SpendGold(GoldTask):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass


class TeamSpendGold(GoldTask):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass


class MakeProfit(GoldTask):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass


class TeamMakeProfit(GoldTask):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass
