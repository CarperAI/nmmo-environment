from types import SimpleNamespace
from copy import deepcopy

import numpy as np
import numpy_indexed as npi

from nmmo.datastore.serialized import SerializedState
from nmmo.core.realm import Realm
from nmmo.entity import Entity
from nmmo.systems.item import Item
from nmmo.systems import skill as Skill

# pylint: disable=no-member
EventState = SerializedState.subclass("Event", [
  "id",
  "ent_id",
  "population_id",
  "tick",

  "event",

  "type",
  "level",
  "number",
  "gold",
  "target_eid",
  "target_pop"
])

EventState.Query = SimpleNamespace(
  table=lambda ds: ds.table("Event").where_neq(
    EventState.State.attr_name_to_col["id"], 0),

  by_event=lambda ds, event_code: ds.table("Event").where_eq(
    EventState.State.attr_name_to_col["event"], event_code),
)

# matching the names to base predicates
class EventCode:
  # Move
  EAT_FOOD = 1
  DRINK_WATER = 2

  # Attack
  SCORE_HIT = 11
  SCORE_KILL = 12
  style2int = { Skill.Melee: 1, Skill.Range:2, Skill.Mage:3 }
  attack_col_map = {
    'combat_style': EventState.State.attr_name_to_col['type'],
    'damage': EventState.State.attr_name_to_col['number'] }

  # Item
  CONSUME_ITEM = 21
  GIVE_ITEM = 22
  DESTROY_ITEM = 23
  PRODUCE_ITEM = 24
  item_col_map = {
    'item_type': EventState.State.attr_name_to_col['type'],
    'quantity': EventState.State.attr_name_to_col['number'],
    'price': EventState.State.attr_name_to_col['gold'] }

  # Exchange
  GIVE_GOLD = 31
  LIST_ITEM = 32
  EARN_GOLD = 33
  BUY_ITEM = 34
  SPEND_GOLD = 35


class EventLogger(EventCode):
  def __init__(self, realm: Realm):
    self.realm = realm
    self.config = realm.config
    self.datastore = realm.datastore

    self.valid_events = { val: evt for evt, val in EventCode.__dict__.items()
                           if isinstance(val, int) }

    # create a custom attr-col mapping
    self.attr2col = deepcopy(EventState.State.attr_name_to_col)
    self.attr2col.update(EventCode.attack_col_map)
    self.attr2col.update(EventCode.item_col_map)

  def reset(self):
    EventState.State.table(self.datastore).reset()

  # define event logging
  def _create_event(self, entity: Entity, event_code: int):
    log = EventState(self.datastore)
    log.id.update(log.datastore_record.id)
    log.ent_id.update(entity.ent_id)
    log.population_id.update(entity.population)
    log.tick.update(self.realm.tick)
    log.event.update(event_code)

    return log

  def record(self, event_code: int, entity: Entity, **kwargs):
    if event_code in [EventCode.EAT_FOOD, EventCode.DRINK_WATER,
                      EventCode.GIVE_ITEM, EventCode.DESTROY_ITEM,
                      EventCode.GIVE_GOLD]:
      # Logs for these events are for counting only
      self._create_event(entity, event_code)
      return

    if event_code == EventCode.SCORE_HIT:
      if ('combat_style' in kwargs and kwargs['combat_style'] in EventCode.style2int) & \
         ('damage' in kwargs and kwargs['damage'] >= 0):
        log = self._create_event(entity, event_code)
        log.type.update(EventCode.style2int[kwargs['combat_style']])
        log.number.update(kwargs['damage'])
        return

    if event_code == EventCode.SCORE_KILL:
      if ('target' in kwargs and isinstance(kwargs['target'], Entity)):
        target = kwargs['target']
        log = self._create_event(entity, event_code)
        log.target_eid.update(target.ent_id)
        log.target_pop.update(target.population)

        # CHECK ME: attack_level or "general" level?? need to clarify
        log.level.update(target.attack_level)
        return

    if event_code in [EventCode.CONSUME_ITEM, EventCode.PRODUCE_ITEM]:
      # CHECK ME: item types should be checked. For example,
      #   Only Ration and Poultice can be consumed
      #   Only Ration, Poultice, Scrap, Shaving, Shard can be produced
      if ('item' in kwargs and isinstance(kwargs['item'], Item)):
        item = kwargs['item']
        log = self._create_event(entity, event_code)
        log.type.update(item.ITEM_TYPE_ID)
        log.level.update(item.level.val)
        log.number.update(item.quantity.val)
        return

    if event_code in [EventCode.LIST_ITEM, EventCode.BUY_ITEM]:
      if ('item' in kwargs and isinstance(kwargs['item'], Item)) & \
         ('price' in kwargs and kwargs['price'] > 0):
        item = kwargs['item']
        log = self._create_event(entity, event_code)
        log.type.update(item.ITEM_TYPE_ID)
        log.level.update(item.level.val)
        log.number.update(item.quantity.val)
        log.gold.update(kwargs['price'])
        return

    if event_code in [EventCode.EARN_GOLD, EventCode.SPEND_GOLD]:
      if ('amount' in kwargs and kwargs['amount'] > 0):
        log = self._create_event(entity, event_code)
        log.gold.update(kwargs['amount'])
        return

    # If reached here, then something is wrong
    # CHECK ME: The below should be commented out after debugging
    raise ValueError(f"Event code: {event_code}", kwargs)

  def get_data(self, event_code=None):
    if event_code is None:
      return EventState.Query.table(self.datastore).astype(np.int16)

    if event_code in self.valid_events:
      return EventState.Query.by_event(self.datastore, event_code).astype(np.int16)

    return None

  def _group_by(self, flt_data, grpby_attr, sum_attr='id'):
    assert grpby_attr in ['ent_id', 'population_id'], "Invalid group-by attr"
    assert sum_attr in ['id', 'number', 'gold', 'damage', 'quantity', 'price'], \
      "Invalid sum_attr"
    g = npi.group_by(flt_data[:, self.attr2col[grpby_attr]])
    result = {}
    for k, v in zip(*g(flt_data[:,self.attr2col[sum_attr]])):
      if sum_attr == 'id':
        result[k] = sum(v) # SUM
      else:
        result[k] = len(v) # COUNT
    return result
