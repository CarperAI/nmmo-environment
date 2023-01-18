
import numpy as np

from nmmo.lib import utils
from nmmo.lib.serialized import SerializedAttributeDef as Attr
from nmmo.lib.serialized import SerializedState
from nmmo.systems import combat, inventory

EntityState = SerializedState.subclass(
   "Entity", lambda config: [
      Attr("id", min=-np.inf),
      Attr("population_id", min=-3, #NPC index, 
                         max=config.PLAYER_POLICIES-1),
      Attr("r", min=0, max=config.MAP_SIZE-1),
      Attr("c", min=0, max=config.MAP_SIZE-1),

      # Status
      Attr("level"),
      Attr("damage"),
      Attr("time_alive"),
      Attr("freeze", max=3),
      Attr("item_level", max=5*config.NPC_LEVEL_MAX),
      Attr("attacker_id", min=-np.inf),
      Attr("message", max=config.COMMUNICATION_NUM_TOKENS),

      # Resources
      Attr("gold"),
      Attr("health", max=config.PLAYER_BASE_HEALTH),
      Attr("food", max=config.RESOURCE_BASE),
      Attr("water", max=config.RESOURCE_BASE),

      # Combat
      Attr("melee_level", max=config.PROGRESSION_LEVEL_MAX),
      Attr("food", max=config.RESOURCE_BASE),
      Attr("range_level", max=config.PROGRESSION_LEVEL_MAX),
      Attr("mage_level", max=config.PROGRESSION_LEVEL_MAX),

      # Skills
      Attr("fishing_level", max=config.PROGRESSION_LEVEL_MAX),
      Attr("herbalism_level", max=config.PROGRESSION_LEVEL_MAX),
      Attr("prospecting_level", max=config.PROGRESSION_LEVEL_MAX),
      Attr("carving_level", max=config.PROGRESSION_LEVEL_MAX),
      Attr("alchemy_level", max=config.PROGRESSION_LEVEL_MAX),
   ])
   

class Resources:
   def __init__(self, ent, config):
    self.config = config
    self.health = ent.health
    self.water  = ent.water
    self.food   = ent.food

    self.health.update(config.PLAYER_BASE_HEALTH)
    self.water.update(config.RESOURCE_BASE)
    self.food.update(config.RESOURCE_BASE)


   def update(self):
      if not self.config.RESOURCE_SYSTEM_ENABLED:
         return

      regen  = self.config.RESOURCE_HEALTH_RESTORE_FRACTION
      thresh = self.config.RESOURCE_HEALTH_REGEN_THRESHOLD

      food_thresh  = self.food  > thresh * self.config.RESOURCE_BASE
      water_thresh = self.water > thresh * self.config.RESOURCE_BASE

      if food_thresh and water_thresh:
          restore = np.floor(self.health.max * regen)
          self.health.increment(restore)

      if self.food.empty:
          self.health.decrement(self.config.RESOURCE_STARVATION_RATE)

      if self.water.empty:
          self.health.decrement(self.config.RESOURCE_DEHYDRATION_RATE)

   def packet(self):
      data = {}
      data['health'] = self.health.packet()
      data['food']   = self.food.packet()
      data['water']  = self.water.packet()
      return data

class Status:
   def __init__(self, ent):
      self.freeze = ent.freeze

   def update(self, realm, entity, actions):
      self.freeze.decrement()

   def packet(self):
      data = {}
      data['freeze'] = self.freeze.val
      return data

class History:
   def __init__(self, ent):
      self.actions = {}
      self.attack  = None
  
      self.starting_position = ent.pos
      self.exploration = 0
      self.player_kills = 0

      self.damage_received = 0
      self.damage_inflicted = 0

      self.damage    = ent.damage
      self.time_alive = ent.time_alive

      self.lastPos = None

   def update(self, realm, entity, actions):
      self.attack  = None
      self.damage.update(0)

      self.actions = {}
      if entity.entID in actions:
          self.actions = actions[entity.entID]
 
      exploration = utils.linf(entity.pos, self.starting_position)
      self.exploration = max(exploration, self.exploration)

      self.time_alive.increment()

   def packet(self):
      data = {}
      data['damage']    = self.damage.val
      data['timeAlive'] = self.time_alive.val
      data['damage_inflicted'] = self.damage_inflicted
      data['damage_received'] = self.damage_received

      if self.attack is not None:
         data['attack'] = self.attack

      actions = {}
      for atn, args in self.actions.items():
         atn_packet = {}

         #Avoid recursive player packet
         if atn.__name__ == 'Attack':
             continue

         for key, val in args.items():
            if hasattr(val, 'packet'):
               atn_packet[key.__name__] = val.packet
            else:
               atn_packet[key.__name__] = val.__name__
         actions[atn.__name__] = atn_packet
      data['actions'] = actions

      return data

class Entity(EntityState):
   def __init__(self, realm, pos, entity_id, name, color, population_id):
      super().__init__(realm.datastore, realm.config)

      self.realm = realm
      self.config       = realm.config

      self.policy       = name
      self.entity_id = entity_id
      self.repr         = None

      self.name  = name + str(entity_id)
      self.color = color
      r, c = pos

      self.r.update(r)
      self.c.update(c)
      self.population_id.update(population_id)
      self.id.update(entity_id)

      # xcxc should this come from config?
      self.level.update(3)

      # xcxc should this come from config?
      self.vision       = 5

      self.attacker     = None
      self.target       = None
      self.closest      = None
      self.spawn_pos     = pos

      # Submodules
      self.status    = Status(self)
      self.history   = History(self)
      self.resources = Resources(self, self.config)
      self.inventory = inventory.Inventory(realm, self)

   def packet(self):
      data = {}

      data['status']    = self.status.packet()
      data['history']   = self.history.packet()
      data['inventory'] = self.inventory.packet()
      data['alive']     = self.alive

      return data

   def base_packet(self):
      data = {}

      data['r']          = self.r.val
      data['c']          = self.c.val
      data['name']       = self.name
      data['level']      = self.attack_level.val
      data['item_level'] = self.item_level.val
      data['color']      = self.color.packet()
      data['population'] = self.population.val
      data['self']       = self.self.val

      return data

   def update(self, realm, actions):
      '''Update occurs after actions, e.g. does not include history'''
      if self.history.damage == 0:
         self.attacker = None
         self.attacker_id.update(0)

      self.level.update(combat.level(self.skills))

      if realm.config.EQUIPMENT_SYSTEM_ENABLED:
         self.item_level.update(self.equipment.total(lambda e: e.level))

      if realm.config.EXCHANGE_SYSTEM_ENABLED:
         self.gold.update(self.inventory.gold.quantity.val)

      self.status.update(realm, self, actions)
      self.history.update(realm, self, actions)

   def receiveDamage(self, source, dmg):
      self.history.damage_received += dmg
      self.history.damage.update(dmg)
      self.resources.health.decrement(dmg)

      if self.alive:
          return True

      if source is None:
          return True 

      if not source.isPlayer:
          return True 

      return False

   def applyDamage(self, dmg, style):
      self.history.damage_inflicted += dmg

   @property
   def pos(self):
      return self.r.val, self.c.val

   @property
   def alive(self):
      if self.resources.health.empty:
         return False

      return True

   @property
   def isPlayer(self) -> bool:
      return False

   @property
   def isNPC(self) -> bool:
      return False

   @property
   def attack_level(self) -> int:
       melee  = self.skills.melee.level.val
       ranged = self.skills.range.level.val
       mage   = self.skills.mage.level.val

       return int(max(melee, ranged, mage))
