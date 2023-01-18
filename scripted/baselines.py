from pdb import set_trace as T
from typing import Dict

from ordered_set import OrderedSet
from collections import defaultdict
import numpy as np
import random

import nmmo
from nmmo import material, Serialized
from nmmo.systems import skill, item
from nmmo.lib import colors
from nmmo.io import action
from nmmo.core.observation import Observation

from scripted import behavior, move, attack, utils


class Item:
    def __init__(self, item_obs):
        self.item_type = Serialized.Item.ItemType.attr(item_obs)
        self.item_class = item.Item.item_class(self.item_type)
        self.level    = Serialized.Item.Level.attr(item_obs)
        self.quantity = Serialized.Item.Quantity.attr(item_obs)
        self.price    = Serialized.Item.Price.attr(item_obs)
        self.instance = Serialized.Item.ID.attr(item_obs)
        self.equipped = Serialized.Item.Equipped.attr(item_obs)


class Scripted(nmmo.Agent):
    '''Template class for scripted models.

    You may either subclass directly or mirror the __call__ function'''
    scripted = True
    color    = colors.Neon.SKY
    def __init__(self, config, idx):
        '''
        Args:
           config : A forge.blade.core.Config object or subclass object
        ''' 
        super().__init__(config, idx)
        self.health_max = config.PLAYER_BASE_HEALTH

        if config.RESOURCE_SYSTEM_ENABLED:
            self.food_max   = config.RESOURCE_BASE
            self.water_max  = config.RESOURCE_BASE

        self.spawnR    = None
        self.spawnC    = None

    @property
    def policy(self):
       return self.__class__.__name__

    @property
    def forage_criterion(self) -> bool:
        '''Return true if low on food or water'''
        min_level = 7 * self.config.RESOURCE_DEPLETION_RATE
        return self.food <= min_level or self.water <= min_level

    def forage(self):
        '''Min/max food and water using Dijkstra's algorithm'''
        move.forageDijkstra(self.config, self.ob, self.actions, self.food_max, self.water_max)

    def gather(self, resource):
        '''BFS search for a particular resource'''
        return move.gatherBFS(self.config, self.ob, self.actions, resource)

    def explore(self):
        '''Route away from spawn'''
        move.explore(self.config, self.ob, self.actions, self.r, self.c)

    @property
    def downtime(self):
        '''Return true if agent is not occupied with a high-priority action'''
        return not self.forage_criterion and self.attacker is None

    def evade(self):
        '''Target and path away from an attacker'''
        move.evade(self.config, self.ob, self.actions, self.attacker)
        self.target     = self.attacker
        self.targetID   = self.attackerID
        self.targetDist = self.attackerDist

    def attack(self):
        '''Attack the current target'''
        if self.target is not None:
           assert self.targetID is not None
           style = random.choice(self.style)
           attack.target(self.config, self.actions, style, self.targetID)

    def target_weak(self):
        '''Target the nearest agent if it is weak'''
        if self.closest is None:
            return False

        selfLevel  = self.me.attribute(Serialized.Entity.Level)
        targLevel  = self.closest.attribute(Serialized.Entity.Level)
        population = self.closest.attribute(Serialized.Entity.Population)
        
        if population == -1 or targLevel <= selfLevel <= 5 or selfLevel >= targLevel + 3:
           self.target     = self.closest
           self.targetID   = self.closestID
           self.targetDist = self.closestDist

    def scan_agents(self):
        '''Scan the nearby area for agents'''
        self.closest, self.closestDist   = attack.closestTarget(self.config, self.ob)
        self.attacker, self.attackerDist = attack.attacker(self.config, self.ob)

        self.closestID = None
        if self.closest is not None:
           self.closestID = self.closest.attribute(Serialized.Entity.ID)

        self.attackerID = None
        if self.attacker is not None:
           self.attackerID = self.attacker.attribute(Serialized.Entity.ID)

        self.target     = None
        self.targetID   = None
        self.targetDist = None

    def adaptive_control_and_targeting(self, explore=True):
        '''Balanced foraging, evasion, and exploration'''
        self.scan_agents()

        if self.attacker is not None:
           self.evade()
           return

        if self.fog_criterion:
           self.explore()
        elif self.forage_criterion or not explore:
           self.forage()
        else:
           self.explore()

        self.target_weak()

    def process_inventory(self):
        if not self.config.ITEM_SYSTEM_ENABLED:
            return

        self.inventory   = OrderedSet()
        self.best_items: Dict[int, Item]   = {}
        self.item_counts = defaultdict(int)

        self.item_levels = {
                item.Hat: self.level,
                item.Top: self.level,
                item.Bottom: self.level,
                item.Sword: self.melee,
                item.Bow: self.range,
                item.Wand: self.mage,
                item.Rod: self.fishing,  
                item.Gloves: self.herbalism,
                item.Pickaxe: self.prospecting,
                item.Chisel: self.carving,
                item.Arcane: self.alchemy,
                item.Scrap: self.melee,
                item.Shaving: self.range,
                item.Shard: self.mage}


        self.gold = Serialized.Entity.Gold.attr(self.me)

        for item_ary in self.ob.inventory:
           itm = Item(item_ary)
           assert itm.item_class.__name__ == 'Gold' or itm.quantity != 0

           self.item_counts[itm.item_type] += itm.quantity
           self.inventory.add(itm)

           # Too high level to equip
           if itm.item_type in self.item_levels and itm.level > self.item_levels[itm.item_type]:
              continue

           # Best by default
           if itm.item_class not in self.best_items:
              self.best_items[itm.item_type] = itm

           best_itm = self.best_items[itm.item_type]

           if itm.level > best_itm.level:
              self.best_items[itm.item_type] = itm

    def upgrade_heuristic(self, current_level, upgrade_level, price):
        return (upgrade_level - current_level) / max(price, 1)

    def process_market(self):
        if not self.config.EXCHANGE_SYSTEM_ENABLED:
            return

        self.market         = OrderedSet()
        self.best_heuristic = {}

        for item_ary in self.ob.market:
           itm = Item(item_ary)

           self.market.add(itm)

           # Prune Unaffordable
           if itm.price > self.gold:
              continue

           # Too high level to equip
           if itm.item_type in self.item_levels and itm.level > self.item_levels[itm.item_type] :
              continue

           #Current best item level
           current_level = 0
           if itm.item_type in self.best_items:
               current_level = self.best_items[itm.item_type].level

           itm.heuristic = self.upgrade_heuristic(current_level, itm.level, itm.price)

           #Always count first item
           if itm.item_type not in self.best_heuristic:
               self.best_heuristic[itm.item_type] = itm
               continue

           #Better heuristic value
           if itm.heuristic > self.best_heuristic[itm.item_type].heuristic:
               self.best_heuristic[itm.item_type] = itm

    def equip(self, items: set):
        for item_type, itm in self.best_items.items():
            if item_type not in items:
               continue

            if itm.equipped:
               continue

            self.actions[action.Use] = {
               action.Item: itm.instance}
           
            return True
 
    def consume(self):
        if self.health <= self.health_max // 2 and item.Poultice in self.best_items:
            itm = self.best_items[item.Poultice.ITEM_TYPE_ID]
        elif (self.food == 0 or self.water == 0) and item.Ration in self.best_items:
            itm = self.best_items[item.Ration.ITEM_TYPE_ID]
        else:
            return

        self.actions[action.Use] = {
           action.Item: itm.instance}
 
    def sell(self, keep_k: dict, keep_best: set):
        for itm in self.inventory:
            price = itm.level

            if itm.item_class == item.Gold:
                continue

            assert itm.quantity > 0

            if itm.item_type in keep_k:
                owned = self.item_counts[itm.item_type]
                k     = keep_k[itm.item_type]
                if owned <= k:
                    continue
 
            #Exists an equippable of the current class, best needs to be kept, and this is the best item
            if itm.item_type in self.best_items and \
                itm.item_type in keep_best and \
                itm.instance == self.best_items[itm.item_type].instance:
                continue

            self.actions[action.Sell] = {
                action.Item: itm.instance,
                action.Price: action.Price.edges[int(price)]}

            return itm

    def buy(self, buy_k: dict, buy_upgrade: set):
        if len(self.inventory) >= self.config.ITEM_INVENTORY_CAPACITY:
            return

        # xcxc not used, is this a bug?
        purchase = None
        best = list(self.best_heuristic.items())
        random.shuffle(best)
        for item_type, itm in best:
            # Buy top k
            if item_type in buy_k:
                owned = self.item_counts[item_type]
                k = buy_k[item_type]
                if owned < k:
                   purchase = itm

            #Check if item desired
            if item_type not in buy_upgrade:
                continue

            #Check is is an upgrade
            if itm.heuristic <= 0:
                continue

            #Buy best heuristic upgrade
            self.actions[action.Buy] = {
                    action.Item: itm.instance}

            return itm

    def exchange(self):
        if not self.config.EXCHANGE_SYSTEM_ENABLED:
            return

        self.process_market()
        self.sell(keep_k=self.supplies, keep_best=self.wishlist)
        self.buy(buy_k=self.supplies, buy_upgrade=self.wishlist)

    def use(self):
        self.process_inventory()
        if self.config.EQUIPMENT_SYSTEM_ENABLED and not self.consume():
            self.equip(items=self.wishlist)

    def __call__(self, observation: Observation):
        '''Process observations and return actions'''
        self.actions = {}

        self.ob = observation
        self.me = observation.agent()

        # Time Alive
        self.timeAlive = self.me.attribute(Serialized.Entity.TimeAlive)

        # Pos
        self.r = self.me.attribute(Serialized.Entity.R)
        self.c = self.me.attribute(Serialized.Entity.C)

        #Resources
        self.health = self.me.attribute(Serialized.Entity.Health)
        self.food   = self.me.attribute(Serialized.Entity.Food)
        self.water  = self.me.attribute(Serialized.Entity.Water)

       
        #Skills
        self.melee       = self.me.attribute(Serialized.Entity.Melee)
        self.range       = self.me.attribute(Serialized.Entity.Range)
        self.mage        = self.me.attribute(Serialized.Entity.Mage)
        self.fishing     = self.me.attribute(Serialized.Entity.Fishing)
        self.herbalism   = self.me.attribute(Serialized.Entity.Herbalism)
        self.prospecting = self.me.attribute(Serialized.Entity.Prospecting)
        self.carving     = self.me.attribute(Serialized.Entity.Carving)
        self.alchemy     = self.me.attribute(Serialized.Entity.Alchemy)

        #Combat level
        # TODO: Get this from agent properties
        self.level       = max(self.melee, self.range, self.mage,
                               self.fishing, self.herbalism,
                               self.prospecting, self.carving, self.alchemy)
 
        self.skills = {
              skill.Melee: self.melee,
              skill.Range: self.range,
              skill.Mage: self.mage,
              skill.Fishing: self.fishing,
              skill.Herbalism: self.herbalism,
              skill.Prospecting: self.prospecting,
              skill.Carving: self.carving,
              skill.Alchemy: self.alchemy}

        if self.spawnR is None:
            self.spawnR = self.me.attribute(Serialized.Entity.R)
        if self.spawnC is None:
            self.spawnC = self.me.attribute(Serialized.Entity.C)

        # When to run from death fog in BR configs
        self.fog_criterion = None
        if self.config.PLAYER_DEATH_FOG is not None:
            start_running = self.timeAlive > self.config.PLAYER_DEATH_FOG - 64
            run_now = self.timeAlive % max(1, int(1 / self.config.PLAYER_DEATH_FOG_SPEED))
            self.fog_criterion = start_running and run_now


