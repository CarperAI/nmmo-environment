# TODO: the below line will be gone after implementation
# pylint: disable=unnecessary-pass
from nmmo.task.task import PredicateTask
from nmmo.systems import item as Item
from nmmo.systems import skill as Skill


class InventorySpaceLT(PredicateTask):
  def __init__(self, space: int):
    super().__init__(space)
    self.space = space

  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class ItemTask(PredicateTask):
  def __init__(self, item: Item.Item, level: int=0, quantity: int=1):
    super().__init__(item, level, quantity)
    self.item_type = item.ITEM_TYPE_ID
    self.level = level
    self.quantity = quantity


class OwnItem(ItemTask):
  '''Own an item of a certain type and level (equal or higher)'''
  def __call__(self, team_gs, ent_id):
    """True if the agent (ent_id) owns the item (item_type, >= min_level) 
       and has greater than or equal to quantity. Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    data = team_gs.item_data # 2d numpy data of the team item instances
    flt_idx = (data[:,team_gs.item_cols['owner_id']] == ent_id) & \
              (data[:,team_gs.item_cols['type_id']] == self.item_type) & \
              (data[:,team_gs.item_cols['level']] >= self.level)

    return sum(data[flt_idx,team_gs.item_cols['quantity']]) >= self.quantity


class TeamOwnItem(ItemTask):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    pass


class EquipItem(ItemTask): # quantity is NOT used here
  '''Equip an item of a certain type and level (equal or higher)'''
  def __call__(self, team_gs, ent_id):
    """True if the agent (ent_id) equips the item (item_type, >= min_level).
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    data = team_gs.item_data # 2d numpy data of the team item instances
    flt_idx = (data[:,team_gs.item_cols['owner_id']] == ent_id) & \
              (data[:,team_gs.item_cols['type_id']] == self.item_type) & \
              (data[:,team_gs.item_cols['level']] >= self.level) & \
              (data[:,team_gs.item_cols['equipped']] > 0)

    return len(data[flt_idx,0]) > 0


# pylint: disable=protected-access
class TeamFullyArmed(PredicateTask):

  WEAPON_IDS = {
    Skill.Melee: {'weapon':5, 'ammo':13}, # Sword, Scrap
    Skill.Range: {'weapon':6, 'ammo':14}, # Bow, Shaving
    Skill.Mage: {'weapon':7, 'ammo':15} # Wand, Shard
  }

  '''Count the number of fully-equipped agents of a specific skill in the team'''
  def __init__(self, combat_style, level: int, num_agent: int):
    assert combat_style in [Skill.Melee, Skill.Range, Skill.Melee], "Wrong style input"
    super().__init__(combat_style, level, num_agent)
    self.combat_style = combat_style
    self.min_level = level
    self.num_agent = num_agent

    self.item_ids = { 'hat':2, 'top':3, 'bottom':4 }
    self.item_ids.update(self.WEAPON_IDS[combat_style])

  def __call__(self, team_gs, ent_id):
    """True if the number of fully equipped agents is greater than or equal to num_agent
       Otherwise false.

       To determine fully equipped, we look at hat, top, bottom, weapon, ammo, respectively,
       and see whether these are equipped and has level greater than or equal to min_level.
    """
    super().__call__(team_gs, ent_id)

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


#######################################
# Event-log based predicates
#######################################

class ConsumeItem(ItemTask):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass


class TeamConsumeItem(ItemTask):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass


class ProduceItem(ItemTask):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass


class TeamProduceItem(ItemTask):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass


class ListItem(ItemTask):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass


class BuyItem(ItemTask):
  def __call__(self, team_gs, ent_id):
    """True if
       Otherwise false.
    """
    super().__call__(team_gs, ent_id)
    pass
