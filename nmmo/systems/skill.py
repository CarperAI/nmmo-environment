from __future__ import annotations

import abc

import numpy as np
from ordered_set import OrderedSet

from nmmo.lib import material
from nmmo.systems import combat
from nmmo.lib.log import EventCode

### Infrastructure ###
class ExperienceCalculator:
  def __init__(self, config):
    if not config.PROGRESSION_SYSTEM_ENABLED:
      return
    self.config = config
    self.exp_threshold = np.array(config.PROGRESSION_EXP_THRESHOLD)
    assert len(self.exp_threshold) >= config.PROGRESSION_LEVEL_MAX,\
      "PROGRESSION_LEVEL_BY_EXP must have at least PROGRESSION_LEVEL_MAX entries"
    self.max_exp = self.exp_threshold[self.config.PROGRESSION_LEVEL_MAX - 1]

  def exp_at_level(self, level):
    level = min(max(level, self.config.PROGRESSION_BASE_LEVEL),
                self.config.PROGRESSION_LEVEL_MAX)
    return int(self.exp_threshold[level - 1])

  def level_at_exp(self, exp):
    if exp >= self.max_exp:
      return self.config.PROGRESSION_LEVEL_MAX
    return np.argmin(exp >= self.exp_threshold)

class SkillGroup:
  def __init__(self, realm, entity):
    self.config  = realm.config
    self.realm   = realm
    self.entity = entity
    self.experience_calculator = ExperienceCalculator(self.config)
    self.skills  = OrderedSet() # critical for determinism

  def update(self):
    for skill in self.skills:
      skill.update()

  def packet(self):
    data = {}
    for skill in self.skills:
      data[skill.__class__.__name__.lower()] = skill.packet()
    return data

class Skill(abc.ABC):
  def __init__(self, skill_group: SkillGroup):
    self.realm = skill_group.realm
    self.config = skill_group.config
    self.entity = skill_group.entity
    self.experience_calculator = skill_group.experience_calculator
    self.skill_group = skill_group
    skill_group.skills.add(self)

  def packet(self):
    data = {}
    data['exp']   = self.exp.val
    data['level'] = self.level.val
    return data

  def add_xp(self, xp):
    self.exp.increment(xp)
    new_level = int(self.experience_calculator.level_at_exp(self.exp.val))

    if new_level > self.level.val:
      self.level.update(new_level)
      self.realm.event_log.record(EventCode.LEVEL_UP, self.entity,
                                  skill=self, level=new_level)

      self.realm.log_milestone(f'Level_{self.__class__.__name__}', new_level,
        f"PROGRESSION: Reached level {new_level} {self.__class__.__name__}",
        tags={"player_id": self.entity.ent_id})

  def set_experience_by_level(self, level):
    self.exp.update(self.experience_calculator.level_at_exp(level))
    self.level.update(int(level))

  # NOTE: All skills have harvest components
  # melee has prospecting, range has carving, mage has alchemy
  def has_tool(self, matl):
    if matl in [material.Water, material.Foilage]:  # no tools necessary for water and food
      return True

    tool = self.entity.equipment.held
    return matl.tool is not None and isinstance(tool.item, matl.tool)

  def process_drops(self, matl, drop_table):
    if not self.config.ITEM_SYSTEM_ENABLED:
      return

    entity = self.entity
    tool = entity.equipment.held

    # harvest without tool will only yield level-1 item even with high skill level
    # for example, fishing level=5 without rod will only yield level-1 ration
    level = 1
    if self.config.PROGRESSION_SYSTEM_ENABLED and \
       matl not in [material.Water, material.Foilage] and self.has_tool(matl):
      level = min(tool.item.level.val, self.config.PROGRESSION_LEVEL_MAX)

    for drop in drop_table.roll(self.realm, level):
      assert drop.level.val == level, 'Drop level does not match roll specification'

      self.realm.log_milestone(f'Gather_{drop.__class__.__name__}',
        level, f"PROFESSION: Gathered level {level} {drop.__class__.__name__} "
        f"(level {self.level.val} {self.__class__.__name__})",
        tags={"player_id": entity.ent_id})

      if entity.inventory.space:
        entity.inventory.receive(drop)
        self.realm.event_log.record(EventCode.HARVEST_ITEM, entity, item=drop)

  def harvest(self, matl, deplete=True):
    entity = self.entity
    realm  = self.realm

    r, c = entity.pos
    if realm.map.tiles[r, c].state != matl:
      return False

    if self.config.EQUIPMENT_SYSTEM_ENABLED and not self.has_tool(matl):
      # pylint: disable=protected-access
      if self.realm._np_random.random() > self.config.HARVEST_WITHOUT_TOOL_PROB:
        return False

    drop_table = realm.map.harvest(r, c, deplete)
    if drop_table:
      self.process_drops(matl, drop_table)

    return drop_table

  def harvest_adjacent(self, matl, deplete=True):
    entity = self.entity
    realm  = self.realm

    r, c = entity.pos
    drop_table = None

    if self.config.EQUIPMENT_SYSTEM_ENABLED and not self.has_tool(matl):
      # pylint: disable=protected-access
      if self.realm._np_random.random() > self.config.HARVEST_WITHOUT_TOOL_PROB:
        return False

    if realm.map.tiles[r-1, c].state == matl:
      drop_table = realm.map.harvest(r-1, c, deplete)
    elif realm.map.tiles[r+1, c].state == matl:
      drop_table = realm.map.harvest(r+1, c, deplete)
    elif realm.map.tiles[r, c-1].state == matl:
      drop_table = realm.map.harvest(r, c-1, deplete)
    elif realm.map.tiles[r, c+1].state == matl:
      drop_table = realm.map.harvest(r, c+1, deplete)

    if drop_table:
      self.process_drops(matl, drop_table)

    return drop_table

  @property
  def level(self):
    raise NotImplementedError(f"Skill {self.__class__.__name__} "\
      "does not implement 'level' property")

  @property
  def exp(self):
    raise NotImplementedError(f"Skill {self.__class__.__name__} "\
      "does not implement 'exp' property")

