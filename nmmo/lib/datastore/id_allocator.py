class IdAllocator:
  def __init__(self, max_id):
    # Key 0 is reserved as padding
    self.max_id = 1
    self.free  = set()
    self.expand(max_id)

  def full(self):
    return len(self.free) == 0

  def remove(self, id):
    self.free.add(id)

  def allocate(self):
    return self.free.pop()

  def expand(self, max_id):
    self.free.update({idx for idx in range(self.max_id, max_id)})
    self.max_id = max_id
