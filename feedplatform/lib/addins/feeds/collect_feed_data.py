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
from feedplatform.util import struct_to_datetime


__all__ = (
    'collect_feed_data',
)


class _base_data_collector(addins.base):
    """Baseclass for both item and feed-level data collector addins.

    Subclasses should provide at least the ``model_name`` and
    ``standard_fields`` attributes, and may implement ``_get_value``
    for additional processing.

    ``standard_fields`` should be a dict in the form (name => field),
    with ``field`` being a database field instance or creation tuple,
    and name being both the model column name and the key name to use
    when reading the value from the feed parser source dict. If you
    want the model field name to differ from the source field, you may
    specifiy a dict for ``field``:

        'href': {'target': 'image_href', 'field': (Unicode, (), {})}
    """

    USE_DEFAULT = object()

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

        # fields may be specified as dicts or tuples: normalize
        for name, value in self.fields.iteritems():
            if not isinstance(value, dict):
                self.fields[name] = {'field': value, 'target': name}

    def get_columns(self):
        return {self.model_name: dict([(n, k['field'])
                    for n, k in self.fields.iteritems()])}

    def _process(self, obj, source_dict, *args, **kwargs):
        """Call this in your respective subclass hook callback.

        ``args`` and ``kwargs`` will be passed along to ``_get_value``.
        """
        for source_name, d in self.fields.iteritems():
            target_name = d['target']

            # First, let child classes handle the field, if they want.
            # Otherwise, fall back to default; Do not handle default
            # inside base _get_value, so that subclasses don't need to
            # bother with super().
            new_value = self._get_value(source_dict, source_name,
                                    target_name, *args, **kwargs)
            if new_value is self.USE_DEFAULT:
                # dates need to be converted to datetime
                if self.date_fields and source_name in self.date_fields:
                    source_name = "%s_parsed" % source_name
                    new_value = struct_to_datetime(source_dict.get(source_name))
                else:
                    new_value = source_dict.get(source_name)

            setattr(obj, target_name, new_value)

    def _get_value(self, source_dict, source_name, target_name, *args, **kwargs):
        """Overwrite this if some of your collector's fields need
        additional processing.

        Should return the final value, or ``self.USE_DEFAULT`` to let
        default processing continue.
        """
        return self.USE_DEFAULT


class collect_feed_data(_base_data_collector):
    """Collect feed-level meta data (as in: not item-specific), and
    store it in the database.

    When a feed upates it's data, so will your database.

    The syntax is:

        collect_feed_data(*known_fields, **custom_fields)

    Known fields currently include title, subtitle, summary, link,
    language, updated, modified.

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
        'link': (Unicode, (), {}),
        'language': (Unicode, (), {}),
        'updated': (DateTime, (), {}),
        'published': (DateTime, (), {}),
    }
    date_fields = ('published', 'updated',)

    def on_after_parse(self, feed, data_dict):
        if not data_dict.bozo:
            return self._process(feed, data_dict.feed)