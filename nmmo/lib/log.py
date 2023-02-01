from collections import defaultdict

import logging


class Logger:
  def __init__(self):
    self.stats = defaultdict(list)

  def log(self, key, val):
    if not isinstance(val, (int, float)):
      raise RuntimeError(f'{val} must be int or float')

    self.stats[key].append(val)
    return True

class MilestoneLogger(Logger):
  def __init__(self, log_file):
    super().__init__()
    logging.basicConfig(format='%(levelname)s:%(message)s',
      level=logging.INFO, filename=log_file, filemode='w')

  def log_min(self, key, val):
    if key in self.stats and val >= self.stats[key][-1]:
      return False

    self.log(key, val)
    return True

  def log_max(self, key, val):
    if key in self.stats and val <= self.stats[key][-1]:
      return False

    self.log(key, val)
    return True
