from __future__ import annotations
from pdb import set_trace as T

import logging
from typing import Dict

from nmmo.io.stimulus import Serialized
from nmmo.lib.colors import Tier

class Item:
  ITEM_TYPE_ID = None
  _item_type_id_to_class: Dict[int, type] = {}

  @staticmethod
  def register(item_type):
    assert item_type.ITEM_TYPE_ID is not None
    if item_type.ITEM_TYPE_ID not in Item._item_type_id_to_class:
      Item._item_type_id_to_class[item_type.ITEM_TYPE_ID] = item_type
  
  @staticmethod
  def item_class(type_id: int):
    return Item._item_type_id_to_class[type_id]

  def __init__(self, realm, level,
              capacity=0, quantity=1, tradable=True,
              melee_attack=0, range_attack=0, mage_attack=0,
              melee_defense=0, range_defense=0, mage_defense=0,
              health_restore=0, resource_restore=0, price=0):

    self.config = realm.config
    self.realm = realm
    Item.register(self.__class__)
    self.datastore_object = realm.datastore.create_record(Serialized.Item.__name__)
    realm.items[self.datastore_object.id] = self

    self.instance = Serialized.Item.ID(self.datastore_object, self.datastore_object.id)
    self.item_type = Serialized.Item.ItemType(self.datastore_object, self.ITEM_TYPE_ID)
    self.level = Serialized.Item.Level(self.datastore_object, level)
    self.capacity = Serialized.Item.Capacity(self.datastore_object, capacity)
    self.quantity = Serialized.Item.Quantity(self.datastore_object, quantity)
    self.tradable = Serialized.Item.Tradable(self.datastore_object, tradable)
    self.melee_attack = Serialized.Item.MeleeAttack(
        self.datastore_object, melee_attack)
    self.range_attack = Serialized.Item.RangeAttack(
        self.datastore_object, range_attack)
    self.mage_attack = Serialized.Item.MageAttack(
        self.datastore_object, mage_attack)
    self.melee_defense = Serialized.Item.MeleeDefense(
        self.datastore_object, melee_defense)
    self.range_defense = Serialized.Item.RangeDefense(
        self.datastore_object, range_defense)
    self.mage_defense = Serialized.Item.MageDefense(
        self.datastore_object, mage_defense)
    self.health_restore = Serialized.Item.HealthRestore(
        self.datastore_object, health_restore)
    self.resource_restore = Serialized.Item.ResourceRestore(
        self.datastore_object, resource_restore)
    self.price = Serialized.Item.Price(self.datastore_object, price)
    self.equipped = Serialized.Item.Equipped(self.datastore_object, 0)
    self.owner = Serialized.Item.Owner(self.datastore_object, 0)
    self.for_sale = Serialized.Item.ForSale(self.datastore_object, 0)


  @property
  def packet(self):
    return {'item':             self.__class__.__name__,
            'level':            self.level.val,
            'capacity':         self.capacity.val,
            'quantity':         self.quantity.val,
            'melee_attack':     self.melee_attack.val,
            'range_attack':     self.range_attack.val,
            'mage_attack':      self.mage_attack.val,
            'melee_defense':    self.melee_defense.val,
            'range_defense':    self.range_defense.val,
            'mage_defense':     self.mage_defense.val,
            'health_restore':   self.health_restore.val,
            'resource_restore': self.resource_restore.val,
            'price':            self.price.val}

  def use(self, entity) -> bool:
    raise NotImplementedError

class Stack:
  @property
  def signature(self):
    return (self.item_type.val, self.level.val)
class Gold(Item, Stack):
  ITEM_TYPE_ID = 0
  def __init__(self, realm, **kwargs):
    super().__init__(realm, level=0, tradable=False, **kwargs)

