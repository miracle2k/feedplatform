"""Addins that store feed metadata in the database for offline access.

# TODO: support custom rules for updating, e.g. update data never when
already existing, update always, only when a certain parser flag is
set (e.g. "fullparse"). This is useful for:
    * making sure data, once set or found, can't be changed by the
      feed author.
    * possibly reduce database writes, if feed authors who change
      their data a lot don't cause an update every time.

# TODO: option to disallow value deletion: values are only overwritten
if the new value is not empty.
"""

from storm.locals import Unicode, DateTime

from feedplatform import addins
from feedplatform import db
from feedplatform import log
from feedplatform.util import struct_to_datetime


__all__ = (
    'collect_feed_data',
)


class _base_data_collector(addins.base):
    """Baseclass for both item and feed-level data collector addins.
    """

    # provide in subclass
    model_name = None
    standard_fields = None
    date_fields = None

    def __init__(self, *args, **kwargs):
        self.fields = {}
        for name in args:
            try:
                f = self.standard_fields[name]
            except KeyError:
                raise ValueError('unknown standard field "%s"' % name)
            self.fields[name] = f

        # only do this now so that defaults from *args are
        # overwritten by kwargs; even though the situation
        # makes hardly sense, this is the best way to resolve
        # it, short of maybe raising an exception.
        self.fields.update(kwargs)

    def get_columns(self):
        return {self.model_name: self.fields}

    def _process(self, obj, source_dict):
        """Call this in your respective subclass hook callback.
        """
        for field in self.fields:
            # dates need to be converted to datetime
            if self.date_fields and field in self.date_fields:
                source_field = "%s_parsed" % field
                new_value = struct_to_datetime(source_dict.get(source_field))
            else:
                new_value = self._process_field(field, source_dict.get(field))

            setattr(obj, field, new_value)

    def _process_field(self, field, value):
        """Overwrite this if some of your collector's default fields
        need additional processing.

        Should return the final value.
        """
        return value


class collect_feed_data(_base_data_collector):
    """Collect feed-level meta data (as in: not item-specific), and
    store it in the database.

    When a feed upates it's data, so will your database.

    The syntax is:

        collect_feed_data(*known_fields, **custom_fields)

    Known fields currently include title, subtitle, summary, language,
    updated, modified.

    Using custom fields, you can read any field you want, but you
    need to specify a datatype for the database field.

    Examples:

        collect_feed_data('title', 'updated')

        from storm.locals import Unicode
        collect_feed_data('title', prism_issn=(Unicode, (), {}))

    If you're using custom fields, familiarize yourself with the
    Feedparser normalization rules:
        http://www.feedparser.org/docs/content-normalization.html
    """

    model_name = 'feed'
    standard_fields = {
        'title': (Unicode, (), {}),
        'subtitle': (Unicode, (), {}),
        'summary': (Unicode, (), {}),
        'language': (Unicode, (), {}),
        'updated': (DateTime, (), {}),
        'published': (DateTime, (), {}),
    }
    date_fields = ('published', 'updated',)

    def on_after_parse(self, feed, data_dict):
        if not data_dict.bozo:
            return self._process(feed, data_dict.feed)