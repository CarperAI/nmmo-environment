class SequentialLoader:
  '''config.PLAYER_LOADER that spreads out agent populations'''
  def __init__(self, config, np_random):
    items = config.PLAYERS

    self.items = items
    self.idx   = -1

    # np_random is the env-level rng
    self.candidate_spawn_pos = spawn_concurrent(config, np_random)

  def __iter__(self):
    return self

  def __next__(self):
    self.idx = (self.idx + 1) % len(self.items)
    return self.items[self.idx]

  # pylint: disable=unused-argument
  def get_spawn_position(self, agent_id):
    # the basic SequentialLoader just provides a random spawn position
    return self.candidate_spawn_pos.pop()

def spawn_continuous(config, np_random):
  '''Generates spawn positions for new agents

  Randomly selects spawn positions around
  the borders of the square game map

  Returns:
      tuple(int, int):

  position:
      The position (row, col) to spawn the given agent
  '''
  #Spawn at edges
  mmax = config.MAP_CENTER + config.MAP_BORDER
  mmin = config.MAP_BORDER

  # np_random is the env-level RNG, a drop-in replacement of numpy.random
  var  = np_random.integers(mmin, mmax)
  fixed = np_random.choice([mmin, mmax])
  r, c = int(var), int(fixed)
  if np_random.random() > 0.5:
    r, c = c, r
  return (r, c)

def get_edge_tiles(config):
  '''Returns a list of all edge tiles'''
  # Accounts for void borders in coord calcs
  left = config.MAP_BORDER
  right = config.MAP_CENTER + config.MAP_BORDER
  lows = config.MAP_CENTER * [left]
  highs = config.MAP_CENTER * [right]
  inc = list(range(config.MAP_BORDER, config.MAP_CENTER+config.MAP_BORDER))

  # All edge tiles in order
  sides = []
  sides.append(list(zip(lows, inc)))
  sides.append(list(zip(inc, highs)))
  sides.append(list(zip(highs, inc[::-1])))
  sides.append(list(zip(inc[::-1], lows)))

  return sides

def spawn_concurrent(config, np_random):
  '''Generates spawn positions for new agents

  Evenly spaces agents around the borders
  of the square game map, assuming the edge tiles are all habitable

  Returns:
      list of tuple(int, int):

  position:
      The position (row, col) to spawn the given agent
  '''
  sides = []
  for side in get_edge_tiles(config):
    sides += side
  np_random.shuffle(sides)
  return sides[:config.PLAYER_N]
