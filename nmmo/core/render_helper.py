# pylint: disable=all

from __future__ import annotations
import numpy as np

from nmmo.overlay import OverlayRegistry

class RenderHelper:
  @staticmethod
  def create(realm) -> RenderHelper:
    if realm.config.RENDER:
      return WebsocketRenderHelper(realm)
    else:
      return DummyRenderHelper()

class DummyRenderHelper(RenderHelper):
  def render(self, mode='human') -> None:
    pass

  def register(self, overlay) -> None:
    pass

  def step(self, obs, pos, cmd):
    pass

class WebsocketRenderHelper(RenderHelper):
  def __init__(self, realm) -> None:
    self.overlay    = None
    self.overlayPos = [256, 256]
    self.client     = None
    self.registry   = OverlayRegistry(realm)

  ############################################################################
  ### Client data
  def render(self, mode='human') -> None:
    '''Data packet used by the renderer

    Returns:
        packet: A packet of data for the client
    '''

    assert self.has_reset, 'render before reset'
    packet = self.packet

    if not self.client:
        from nmmo.websocket import Application
        self.client = Application(self)

    pos, cmd = self.client.update(packet)
    self.registry.step(self.obs, pos, cmd)

  def register(self, overlay) -> None:
    '''Register an overlay to be sent to the client

    The intended use of this function is: User types overlay ->
    client sends cmd to server -> server computes overlay update ->
    register(overlay) -> overlay is sent to client -> overlay rendered

    Args:
        values: A map-sized (self.size) array of floating point values
    '''
    err = 'overlay must be a numpy array of dimension (*(env.size), 3)'
    assert type(overlay) == np.ndarray, err
    self.overlay = overlay.tolist()
