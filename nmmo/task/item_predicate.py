from nmmo.task.predicate import Predicate, Group
from nmmo.task.game_state import GameState
from nmmo.systems import item as Item
from nmmo.systems import skill as Skill


class InventorySpaceGE(Predicate):
  def __init__(self, subject: Group, space: int):
    super().__init__(subject, space)
    self._space = space

  def __call__(self, gs: GameState):
    """True if the inventory space of every subjects is greater than or equal to
       the self._space. Otherwise false.
    """
    result = True

    max_space = gs.config.ITEM_INVENTORY_CAPACITY
    for ent_id in self.subject:
      if ent_id in gs.env_obs:
        space = max_space - gs.env_obs[ent_id].inventory.len
        if space < self._space:
          # an agent with inventory space less than _space is found -> False
          result = False
          break

    return result


class ItemPredicate(Predicate):
  # pylint: disable=abstract-method
  def __init__(self, subject: Group,
               item: Item.Item, level: int, quantity: int):
    super().__init__(subject, item, level, quantity)
    self._item_type = item.ITEM_TYPE_ID
    self._level = level
    self._quantity = quantity


class OwnItem(ItemPredicate):
  def __call__(self, gs: GameState):
    """True if the team as whole owns the item (_item_type, >=_level) 
       and has greater than or equal to quantity. Otherwise false.
    """
    sbj_item = gs.where_in_id('item', self.subject)
    flt_idx = (sbj_item[:,gs.item_cols['type_id']] == self._item_type) & \
              (sbj_item[:,gs.item_cols['level']] >= self._level)

    return sum(sbj_item[flt_idx, gs.item_cols['quantity']]) >= self._quantity


class EquipItem(Predicate): # quantity is NOT used here
  def __init__(self, subject: Group,
               item: Item.Item, level: int, num_agent: int):
    super().__init__(subject, item, level, num_agent)
    self._item_type = item.ITEM_TYPE_ID
    self._level = level
    self._num_agent = num_agent

  '''Equip an item of a certain type and level (equal or higher)'''
  def __call__(self, gs: GameState):
    """True if the number of agents that equip the item (_item_type, >=_level)
       is greater than or equal to _num_agent. Otherwise false.
    """
    sbj_item = gs.where_in_id('item', self.subject)
    flt_idx = (sbj_item[:,gs.item_cols['type_id']] == self._item_type) & \
              (sbj_item[:,gs.item_cols['level']] >= self._level) & \
              (sbj_item[:,gs.item_cols['equipped']] > 0)

    return len(sbj_item[flt_idx,0]) >= self._num_agent


class FullyArmed(Predicate):

  _WEAPON_IDS = {
    Skill.Melee: {'weapon':5, 'ammo':13}, # Sword, Scrap
    Skill.Range: {'weapon':6, 'ammo':14}, # Bow, Shaving
    Skill.Mage: {'weapon':7, 'ammo':15} # Wand, Shard
  }

  '''Count the number of fully-equipped agents of a specific skill in the team'''
  def __init__(self, subject: Group,
               combat_style, level: int, num_agent: int):
    assert combat_style in [Skill.Melee, Skill.Range, Skill.Melee], "Wrong style input"
    super().__init__(subject, combat_style, level, num_agent)
    self._combat_style = combat_style
    self._level = level
    self._num_agent = num_agent

    self._item_ids = { 'hat':2, 'top':3, 'bottom':4 }
    self._item_ids.update(self._WEAPON_IDS[combat_style])

  def __call__(self, gs: GameState):
    """True if the number of fully equipped agents is greater than or equal to _num_agent
       Otherwise false.

       To determine fully equipped, we look at hat, top, bottom, weapon, ammo, respectively,
       and see whether these are equipped and has level greater than or equal to _level.
    """
    sbj_item = gs.where_in_id('item', self.subject)
    flt_idx = (sbj_item[:,gs.item_cols['level']] >= self._level) & \
              (sbj_item[:,gs.item_cols['equipped']] > 0)

    # should have all hat, top, bottom (general)
    tmp_grpby = {}
    for item, type_id in self._item_ids.items():
      flt_tmp = flt_idx & (sbj_item[:,gs.item_cols['type_id']] == type_id)
      tmp_grpby[item] = \
        gs.group_by(sbj_item[flt_tmp], gs.item_cols['owner_id'])

    # get the intersection of all tmp_grpby keys
    equipped_each = [set(equipped.keys()) for equipped in tmp_grpby.values()]
    equipped_all = set.intersection(*equipped_each)

    return len(equipped_all) >= self._num_agent


#######################################
# Event-log based predicates
#######################################

class ConsumeItem(ItemPredicate):
  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class ProduceItem(ItemPredicate):
  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class ListItem(ItemPredicate):
  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class BuyItem(ItemPredicate):
  def __call__(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError
