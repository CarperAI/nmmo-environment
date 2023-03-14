from nmmo.task.task import PredicateTask
from nmmo.systems import item as Item
from nmmo.io import action as Action


# CHECK ME: maybe this should be the default task?
class LiveLong(PredicateTask):
  # uses the default __init__, step, reward
  def evaluate(self, team_gs, ent_id):
    """True if the health of agent (ent_id) is greater than 0.
       Otherwise false.
    """
    row = team_gs.entity_or_none(ent_id)
    if row:
      return row.health > 0

    return False


class HoardGold(PredicateTask):
  def __init__(self, min_amount: int):
    super().__init__(min_amount)
    self.min_amount = min_amount

  def evaluate(self, team_gs, ent_id):
    """True if the gold of agent (ent_id) is greater than or equal to min_amount.
       Otherwise false.
    """
    row = team_gs.entity_or_none(ent_id)
    if row:
      return row.gold >= self.min_amount

    return False


# each agent is rewarded if the alive teammate is greater than min_size
class TeamSizeGE(PredicateTask): # greater than or equal to
  def __init__(self, min_size: int):
    super().__init__(min_size)
    self.min_size = min_size

  def evaluate(self, team_gs, ent_id):
    """True if the number of alive teammates is greater than or equal to min_size.
       Otherwise false.
    """
    assert team_gs.is_member(ent_id), \
      "Agent is not in the team, so cannot access the team game state"
    if team_gs.pop_id in team_gs.alive_all:
      return len(team_gs.alive_all) >= self.min_size

    return False


class TeamHoardGold(PredicateTask):
  def __init__(self, min_amount: int):
    super().__init__(min_amount)
    self.min_amount = min_amount

  def evaluate(self, team_gs, ent_id):
    """True if the summed gold of all teammate is greater than or equal to min_amount.
       Otherwise false
    """
    assert team_gs.is_member(ent_id), \
      "Agent is not in the team, so cannot access the team game state"
    return sum(team_gs.entity_data[:,team_gs.entity_cols['gold']]) >= self.min_amount


class OwnItem(PredicateTask):
  '''Own an item of a certain type and level (equal or higher)'''
  def __init__(self, item: Item.Item, min_level: int=0, quantity: int=1):
    super().__init__(item, min_level, quantity)
    self.item_type = item.ITEM_TYPE_ID
    self.min_level = min_level
    self.quantity = quantity

  def evaluate(self, team_gs, ent_id):
    """True if the agent (ent_id) owns the item (item_type, >= min_level) 
       and has greater than or equal to quantity. Otherwise false.
    """
    assert team_gs.is_member(ent_id), \
      "Agent is not in the team, so cannot access the team game state"
    data = team_gs.item_data # 2d numpy data of the team item instances
    flt_idx = (data[:,team_gs.item_cols['owner_id']] == ent_id) & \
              (data[:,team_gs.item_cols['type_id']] == self.item_type) & \
              (data[:,team_gs.item_cols['level']] >= self.min_level)

    return len(data[flt_idx,0]) >= self.quantity


class EquipItem(PredicateTask):
  '''Equip an item of a certain type and level (equal or higher)'''
  def __init__(self, item: Item.Equipment, min_level: int=0):
    super().__init__(item, min_level)
    self.item_type = item.ITEM_TYPE_ID
    self.min_level = min_level

  def evaluate(self, team_gs, ent_id):
    """True if the agent (ent_id) equips the item (item_type, >= min_level).
       Otherwise false.
    """
    assert team_gs.is_member(ent_id), \
      "Agent is not in the team, so cannot access the team game state"
    data = team_gs.item_data # 2d numpy data of the team item instances
    flt_idx = (data[:,team_gs.item_cols['owner_id']] == ent_id) & \
              (data[:,team_gs.item_cols['type_id']] == self.item_type) & \
              (data[:,team_gs.item_cols['level']] >= self.min_level) & \
              (data[:,team_gs.item_cols['equipped']] > 0)

    return len(data[flt_idx,0]) > 0

# pylint: disable=protected-access
class TeamFullyArmed(PredicateTask):

  WEAPON_IDS = {
    Action.Melee: {'weapon':5, 'ammo':13}, # Sword, Scrap
    Action.Range: {'weapon':6, 'ammo':14}, # Bow, Shaving
    Action.Mage: {'weapon':7, 'ammo':15} # Wand, Shard
  }

  '''Count the number of fully-equipped agents of a specific skill in the team'''
  def __init__(self, attack_style, min_level: int, num_agent: int):
    assert attack_style in [Action.Melee, Action.Range, Action.Melee], "Wrong style input"
    super().__init__(attack_style, min_level, num_agent)
    self.attack_style = attack_style
    self.min_level = min_level
    self.num_agent = num_agent

    self.item_ids = { 'hat':2, 'top':3, 'bottom':4 }
    self.item_ids.update(self.WEAPON_IDS[attack_style])

  def evaluate(self, team_gs, ent_id):
    """True if the number of fully equipped agents is greater than or equal to num_agent
       Otherwise false.

       To determine fully equipped, we look at hat, top, bottom, weapon, ammo, respectively,
       and see whether these are equipped and has level greater than or equal to min_level.
    """
    assert team_gs.is_member(ent_id), \
      "Agent is not in the team, so cannot access the team game state"

    # check if the cached result is available
    if self.__class__ in team_gs.cache_result:
      return team_gs.cache_result[self.__class__]

    data = team_gs.item_data # 2d numpy data of the team item instances
    flt_idx = (data[:,team_gs.item_cols['level']] >= self.min_level) & \
              (data[:,team_gs.item_cols['equipped']] > 0)

    # should have all hat, top, bottom (general)
    tmp_grpby = {}
    for item, type_id in self.item_ids.items():
      flt_tmp = flt_idx & (data[:,team_gs.item_cols['type_id']] == type_id)
      tmp_grpby[item] = \
        team_gs.group_by(data[flt_tmp], team_gs.item_cols['owner_id'])

    # get the intersection of all tmp_grpby keys
    equipped_each = [set(equipped.keys()) for equipped in tmp_grpby.values()]
    equipped_all = set.intersection(*equipped_each)

    team_gs.cache_result[self.__class__] = len(equipped_all) >= self.num_agent

    return team_gs.cache_result[self.__class__]
