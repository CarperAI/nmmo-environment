from __future__ import annotations
from typing import Dict,  Iterable, Tuple, TYPE_CHECKING
from collections import OrderedDict, Set, Sequence

if TYPE_CHECKING:
  from nmmo.task.game_state import GameState, GroupView

class Group(Sequence, Set):
  ''' An immutable, ordered, unique group of agents involved in a task
  '''
  def __init__(self, 
               agents: Iterable[int], 
               name: str=None):

    assert len(agents) > 0, "Team must have at least one agent"
    self.name = name if name else f"Agent({','.join([str(e) for e in agents])})"
    # Remove duplicates
    self._agents = tuple(OrderedDict.fromkeys(sorted(agents)).keys())
    if not isinstance(self._agents,tuple):
      self._agents = (self._agents,)

    self._sd: GroupView = None
    self._gs: GameState = None
  
  def __eq__(self, o):
    return self._agents == o

  def __len__(self):
    return len(self._agents)

  def __hash__(self):
    return hash(self._agents)

  def __getitem__(self, key):
      if len(self) == 1 and key == 0:
        return self
      return Group((self._agents[key],), f"{self.name}.{key}")
  
  def __str__(self) -> str:
    return str(self._agents)
  
  def description(self) -> Dict:
    return {
      "type": "Group",
      "name": self.name,
      "agents": self._agents
    }
  
  def update(self, gs: GameState) -> None:
    self._gs = gs
    self._sd = gs.get_subject_view(self)

  def __getattr__(self, attr):
    return self._sd.__getattribute__(attr)
