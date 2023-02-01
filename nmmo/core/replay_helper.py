from __future__ import annotations

from nmmo.core.replay import Replay

class ReplayHelper():
  @staticmethod
  def create(realm) -> ReplayHelper:
    if realm.config.SAVE_REPLAY:
      return SimpleReplayHelper(realm)
    return DummyReplayHelper()


class DummyReplayHelper(ReplayHelper):
  def update(self) -> None:
    pass

class SimpleReplayHelper(ReplayHelper):
  def __init__(self, realm) -> None:
    self.realm = realm
    self.config = realm.config
    self.replay = Replay(self.config)
    self.packet = None
    self.overlay = None

  def update(self) -> None:
    if self.config.RENDER or self.config.SAVE_REPLAY:
      packet = {
        'config': self.config,
        'wilderness': 0
      }

      packet = {**self.realm.packet(), **packet}

      if self.overlay is not None:
        packet['overlay'] = self.overlay

    self.packet = packet

    if self.config.SAVE_REPLAY:
      self.replay.update(packet)
