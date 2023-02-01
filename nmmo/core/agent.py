
from nmmo.lib import colors


class Agent:
  policy   = 'Neural'

  color    = colors.Neon.CYAN
  pop      = 0

  def __init__(self, config, idx):
    '''Base class for agents

    Args:
      config: A Config object
      idx: Unique AgentID int
    '''
    self.config = config
    self.iden   = idx
    self.pop    = Agent.pop

  def __call__(self, obs):
    '''Used by scripted agents to compute actions. Override in subclasses.

    Args:
        obs: Agent observation provided by the environment
    '''
