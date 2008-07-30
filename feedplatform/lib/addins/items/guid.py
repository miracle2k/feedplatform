"""Addins that provide various fallbacks should a feed not provide
``<guid>`` elements to identify it's items.

Generally, it is a good idea to use many of those, since a huge number
of feeds out in the wild are in fact lacking guids, and FeedPlatform
ultimately requires *some* way to identify an item - otherwise, it
*will* be skipped.

There is, however, no perfect solution to this problem, only (better
or worse) approximations. For example, here is the strategy used by
Nick Bradbury's FeedDemon, a popular Windows feedreader:


    1) Use <guid>
    2) If date specified: <title> + <pubDate> (or <title> + <dc:date>)
    3) If link specified: <title> + <link>
    4) Use <title>

You can replicate that behaviour like so:

    ADDINS += [
        guid_by_content(fields=('title', 'date')),
        guid_by_content(fields=('title', 'link')),
        guid_by_content(fields=('title')),
    ]

    # TODO: Not true! Nr. 1 will match even if date doesn't exist; maybe
    introduce a require=(fields...) parameter syntax?
"""

from feedplatform import addins
from hashlib import md5
import calendar


__all__ = (
    'guid_by_content',
    'guid_by_enclosure',
    'guid_by_link',
    'guid_by_date',
)


class guid_by_content(addins.base):
    """Generates a guid by hashing selected item data fields.

    By default, those fields are ``title`` and ``description``,
    although you may use the ``fields`` option to change that
    to your liking.

    Note that all the fields will be used to generate the
    hash - that is, if any of them changes, an item will be
    considered new.

    By default, the guids are prefixed with ``content:`` for
    identification. You may override this using the ``prefix``
    parameter, or disable it completely by passing ``False``.

    By default, if all requested content fields are missing,
    this addin passes (no guid is generated). You can change
    that behaviour by use of ``allow_empty``.

    The hash function used is md5.
    """

    def __init__(self, fields=('title', 'description'), allow_empty=False,
                 prefix='content:'):
        self.fields = fields
        self.allow_empty = allow_empty
        self.prefix = prefix

    def on_need_guid(self, feed, item_dict):
        # assemble content
        content = u""
        for field in self.fields:
            value = item_dict.get(field)
            if value:
                content += unicode(value)

        # return has hash
        if content or self.allow_empty:
            hash = md5(content.encode('ascii', 'ignore'))
            result = u'%s%s' % (self.prefix or '', hash.hexdigest())
            return result

        return None


class guid_by_enclosure(addins.base):
    """Generates a guid based the enclosure attached to an item.

    The enclosure URL will be used as the guid.

    For podcast feeds, the enclosure is usually a defining element
    of the item. If you are working in such a scenario, you probably
    want this addin high up in your list.

    Note that this only looks at the first enclosure (see the
    enclosure support addin for more information on the subject of
    multiple enclosures).

    Attention: This requires our patched version of feedparser -
    the original will always fallback to a enclosure url if a guid
    is missing, which is not controllable from our side.

    By default, the guids are prefixed with ``enclosure:`` for
    identification. You may override this using the ``prefix``
    parameter, or disable it completely by passing ``False``.
    """

    def __init__(self, prefix='enclosure:'):
        self.prefix = prefix

    def on_need_guid(self, feed, item_dict):
        enclosures = item_dict.get('enclosures')
        if enclosures and len(enclosures) > 0:
            enc_href = enclosures[0].get('href')
            if enc_href:
                return '%s%s' % (self.prefix or '', enc_href)

        return None


class guid_by_link(addins.base):
    """Generates a guid based on the <link> element of an item.

    The link url itself will be used as the guid. This differs from
    ``guid_by_content`` which could be used on the link-field with
    much the same effect, but would store a hash.

    This can go terribly wrong: There are a number of feeds out there
    which use a common base url for all items.

    By default, the guids are prefixed with ``link:`` for
    identification. You may override this using the ``prefix``
    parameter, or disable it completely by passing ``False``.
    """

    def __init__(self, prefix='link:'):
        self.prefix = prefix

    def on_need_guid(self, feed, item_dict):
        link = item_dict.get('link')
        if link:
            return '%s%s' % (self.prefix or '', link)

        return None


class guid_by_date(addins.base):
    """Generates a guid based on the date of an item.

    The date as a Unix timestamp will be used as the guid. A
    similar effect could be achieved using ``guid_by_content``,
    which would store a hash. However, what makes this one slightly
    better is that if the feed starts giving dates in a different
    timezone, it will still be able to identify items correctly.

    The above also implies that a valid date is required, that we
    are able to parse. No guids will be provided for items with
    invalid dates by this addin.

    By default, the guids are prefixed with ``date:`` for
    identification. You may override this using the ``prefix``
    parameter, or disable it completely by passing ``False``.
    """

    def __init__(self, prefix='date:'):
        self.prefix = prefix

    def on_need_guid(self, feed, item_dict):
        date_tuple = item_dict.get('date_parsed')
        if date_tuple:
            return u'%s%s' % (self.prefix or '',
                             int(calendar.timegm(date_tuple)))

        return None