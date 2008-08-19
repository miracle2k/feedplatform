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


class collect_feed_data(addins.base):
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

    def __init__(self, *args, **kwargs):
        self.fields = {}
        for name in args:
            try:
                f = {'title': (Unicode, (), {}),
                     'subtitle': (Unicode, (), {}),
                     'summary': (Unicode, (), {}),
                     'language': (Unicode, (), {}),
                     'updated': (DateTime, (), {}),
                     'published': (DateTime, (), {})}[name]
            except KeyError:
                raise ValueError('unknown standard field "%s"' % name)
            self.fields[name] = f

        # only do this now so that defaults from *args are
        # overwritten by kwargs; even though the situation
        # makes hardly sense, this is the best way to resolve
        # it, short of maybe raising an exception.
        self.fields.update(kwargs)

    def get_columns(self):
        return {'feed': self.fields}

    def on_after_parse(self, feed, data_dict):
        if not data_dict.bozo:
            feed_dict = data_dict.feed
            for field in self.fields:
                # dates need to be converted to datetime
                if field in ('published', 'updated'):
                    source_field = {
                        'published': 'published_parsed',
                        'updated': 'updated_parsed',
                    }.get(field)
                    new_value = struct_to_datetime(feed_dict.get(source_field))
                else:
                    new_value = feed_dict.get(field)

                setattr(feed, field, new_value)