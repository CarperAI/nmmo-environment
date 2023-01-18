from nmmo.core.replay import Replay

# xcxc create a null replay helper
class ReplayHelper():
  def __init__(self, config, realm) -> None:
    self.config = config
    self.realm = realm
    self.replay = Replay(self.config)

def update(self) -> None:
  if self.config.RENDER or self.config.SAVE_REPLAY:
    packet = {
      'config': self.config,
      'pos': self.env.overlayPos,
      'wilderness': 0
    }

    packet = {**self.realm.packet(), **packet}

    if self.overlay is not None:
      packet['overlay'] = self.overlay
      self.overlay      = None

  self.packet = packet

  if self.config.SAVE_REPLAY:
    self.replay.update(packet)