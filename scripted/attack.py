from pdb import set_trace as T
import numpy as np

import nmmo
from nmmo.core.observation import Observation

from scripted import utils

def closestTarget(config, ob: Observation):
   shortestDist = np.inf
   closestAgent = None

   Entity = nmmo.Serialized.Entity
   agent  = ob.agent()

   sr = agent.attribute(Entity.R)
   sc = agent.attribute(Entity.C)
   start = (sr, sc)

   for target in ob.entities:
      exists = target.attribute(Entity.Self)
      if not exists:
         continue

      tr = target.attribute(Entity.R)
      tc = target.attribute(Entity.C)

      goal = (tr, tc)
      dist = utils.l1(start, goal)

      if dist < shortestDist and dist != 0:
          shortestDist = dist
          closestAgent = target

   if closestAgent is None:
      return None, None

   return closestAgent, shortestDist

def attacker(config, ob: Observation):
   Entity = nmmo.Serialized.Entity

   sr = ob.agent().attribute(Entity.R)
   sc = ob.agent().attribute(Entity.C)
 
   attackerID = ob.agent().attribute(Entity.AttackerID)

   if attackerID == 0:
       return None, None

   for target in ob.entities:
      identity = target.attribute(Entity.ID)
      if identity == attackerID:
         tr = target.attribute(Entity.R)
         tc = target.attribute(Entity.C)
         dist = utils.l1((sr, sc), (tr, tc))
         return target, dist
   return None, None

def target(config, actions, style, targetID):
   actions[nmmo.action.Attack] = {
         nmmo.action.Style: style,
         nmmo.action.Target: targetID}

