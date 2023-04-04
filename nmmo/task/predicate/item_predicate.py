#pylint: disable=invalid-name, unused-argument
import numpy as np
from numpy import count_nonzero as count
from nmmo.task.predicate import Predicate
from nmmo.task.predicate.core import predicate
from nmmo.task.group import Group
from nmmo.task.game_state import GameState
from nmmo.systems.item import Item
from nmmo.systems import skill as Skill

class InventorySpaceGE(Predicate):
  def __init__(self, subject: Group, space: int):
    super().__init__(subject, space)
    self.subject = subject
    self._space = space

  def _evaluate(self, gs: GameState):
    """True if the inventory space of every subjects is greater than or equal to
       the self._space. Otherwise false.
    """
    result = True

    max_space = gs.config.ITEM_INVENTORY_CAPACITY
    for ent_id in self.subject.agents:
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
               item: Item, level: int, quantity: int):
    super().__init__(subject, item, level, quantity)
    self.subject = subject
    self._item_type = item.ITEM_TYPE_ID
    self._level = level
    self._quantity = quantity

@predicate
def OwnItem(gs: GameState,
            subject: Group,
            item: Item,
            level: int,
            quantity: int):
  """True if the number of items owned (_item_type, >= level)
     is greater than or equal to quantity.
  """
  owned = (subject.item.type_id == item.ITEM_TYPE_ID) & \
          (subject.item.level >= level)
  return sum(subject.item.quantity[owned]) >= quantity

@predicate
def EquipItem(gs: GameState,
              subject: Group,
              item: Item,
              level: int,
              num_agent: int):
  """True if the number of agents that equip the item (_item_type, >=_level)
     is greater than or equal to _num_agent.
  """
  equipped = (subject.item.type_id == item.ITEM_TYPE_ID) & \
             (subject.item.level >= level) & \
             (subject.item.equipped > 0)
  return count(equipped) >= num_agent

@predicate
def FullyArmed(gs: GameState,
               subject: Group,
               combat_style: Skill.CombatSkill,
               level: int,
               num_agent: int):
  """True if the number of fully equipped agents is greater than or equal to _num_agent
       Otherwise false.

       To determine fully equipped, we look at hat, top, bottom, weapon, ammo, respectively,
       and see whether these are equipped and has level greater than or equal to _level.
  """
  WEAPON_IDS = {
    Skill.Melee: {'weapon':5, 'ammo':13}, # Sword, Scrap
    Skill.Range: {'weapon':6, 'ammo':14}, # Bow, Shaving
    Skill.Mage: {'weapon':7, 'ammo':15} # Wand, Shard
  }
  item_ids = { 'hat':2, 'top':3, 'bottom':4 }
  item_ids.update(WEAPON_IDS[combat_style])

  lvl_flt = (subject.item.level >= level) & \
            (subject.item.equipped > 0)
  type_flt = np.isin(subject.item.type_id,list(item_ids.values()))
  _, equipment_numbers = np.unique(subject.item.owner_id[lvl_flt & type_flt],
                                   return_counts=True)

  return (equipment_numbers >= len(item_ids.items())).sum() >= num_agent

#######################################
# Event-log based predicates
#######################################

class ConsumeItem(ItemPredicate):
  def _evaluate(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class ProduceItem(ItemPredicate):
  def _evaluate(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError


class ListItem(ItemPredicate):
  def _evaluate(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError

class BuyItem(ItemPredicate):
  def _evaluate(self, gs: GameState):
    """True if
       Otherwise false.
    """
    raise NotImplementedError
