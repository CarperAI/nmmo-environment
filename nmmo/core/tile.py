from pdb import set_trace as T
from types import SimpleNamespace
import numpy as np

import nmmo
from nmmo.lib.serialized import SerializedState
from nmmo.lib import material

TileState = SerializedState.subclass(
  "Tile", [
    "r",
    "c",
    "material_id",
  ])

TileState.Limits = lambda config: {
  "r": (0, config.MAP_SIZE-1),
  "c": (0, config.MAP_SIZE-1),
  "material_id": (0, config.MAP_N_TILE),
}

TileState.Query = SimpleNamespace(
  window=lambda ds, r, c, radius: ds.table("Tile").window(
    TileState._attr_name_to_col["r"],
    TileState._attr_name_to_col["c"],
    r, c, radius),
)

class Tile(TileState):
    def __init__(self, realm, r, c):
        super().__init__(realm.datastore, TileState.Limits(realm.config))
        self.realm = realm
        self.config = realm.config

        self.r.update(r)
        self.c.update(c)
        self.entities = {}

    @property
    def repr(self):
        return ((self.r.val, self.c.val))

    @property
    def pos(self):
        return self.r.val, self.c.val

    @property
    def habitable(self):
        return self.material in material.Habitable

    @property
    def impassible(self):
        return self.material in material.Impassible

    @property
    def lava(self):
        return self.material == material.Lava

    def reset(self, mat, config):
        self.state = mat(config)
        self.material = mat(config)
        self.material_id.update(self.state.index)

        self.depleted = False
        self.tex = self.material.tex

        self.entities = {}

    def addEnt(self, ent):
        assert ent.entID not in self.entities
        self.entities[ent.entID] = ent

    def delEnt(self, entID):
        assert entID in self.entities
        del self.entities[entID]

    def step(self):
        if not self.depleted or np.random.rand() > self.material.respawn:
            return

        self.depleted = False
        self.state = self.material
        self.material_id.update(self.state.index)

    def harvest(self, deplete):
        if __debug__:
            assert not self.depleted, f'{self.state} is depleted'
            assert self.state in material.Harvestable, f'{self.state} not harvestable'

        if deplete:
            self.depleted = True
            self.state = self.material.deplete(self.config)
            self.material_id.update(self.state.index)

        return self.material.harvest()