class Equipment(Item):
  @property
  def packet(self):
    packet = {'color': self.color.packet()}
    return {**packet, **super().packet}

  @property
  def color(self):
    if self.level == 0:
      return Tier.BLACK
    if self.level < 10:
      return Tier.WOOD
    elif self.level < 20:
      return Tier.BRONZE
    elif self.level < 40:
      return Tier.SILVER
    elif self.level < 60:
      return Tier.GOLD
    elif self.level < 80:
      return Tier.PLATINUM
    else:
      return Tier.DIAMOND

  def unequip(self, entity, equip_slot):
    assert self.equipped.val == 1
    self.equipped.update(0)
    equip_slot.unequip(self)

  def equip(self, entity, equip_slot):
    assert self.equipped.val == 0
    if self._level(entity) < self.level.val:
      return

    self.equipped.update(1)
    equip_slot.equip(self)

    if self.config.LOG_MILESTONES and entity.isPlayer and self.config.LOG_VERBOSE:
      for (label, level) in [
        (f"{self.__class__.__name__}_Level", self.level.val),
        ("Item_Level", entity.equipment.item_level),
        ("Melee_Attack", entity.equipment.melee_attack),
        ("Range_Attack", entity.equipment.range_attack),
        ("Mage_Attack", entity.equipment.mage_attack),
        ("Melee_Defense", entity.equipment.melee_defense),
        ("Range_Defense", entity.equipment.range_defense),
        ("Mage_Defense", entity.equipment.mage_defense)]:
      
        if self.realm.quill.milestone.log_max(label, level):
          logging.info(f'EQUIPMENT: {label} {level}')
    
  def _slot(self, entity):
    raise NotImplementedError

  def _level(self, entity):
    return entity.level.val

  def use(self, entity):
    if self.equipped.val:
      self.unequip(entity, self._slot(entity))
    else:
      self.equip(entity, self._slot(entity))

class Armor(Equipment):
  def __init__(self, realm, level, **kwargs):
    defense = realm.config.EQUIPMENT_ARMOR_BASE_DEFENSE + \
              level*realm.config.EQUIPMENT_ARMOR_LEVEL_DEFENSE
    super().__init__(realm, level,
                     melee_defense=defense,
                     range_defense=defense,
                     mage_defense=defense,
                     **kwargs)
class Hat(Armor):
  ITEM_TYPE_ID = 2
  def _slot(self, entity):
    return entity.inventory.equipment.hat
class Top(Armor):
  ITEM_TYPE_ID = 3
  def _slot(self, entity):
    return entity.inventory.equipment.top
class Bottom(Armor):
  ITEM_TYPE_ID = 4
  def _slot(self, entity):
      return entity.inventory.equipment.bottom

class Weapon(Equipment):
  def __init__(self, realm, level, **kwargs):
    super().__init__(realm, level, **kwargs)
    self.attack = (
      realm.config.EQUIPMENT_WEAPON_BASE_DAMAGE +
      level*realm.config.EQUIPMENT_WEAPON_LEVEL_DAMAGE)

  def _slot(self, entity):
    return entity.inventory.equipment.weapon

class Sword(Weapon):
  ITEM_TYPE_ID = 5

  def __init__(self, realm, level, **kwargs):
    super().__init__(realm, level, **kwargs)
    self.melee_attack.update(self.attack)

  def _level(self, entity):
    return entity.skills.melee.level.val
class Bow(Weapon):
  ITEM_TYPE_ID = 6

  def __init__(self, realm, level, **kwargs):
    super().__init__(realm, level, **kwargs)
    self.range_attack.update(self.attack)

  def _level(self, entity):
    return entity.skills.range.level.val
class Wand(Weapon):
  ITEM_TYPE_ID = 7

  def __init__(self, realm, level, **kwargs):
    super().__init__(realm, level, **kwargs)
    self.mage_attack.update(self.attack)

  def _level(self, entity):
    return entity.skills.mage.level.val

class Tool(Equipment):
  def __init__(self, realm, level, **kwargs):
    defense = realm.config.EQUIPMENT_TOOL_BASE_DEFENSE + \
        level*realm.config.EQUIPMENT_TOOL_LEVEL_DEFENSE
    super().__init__(realm, level,
                      melee_defense=defense,
                      range_defense=defense,
                      mage_defense=defense,
                      **kwargs)
  
  def _slot(self, entity):
    return entity.inventory.equipment.held