class Random(Scripted):
    '''Moves randomly'''
    def __call__(self, obs):
        super().__call__(obs)

        move.random(self.config, self.ob, self.actions)
        return self.actions

class Meander(Scripted):
    '''Moves randomly on safe terrain'''
    def __call__(self, obs):
        super().__call__(obs)

        move.meander(self.config, self.ob, self.actions)
        return self.actions

class Explore(Scripted):
    '''Actively explores towards the center'''
    def __call__(self, obs):
        super().__call__(obs)

        self.explore()

        return self.actions

class Forage(Scripted):
    '''Forages using Dijkstra's algorithm and actively explores'''
    def __call__(self, obs):
        super().__call__(obs)

        if self.forage_criterion:
           self.forage()
        else:
           self.explore()

        return self.actions

class Combat(Scripted):
    '''Forages, fights, and explores'''
    def __init__(self, config, idx):
        super().__init__(config, idx)
        self.style  = [action.Melee, action.Range, action.Mage]

    @property
    def supplies(self):
        return {item.Ration: 2, item.Poultice: 2, self.ammo: 10}

    @property
    def wishlist(self):
        return {
            item.Hat.ITEM_TYPE_ID, 
            item.Top,
            item.Bottom, 
            self.weapon,
            self.ammo
        }

    def __call__(self, obs):
        super().__call__(obs)
        self.use()
        self.exchange()

        self.adaptive_control_and_targeting()
        self.attack()

        return self.actions

