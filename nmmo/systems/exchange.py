from __future__ import annotations
from collections import deque

from typing import Dict, Union

from nmmo.systems.item import Item


class ItemListing:
  def __init__(self, item: Item, seller, price: int, tick: int):
    self.item = item
    self.seller = seller
    self.price = price
    self.tick = tick
class Exchange:
  def __init__(self, config):
    self._listings_queue: deque[(int, int)] = deque() # (item_id, tick)
    self._item_listings: Dict[int, ItemListing] = {}
    self._config = config

  def _list_item(self, item: Item, seller, price: int, tick: int):
    item.for_sale.update(1)
    item.listed_price.update(price)
    self._item_listings[item.id.val] = ItemListing(item, seller, price, tick)
    self._listings_queue.append((item.id.val, tick))

  def _unlist_item(self, item_id: int):
    item = self._item_listings.pop(item_id).item
    item.for_sale.update(0)
    item.listed_price.update(0)

  def step(self, current_tick: int):
    # Remove expired listings
    while self._listings_queue:
      (item_id, listing_tick) = self._listings_queue[0]
      if current_tick - listing_tick <= self._config.EXCHANGE_LISTING_DURATION:
        # Oldest listing has not expired
        break

      # Remove expired listing from queue
      self._listings_queue.popleft()

      # The actual listing might have been refreshed and is newer than the queue record.
      # Or it might have already been removed.
      listing = self._item_listings.get(item_id)      
      if listing is not None and current_tick - listing.tick > self._config.EXCHANGE_LISTING_DURATION:
        self._unlist_item(item_id)

  def sell(self, seller, item: Item, price: int, tick: int):
    assert isinstance(
        item, object), f'{item} for sale is not an Item instance'
    assert item in seller.inventory, f'{item} for sale is not in {seller} inventory'
    assert item.quantity.val > 0, f'{item} for sale has quantity {item.quantity.val}'

    self._list_item(item, seller, price, tick)

    # xcxc
    # if ((self.config.LOG_MILESTONES and realm.quill.milestone.log_max(f'Sell_{item.__name__}', level)) or
    #    (config.LOG_EVENTS and realm.quill.event.log(f'Sell_{item.__name__}', level))) and config.LOG_VERBOSE:
    #    logging.info(f'EXCHANGE: Offered level {level} {item.__name__} for {price} gold')

  def buy(self, buyer, item_id: int):
    listing = self._item_listings[item_id]
    item = listing.item
    assert item.quantity.val == 1, f'{item} purchase has quantity {item.quantity.val}'

    # TODO: Handle ammo stacks
    if not buyer.inventory.space:
        return

    if not buyer.gold.val >= item.listed_price.val:
        return

    self.unlist_item(item_id)
    listing.seller.inventory.remove(item)
    buyer.inventory.receive(item)
    buyer.gold.decrement(item.listed_price.val)
    listing.seller.gold.increment(item.listed_price.val)

    # xcxc
    # if ((config.LOG_MILESTONES and realm.quill.milestone.log_max(f'Buy_{item.__name__}', level)) or
    #       (config.LOG_EVENTS and realm.quill.event.log(f'Buy_{item.__name__}', level))) and config.LOG_VERBOSE:
    #    logging.info(f'EXCHANGE: Bought level {level} {item.__name__} for {price} gold')
    # if ((config.LOG_MILESTONES and realm.quill.milestone.log_max(f'Transaction_Amount', price)) or
    #       (config.LOG_EVENTS and realm.quill.event.log(f'Transaction_Amount', price))) and config.LOG_VERBOSE:
    #    logging.info(f'EXCHANGE: Transaction of {price} gold (level {level} {item.__name__})')

  # xcxc
  @property
  def packet(self):
      return {}
      # packet = {}
      # for (item_cls, level), listings in self.item_listings.items():
      #     key = f'{item_cls.__name__}_{level}'

      #     item = listings.placeholder
      #     if item is None:
      #         continue

      #     packet[key] = {
      #             'price': listings.price,
      #             'supply': listings.supply}
      # return packet