### Skill Bases ###
class CombatSkill(Skill):
  def process_drops(self, matl, drop_table):
    super().process_drops(matl, drop_table)
    if self.config.PROGRESSION_SYSTEM_ENABLED:
      self.add_xp(self.config.PROGRESSION_AMMO_HARVEST_XP_SCALE)

class DummyValue:
  def __init__(self, val=0):
    self.val = val

  def update(self, val):
    self.val = val

class NonCombatSkill(Skill):
  def __init__(self, skill_group: SkillGroup):
    super().__init__(skill_group)
    self._dummy_value = DummyValue()  # for water and food

  @property
  def level(self):
    return self._dummy_value

  @property
  def exp(self):
    return self._dummy_value

class ConsumableSkill(NonCombatSkill):
  def process_drops(self, matl, drop_table):
    super().process_drops(matl, drop_table)
    if self.config.PROGRESSION_SYSTEM_ENABLED:
      self.add_xp(self.config.PROGRESSION_CONSUMABLE_XP_SCALE)

### Skill groups ###
class Basic(SkillGroup):
  def __init__(self, realm, entity):
    super().__init__(realm, entity)
    self.water = Water(self)
    self.food  = Food(self)

class Harvest(SkillGroup):
  def __init__(self, realm, entity):
    super().__init__(realm, entity)
    self.fishing = Fishing(self)
    self.herbalism = Herbalism(self)

class Combat(SkillGroup):
  def __init__(self, realm, entity):
    super().__init__(realm, entity)

    # NOTE: All skills have harvest components
    # melee has prospecting, range has carving, mage has alchemy
    self.melee = Melee(self)
    self.range = Range(self)
    self.mage  = Mage(self)

  def packet(self):
    data          = super().packet()
    data['level'] = combat.level(self)
    return data

  def apply_damage(self, style):
    if self.config.PROGRESSION_SYSTEM_ENABLED:
      skill  = self.__dict__[style]
      skill.add_xp(self.config.PROGRESSION_ATTACK_XP_SCALE)

  def receive_damage(self, dmg):
    pass

class Skills(Basic, Harvest, Combat):
  pass

### Combat Skills, now cover harvest ###
class Melee(CombatSkill):
  SKILL_ID = 1

  @property
  def level(self):
    return self.entity.melee_level

  @property
  def exp(self):
    return self.entity.melee_exp

  def update(self):
    self.harvest(material.Ore)

class Range(CombatSkill):
  SKILL_ID = 2

  @property
  def level(self):
    return self.entity.range_level

  @property
  def exp(self):
    return self.entity.range_exp

  def update(self,):
    self.harvest(material.Tree)

class Mage(CombatSkill):
  SKILL_ID = 3

  @property
  def level(self):
    return self.entity.mage_level

  @property
  def exp(self):
    return self.entity.mage_exp

  def update(self):
    self.harvest(material.Crystal)

Melee.weakness = Mage
Range.weakness = Melee
Mage.weakness  = Range


### Basic/Harvest Skills ###
class Water(NonCombatSkill):
  def update(self):
    config = self.config
    if not config.RESOURCE_SYSTEM_ENABLED or config.IMMORTAL:
      return

    depletion = config.RESOURCE_DEPLETION_RATE
    water = self.entity.resources.water
    water.decrement(depletion)

    if not self.harvest_adjacent(material.Water, deplete=False):
      return

    restore = np.floor(config.RESOURCE_BASE * config.RESOURCE_HARVEST_RESTORE_FRACTION)
    water.increment(restore)
    self.realm.event_log.record(EventCode.DRINK_WATER, self.entity)

class Food(NonCombatSkill):
  def update(self):
    config = self.config
    if not config.RESOURCE_SYSTEM_ENABLED or config.IMMORTAL:
      return

    depletion = config.RESOURCE_DEPLETION_RATE
    food = self.entity.resources.food
    food.decrement(depletion)

    if not self.harvest(material.Foilage):
      return

    restore = np.floor(config.RESOURCE_BASE * config.RESOURCE_HARVEST_RESTORE_FRACTION)
    food.increment(restore)
    self.realm.event_log.record(EventCode.EAT_FOOD, self.entity)

class Fishing(ConsumableSkill):
  SKILL_ID = 4

  @property
  def level(self):
    return self.entity.fishing_level

  @property
  def exp(self):
    return self.entity.fishing_exp

  def update(self):
    self.harvest_adjacent(material.Fish)

class Herbalism(ConsumableSkill):
  SKILL_ID = 5

  @property
  def level(self):
    return self.entity.herbalism_level

  @property
  def exp(self):
    return self.entity.herbalism_exp

  def update(self):
    self.harvest(material.Herb)
