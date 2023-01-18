from pdb import set_trace as T
from typing import Dict, Tuple
import numpy as np

from ordered_set import OrderedSet
import logging

from nmmo.systems import item as Item 
class EquipmentSlot:
  def __init__(self) -> None:
    self.item = None
  
  def equip(self, item: Item.Item) -> None:
    self.item = item

  def unequip(self) -> None:
    self.item = None

class Equipment:
  def __init__(self):
    self.hat = EquipmentSlot()
    self.top = EquipmentSlot()
    self.bottom = EquipmentSlot()
    self.held = EquipmentSlot() 
    self.ammunition = EquipmentSlot()

  def total(self, lambda_getter):
    items = [lambda_getter(e).val for e in self]
    if not items:
      return 0
    return sum(items)

  def __iter__(self):
    for slot in [self.hat, self.top, self.bottom, self.held, self.ammunition]:
      if slot.item is not None:
        yield slot.item

  def conditional_packet(self, packet, slot_name: str, slot: EquipmentSlot):
    if slot.item:
      packet[slot_name] = slot.item.packet

  @property
  def item_level(self):
    return self.total(lambda e: e.level)

  @property
  def melee_attack(self):
    return self.total(lambda e: e.melee_attack)

  @property
  def range_attack(self):
    return self.total(lambda e: e.range_attack)

  @property
  def mage_attack(self):
    return self.total(lambda e: e.mage_attack)

  @property
  def melee_defense(self):
    return self.total(lambda e: e.melee_defense)

  @property
  def range_defense(self):
    return self.total(lambda e: e.range_defense)

  @property
  def mage_defense(self):
    return self.total(lambda e: e.mage_defense)

  @property
  def packet(self):
    packet = {}

    self.conditional_packet(packet, 'hat',        self.hat)
    self.conditional_packet(packet, 'top',        self.top)
    self.conditional_packet(packet, 'bottom',     self.bottom)
    self.conditional_packet(packet, 'held',       self.held)
    self.conditional_packet(packet, 'ammunition', self.ammunition)

    packet['item_level']    = self.item_level

    packet['melee_attack']  = self.melee_attack
    packet['range_attack']  = self.range_attack
    packet['mage_attack']   = self.mage_attack
    packet['melee_defense'] = self.melee_defense
    packet['range_defense'] = self.range_defense
    packet['mage_defense']  = self.mage_defense

    return packet


class Inventory:
  def __init__(self, realm, entity):
    config           = realm.config
    self.realm       = realm
    self.entity      = entity
    self.config      = config

    self.equipment   = Equipment()

    if not config.ITEM_SYSTEM_ENABLED:
        return

    self.capacity         = config.ITEM_INVENTORY_CAPACITY
    # xcxc
    # self.gold             = Item.Gold(realm)
    # self.gold.owner.update(entity.datastore_object.id)

    self._item_stacks: Dict[Tuple, Item.Stack] = {
      # self.gold.signature: self.gold
    }
    self._items: OrderedSet[Item.Item] = OrderedSet([
      # self.gold
    ])

  @property
  def space(self):
    return self.capacity - len(self._items)

  def packet(self):
    item_packet = []
    if self.config.ITEM_SYSTEM_ENABLED:
        item_packet = [e.packet for e in self._items]

    return {
          'items':     item_packet,
          'equipment': self.equipment.packet}

  def __iter__(self):
    for item in self._items:
      yield item

  def receive(self, item):
    assert isinstance(item, Item.Item), f'{item} received is not an Item instance'
    assert item not in self._items, f'{item} object received already in inventory'
    assert not item.equipped.val, f'Received equipped item {item}'
    assert item.quantity.val, f'Received empty item {item}'

    config = self.config

    if isinstance(item, Item.Stack):
        signature = item.signature
        if signature in self._item_stacks:
            stack = self._item_stacks[signature]
            assert item.level.val == stack.level.val, f'{item} stack level mismatch'
            stack.quantity += item.quantity.val

            if config.LOG_MILESTONES and isinstance(item, Item.Gold) and self.realm.quill.milestone.log_max(f'Wealth', self.gold.quantity.val) and config.LOG_VERBOSE:
                logging.info(f'EXCHANGE: Total wealth {self.gold.quantity.val} gold')
            
            return
        elif not self.space:
            return

        self._item_stacks[signature] = item

    if not self.space:
        return

    if config.LOG_MILESTONES and self.realm.quill.milestone.log_max(f'Receive_{item.__class__.__name__}', item.level.val) and config.LOG_VERBOSE:
        logging.info(f'INVENTORY: Received level {item.level.val} {item.__class__.__name__}')

    item.owner.update(self.entity.datastore_object.id)
    self._items.add(item)

  def remove(self, item, quantity=None):
    assert isinstance(item, Item.Item), f'{item} removing item is not an Item instance'
    assert item in self._items, f'No item {item} to remove'

    if isinstance(item, Item.Equipment) and item.equipped.val:
      item.unequip(self.entity)

    if isinstance(item, Item.Stack):
        signature = item.signature 

        assert item.signature in self._item_stacks, f'{item} stack to remove not in inventory'
        stack = self._item_stacks[signature]

        if quantity is None or stack.quantity.val == quantity:
          self._items.remove(stack)
          del self._item_stacks[signature]
          return

        assert 0 < quantity <= stack.quantity.val, f'Invalid remove {quantity} x {item} ({stack.quantity.val} available)'
        stack.quantity.val -= quantity

        return

    item.owner.update(0)
    self._items.remove(item)
