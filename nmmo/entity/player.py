

from nmmo.systems.skill import Skills
from nmmo.systems.achievement import Diary
from nmmo.systems import combat
from nmmo.entity import entity

# pylint: disable=no-member
class Player(entity.Entity):
  def __init__(self, realm, pos, agent, color, pop):
    super().__init__(realm, pos, agent.iden, agent.policy, color, pop)

    self.agent    = agent
    self.pop      = pop
    self.immortal = realm.config.IMMORTAL

    # Scripted hooks
    self.target = None
    self.vision = 7

    # Logs
    self.buys                     = 0
    self.sells                    = 0
    self.ration_consumed          = 0
    self.poultice_consumed        = 0
    self.ration_level_consumed    = 0
    self.poultice_level_consumed  = 0

    # Submodules
    self.skills = Skills(realm, self)

    self.diary  = None
    tasks = realm.config.TASKS
    if tasks:
      self.diary = Diary(self, tasks)

  @property
  def serial(self):
    return self.population_id, self.entID

  @property
  def is_player(self) -> bool:
    return True

  @property
  def population(self):
    if __debug__:
      assert self.population_id.val == self.pop
    return self.pop

  @property
  def level(self) -> int:
    return combat.level(self.skills)

  def apply_damage(self, dmg, style):
    super().apply_damage(dmg, style)
    self.skills.apply_damage(style)

  # TODO(daveey): The returns for this function are a mess
  def receive_damage(self, source, dmg):
    if self.immortal:
      return False

    if super().receive_damage(source, dmg):
      return True

    if not self.config.ITEM_SYSTEM_ENABLED:
      return False

    for item in list(self.inventory.items):
      if not item.quantity.val:
        continue

      self.inventory.remove(item)
      source.inventory.receive(item)

    if not super().receive_damage(source, dmg):
      if source:
        source.history.player_kills += 1
      return False

    self.skills.receive_damage(dmg)
    return False

  @property
  def equipment(self):
    return self.inventory.equipment

  def packet(self):
    data = super().packet()

    data['entID']     = self.entID
    data['annID']     = self.population

    data['resource']  = self.resources.packet()
    data['skills']    = self.skills.packet()
    data['inventory'] = self.inventory.packet()

    return data

  def update(self, realm, actions):
    '''Post-action update. Do not include history'''
    super().update(realm, actions)

    # Spawsn battle royale style death fog
    # Starts at 0 damage on the specified config tick
    # Moves in from the edges by 1 damage per tile per tick
    # So after 10 ticks, you take 10 damage at the edge and 1 damage
    # 10 tiles in, 0 damage in farther
    # This means all agents will be force killed around
    # MAP_CENTER / 2 + 100 ticks after spawning
    fog = self.config.PLAYER_DEATH_FOG
    if fog is not None and self.realm.tick >= fog:
      row, col = self.pos
      cent = self.config.MAP_BORDER + self.config.MAP_CENTER // 2

      # Distance from center of the map
      dist = max(abs(row - cent), abs(col - cent))

      # Safe final area
      if dist > self.config.PLAYER_DEATH_FOG_FINAL_SIZE:
        # Damage based on time and distance from center
        time_dmg = self.config.PLAYER_DEATH_FOG_SPEED * (self.realm.tick - fog + 1)
        dist_dmg = dist - self.config.MAP_CENTER // 2
        dmg = max(0, dist_dmg + time_dmg)
        self.receive_damage(None, dmg)

    if not self.alive:
      return

    self.resources.update()
    self.skills.update()

    if self.diary:
      self.diary.update(realm)