class Rod(Tool):
  ITEM_TYPE_ID = 8
  def _level(self, entity):
    return entity.skills.fishing.level.val
class Gloves(Tool):
  ITEM_TYPE_ID = 9
  def _level(self, entity):
    return entity.skills.herbalism.level.val
class Pickaxe(Tool):
  ITEM_TYPE_ID = 10
  def _level(self, entity):
    return entity.skills.prospecting.level.val
class Chisel(Tool):
  ITEM_TYPE_ID = 11
  def _level(self, entity):
    return entity.skills.carving.level.val
class Arcane(Tool):
  ITEM_TYPE_ID = 12
  def _level(self, entity):
    return entity.skills.alchemy.level.val
class Ammunition(Equipment, Stack):
  def __init__(self, realm, level, **kwargs):
    super().__init__(realm, level, **kwargs)
    self.attack = (
      realm.config.EQUIPMENT_AMMUNITION_BASE_DAMAGE +
      level*realm.config.EQUIPMENT_AMMUNITION_LEVEL_DAMAGE)

  def _slot(self, entity):
    return entity.inventory.equipment.ammunition

  def fire(self, entity) -> int:
    if __debug__:
      assert self.quantity.val > 0, 'Used ammunition with 0 quantity'

    self.quantity.decrement()

    if self.quantity.val == 0:
      entity.inventory.remove(self)

    return self.damage


class Scrap(Ammunition):
  ITEM_TYPE_ID = 13

  def __init__(self, realm, level, **kwargs):
    super().__init__(realm, level, **kwargs)
    self.melee_attack.update(self.attack)

  def _level(self, entity):
    return entity.skills.melee.level.val  

  @property
  def damage(self):
    return self.melee_attack.val

class Shaving(Ammunition):
  ITEM_TYPE_ID = 14

  def __init__(self, realm, level, **kwargs):
    super().__init__(realm, level, **kwargs)
    self.range_attack.update(self.attack)

  def _level(self, entity):
    return entity.skills.range.level.val

  @property
  def damage(self):
    return self.range_attack.val

class Shard(Ammunition):
  ITEM_TYPE_ID = 15

  def __init__(self, realm, level, **kwargs):
    super().__init__(realm, level, **kwargs)
    self.mage_attack.update(self.attack)

  def _level(self, entity):
    return entity.skills.mage.level.val

  @property
  def damage(self):
    return self.mage_attack.val

class Consumable(Item):
  def use(self, entity) -> bool:
    if self._level(entity) < self.level.val:
      return False

    if self.config.LOG_MILESTONES and self.realm.quill.milestone.log_max(
      f'Consumed_{self.__class__.__name__()}', self.level.val) and self.config.LOG_VERBOSE:
        logging.info(" ".join(
          "PROF",
          self._log_name(),
          str(self.level.val),
          str(self.realm.quill.milestone.get(f"Consumed_{self._log_name()}")),
          str(entity.level.val)
        ))

    self._apply_effects(entity)
    entity.inventory.remove(self)
    return True
class Ration(Consumable):
  ITEM_TYPE_ID = 16

  def __init__(self, realm, level, **kwargs):
    restore = realm.config.PROFESSION_CONSUMABLE_RESTORE(level)
    super().__init__(realm, level, resource_restore=restore, **kwargs)

  def _apply_effects(self, entity):
    entity.resources.food.increment(self.resource_restore.val)
    entity.resources.water.increment(self.resource_restore.val)

class Poultice(Consumable):
  ITEM_TYPE_ID = 17

  def __init__(self, realm, level, **kwargs):
    restore = realm.config.PROFESSION_CONSUMABLE_RESTORE(level)
    super().__init__(realm, level, health_restore=restore, **kwargs)

  def _apply_effects(self, entity):
    entity.resources.health.increment(self.health_restore.val)
    entity.poultice_consumed += 1
    entity.poultice_level_consumed = max(
      entity.poultice_level_consumed, self.level.val)
