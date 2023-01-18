class RenderHelper:
  def __init__(self) -> None:
    self.overlay    = None
    self.overlayPos = [256, 256]
    self.client     = None
    self.registry   = nmmo.OverlayRegistry(config, self)
     
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

  def dense(self):
    '''Simulates an agent on every tile and returns observations

    This method is used to compute per-tile visualizations across the
    entire map simultaneously. To do so, we spawn agents on each tile
    one at a time. We compute the observation for each agent, delete that
    agent, and go on to the next one. In this fashion, each agent receives
    an observation where it is the only agent alive. This allows us to
    isolate potential influences from observations of nearby agents

    This function is slow, and anything you do with it is probably slower.
    As a concrete example, consider that we would like to visualize a
    learned agent value function for the entire map. This would require
    computing a forward pass for one agent per tile. To cut down on
    computation costs, we omit lava tiles from this method

    Returns:
        (dict, dict):

        observations:
          A dictionary of agent observations as specified by step()

        ents:
          A corresponding dictionary of agents keyed by their entID
    '''
    config  = self.config
    R, C    = self.realm.map.tiles.shape

    entID   = 100000
    pop     = 0
    name    = "Value"
    color   = (255, 255, 255)


    observations, ents = {}, {}
    for r in range(R):
        for c in range(C):
          tile    = self.realm.map.tiles[r, c]
          if not tile.habitable:
              continue

          # xcxc
          current = tile.entity_id.val
          n       = len(current)
          if n == 0:
              ent = entity.Player(self.realm, (r, c), entID, pop, name, color)
          else:
              ent = list(current.values())[0]

          obs = self.realm.datastore.dataframe([ent])
          if n == 0:
              ent.datastore_object.delete()

          observations[entID] = obs
          ents[entID] = ent
          entID += 1

    return observations, ents
