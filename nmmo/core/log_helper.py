from __future__ import annotations

# xcxc
# TODO(daveey): This is currently unused, as far as I can tell

from collections import defaultdict
from nmmo.core.agent import Agent
from nmmo.core.config import Config
from nmmo.core.realm import Realm

class LogHelper:
  @staticmethod
  def create(realm: Realm) -> LogHelper:
    if realm.config.LOG_ENV:
      return SimpleLogHelper(realm)
    else:
      return DummyLogHelper()

class DummyLogHelper(LogHelper):
  def reset(self) -> None:
    pass

  def update(self) -> None:
    pass

class SimpleLogHelper(LogHelper):
  def __init__(self, realm: Realm) -> None:
      self.realm = realm
      self.config = realm.config
      self.quill = realm.quill

  def reset(self):
    quill = quill

    quill.register('Basic/Lifetime', lambda player: player.history.time_alive.val)

    if self.config.TASKS:
      quill.register('Task/Completed', lambda player: player.diary.completed)
      quill.register('Task/Reward' , lambda player: player.diary.cumulative_reward)

    else:
      quill.register('Task/Completed', lambda player: player.history.time_alive.val)

    # Skills
    if self.config.PROGRESSION_SYSTEM_ENABLED:
      if self.config.COMBAT_SYSTEM_ENABLED:
        quill.register('Skill/Mage', lambda player: player.skills.mage.level.val)
        quill.register('Skill/Range', lambda player: player.skills.range.level.val)
        quill.register('Skill/Melee', lambda player: player.skills.melee.level.val)
      if self.config.PROFESSION_SYSTEM_ENABLED:
        quill.register('Skill/Fishing', lambda player: player.skills.fishing.level.val)
        quill.register('Skill/Herbalism', lambda player: player.skills.herbalism.level.val)
        quill.register('Skill/Prospecting', lambda player: player.skills.prospecting.level.val)
        quill.register('Skill/Carving', lambda player: player.skills.carving.level.val)
        quill.register('Skill/Alchemy', lambda player: player.skills.alchemy.level.val)
      if self.config.EQUIPMENT_SYSTEM_ENABLED:
        quill.register('Item/Held-Level', lambda player: player.inventory.equipment.held.item.level.val if player.inventory.equipment.held.item else 0)
        quill.register('Item/Equipment-Total', lambda player: player.equipment.total(lambda e: e.level))

    if self.config.EXCHANGE_SYSTEM_ENABLED:
        quill.register('Item/Wealth', lambda player: player.gold.val)

    # Item usage
    if self.config.PROFESSION_SYSTEM_ENABLED:
      quill.register('Item/Ration-Consumed', lambda player: player.ration_consumed)
      quill.register('Item/Poultice-Consumed', lambda player: player.poultice_consumed)
      quill.register('Item/Ration-Level', lambda player: player.ration_level_consumed)
      quill.register('Item/Poultice-Level', lambda player: player.poultice_level_consumed)

    # Market
    if self.config.EXCHANGE_SYSTEM_ENABLED:
      quill.register('Exchange/Player-Sells', lambda player: player.sells)
      quill.register('Exchange/Player-Buys',  lambda player: player.buys)


  def log_player(self, player: Agent) -> None:
    '''Logs player data upon death

    This function is called automatically when an agent dies
    to compute summary stats. You should not call it manually.
    Instead, override this method to customize logging.

    Args:
        player: An agent
    '''

    quill  = self.realm.quill
    policy = player.policy

    for key, fn in quill.shared.items():
        quill.log_player(f'{key}_{policy}', fn(player))

    # Duplicated task reward with/without name for SR calc
    if player.diary:
        if player.agent.scripted:
          player.diary.update(self.realm, player)

        quill.log_player(f'Task_Reward',     player.diary.cumulative_reward)

        for achievement in player.diary.achievements:
          quill.log_player(achievement.name, float(achievement.completed))
    else:
        quill.log_player(f'Task_Reward', player.history.time_alive.val)

    # Used for SR
    quill.log_player('PolicyID', player.agent.policyID)
    if player.diary:
        quill.log_player(f'Task_Reward', player.diary.cumulative_reward)

  def terminal(self):
    '''Logs currently alive agents and returns all collected logs

    Automatic log calls occur only when agents die. To evaluate agent
    performance over a fixed horizon, you will need to include logs for
    agents that are still alive at the end of that horizon. This function
    performs that logging and returns the associated a data structure
    containing logs for the entire evaluation

    Args:
        ent: An agent

    Returns:
        Log datastructure
    '''

    for entID, ent in self.realm.players.entities.items():
        self.log_player(ent)

    if self.config.SAVE_REPLAY:
        self.replay.save()

    return self.realm.quill.packet

  def log_env(self, env) -> None:
    '''Logs player data upon death

    This function is called automatically once per environment step
    to compute summary stats. You should not call it manually.
    Instead, override this method to customize logging.
    '''

    # This fn more or less repeats log_player once per tick
    # It was added to support eval-time logging
    # It needs to be redone to not duplicate player logging and
    # also not slow down training
    if not self.config.LOG_ENV:
        return 

    quill  = self.realm.quill

    if len(self.realm.players) == 0:
        return

    #Aggregate logs across env
    for key, fn in quill.shared.items():
      dat = defaultdict(list)
      for _, player in self.realm.players.items():
          name = player.agent.policy
          dat[name].append(fn(player))
      for policy, vals in dat.items():
          quill.log_env(f'{key}_{policy}', float(np.mean(vals)))

    if self.config.EXCHANGE_SYSTEM_ENABLED:
        for item in nmmo.systems.item.ItemID.item_ids:
            for level in range(1, 11):
                name = item.__name__
                key = (item, level)
                if key in self.realm.exchange.item_listings:
                    listing = self.realm.exchange.item_listings[key]
                    quill.log_env(f'Market/{name}-{level}_Price', listing.price if listing.price else 0)
                    quill.log_env(f'Market/{name}-{level}_Volume', listing.volume if listing.volume else 0)
                    quill.log_env(f'Market/{name}-{level}_Supply', listing.supply if listing.supply else 0)
                else:
                    quill.log_env(f'Market/{name}-{level}_Price', 0)
                    quill.log_env(f'Market/{name}-{level}_Volume', 0)
                    quill.log_env(f'Market/{name}-{level}_Supply', 0)
  
    for entID, ent in self.dead.items():
      self.log_player(ent)

  def max(self, fn):
    return max(fn(player) for player in self.realm.players.values())

  def max_held(self, policy):
    lvls = [player.equipment.held.level.val for player in self.realm.players.values()
            if player.equipment.held is not None and player.policy == policy]

    if len(lvls) == 0:
      return 0

    return max(lvls)

  def max_item(self, policy):
    lvls = [player.equipment.item_level for player in self.realm.players.values() if player.policy == policy]

    if len(lvls) == 0:
      return 0

    return max(lvls)

