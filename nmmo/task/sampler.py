import random

from nmmo.task.predicate import Predicate
from nmmo.task.predicate.core import AND, NOT, OR

class RandomTaskSampler:
  def __init__(self) -> None:
    self._task_specs = []
    self._task_spec_weights = []

  def add_task_spec(self, task_class, param_space = None, weight: float = 1):
    self._task_specs.append((task_class, param_space or []))
    self._task_spec_weights.append(weight)

  def sample(self,
             min_clauses: int = 1,
             max_clauses: int = 1,
             min_clause_size: int = 1,
             max_clause_size: int = 1,
             not_p: float = 0.0) -> Predicate:

    clauses = []
    for _ in range(0, random.randint(min_clauses, max_clauses)):
      task_specs = random.choices(
        self._task_specs,
        weights = self._task_spec_weights,
        k = random.randint(min_clause_size, max_clause_size)
      )
      pred_list = []
      for task_class, task_param_space in task_specs:
        predicate = task_class(*[random.choice(tp) for tp in task_param_space])
        if random.random() < not_p:
          predicate = NOT(predicate)
        pred_list.append(predicate)

      if len(pred_list) == 1:
        clauses.append(pred_list[0])
      else:
        clauses.append(AND(*pred_list))

    if len(clauses) == 1:
      return clauses[0]

    return OR(*clauses)

  # @staticmethod
  # def create_default_task_sampler(team_helper: task.TeamHelper, agent_id: int):
  #   neighbors = [team_helper.left_team(agent_id), team_helper.right_team(agent_id)]
  #   own_team = team_helper.own_team(agent_id)
  #   team_mates = [own_team.member(m) for m in range(team_helper.team_size)]
  #   sampler = TaskSampler()

  #   sampler.add_task_spec(InflictDamage, [neighbors + [own_team], [0, 1, 2], [0, 100, 1000]])
  #   sampler.add_task_spec(Defend, [team_mates, [512, 1024]])

  #   return sampler
