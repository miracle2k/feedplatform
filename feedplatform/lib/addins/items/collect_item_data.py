"""Addins that store item metadata in the database for offline access.
"""

from storm.locals import Unicode, DateTime

from feedplatform import addins
from feedplatform import db
from feedplatform.util import struct_to_datetime
from feedplatform.lib.addins.feeds.collect_feed_data \
    import _base_data_collector


__all__ = (
    'collect_item_data',
)


class collect_item_data(_base_data_collector):
    """Collect item-level meta data, and store it in the database.

    This works precisely like ``collect_feed_data``, except that
    the supported known fields are:

    title, summary, updated, link
    """

    model_name = 'item'
    standard_fields = {
        'title': (Unicode, (), {}),
        'summary': (Unicode, (), {}),
        'link': (Unicode, (), {}),
        'updated': (DateTime, (), {})
    }
    date_fields = ('updated',)

    def on_found_item(self, item, entry_dict):
        return self._process(item, entry_dict)

    def on_new_item(self, item, entry_dict):
        return self._process(item, entry_dict)