class Gather(Scripted):
    '''Forages, fights, and explores'''
    def __init__(self, config, idx):
        super().__init__(config, idx)
        self.resource = [material.Fish, material.Herb, material.Ore, material.Tree, material.Crystal]

    @property
    def supplies(self):
        return {item.Ration: 2, item.Poultice: 2}

    @property
    def wishlist(self):
        return {item.Hat, item.Top, item.Bottom, self.tool}

    def __call__(self, obs):
        super().__call__(obs)
        self.use()
        self.exchange()

        if self.forage_criterion:
           self.forage()
        elif self.fog_criterion or not self.gather(self.resource):
           self.explore()

        return self.actions

class Fisher(Gather):
    def __init__(self, config, idx):
        super().__init__(config, idx)
        if config.SPECIALIZE:
            self.resource = [material.Fish]
        self.tool     = item.Rod

class Herbalist(Gather):
    def __init__(self, config, idx):
        super().__init__(config, idx)
        if config.SPECIALIZE:
            self.resource = [material.Herb]
        self.tool     = item.Gloves

class Prospector(Gather):
    def __init__(self, config, idx):
        super().__init__(config, idx)
        if config.SPECIALIZE:
            self.resource = [material.Ore]
        self.tool     = item.Pickaxe

class Carver(Gather):
    def __init__(self, config, idx):
        super().__init__(config, idx)
        if config.SPECIALIZE:
            self.resource = [material.Tree]
        self.tool     = item.Chisel

class Alchemist(Gather):
    def __init__(self, config, idx):
        super().__init__(config, idx)
        if config.SPECIALIZE:
            self.resource = [material.Crystal]
        self.tool     = item.Arcane

class Melee(Combat):
    def __init__(self, config, idx):
        super().__init__(config, idx)
        if config.SPECIALIZE:
            self.style  = [action.Melee]
        self.weapon = item.Sword
        self.ammo   = item.Scrap

class Range(Combat):
    def __init__(self, config, idx):
        super().__init__(config, idx)
        if config.SPECIALIZE:
            self.style  = [action.Range]
        self.weapon = item.Bow
        self.ammo   = item.Shaving

class Mage(Combat):
    def __init__(self, config, idx):
        super().__init__(config, idx)
        if config.SPECIALIZE:
            self.style  = [action.Mage]
        self.weapon = item.Wand
        self.ammo   = item.Shard
