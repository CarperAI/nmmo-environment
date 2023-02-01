import json
import lzma

class Replay:
  def __init__(self, config):
    self.packets = []
    self.map     = None

    if config is not None:
      self.path = config.SAVE_REPLAY + '.lzma'

    self._i = 0

  def update(self, packet):
    data = {}
    for key, val in packet.items():
      if key == 'environment':
        self.map = val
        continue
      if key == 'config':
        continue

      data[key] = val

    self.packets.append(data)

  def save(self):
    print(f'Saving replay to {self.path} ...')

    data = {
        'map': self.map,
        'packets': self.packets}

    data = json.dumps(data).encode('utf8')
    data = lzma.compress(data, format=lzma.FORMAT_ALONE)
    with open(self.path, 'wb') as out:
      out.write(data)

  @classmethod
  def load(cls, path):
    with open(path, 'rb') as fp:
      data = fp.read()

    data = lzma.decompress(data, format=lzma.FORMAT_ALONE)
    data = json.loads(data.decode('utf-8'))

    replay = Replay(None)
    replay.map = data['map']
    replay.packets = data['packets']
    return replay

  def render(self):
    from nmmo.websocket import Application
    client = Application(realm=None)
    for packet in self:
      client.update(packet)

  def __iter__(self):
    self._i = 0
    return self

  def __next__(self):
    if self._i >= len(self.packets):
      raise StopIteration
    packet = self.packets[self._i]
    packet['environment'] = self.map
    self._i += 1
    return packet
