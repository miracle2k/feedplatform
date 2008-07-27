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
"""

from feedplatform import addins
from hashlib import md5


__all__ = (
    'guid_by_content',
    'guid_by_enclosure',
    'guid_by_link',
    'guid_by_date',
)


class guid_by_content(addins.base):

    def __init__(self, fields=('title', 'summary'), allow_empty=False,
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
        if content:
            hash = md5(content.encode('ascii', 'ignore'))
            result = u'%s%s' % (self.prefix, hash.hexdigest())
            return result

        return None


class guid_by_enclosure(addins.base):
    """
    for podcast feeds, the enclosure is usually a defining element

    Note that this only looks at the first enclosure (spec is unclear, many
    programs only support one, some more. generally we do support more, but
    not in this case).http://www.reallysimplesyndication.com/2004/12/21#a221
    """

    def __init__(self, prefix='enclosure:'):
        self.prefix = prefix

    def on_need_guid(self, feed, item_dict):
        enclosures = item_dict.get('enclosures')
        if enclosures and len(enclosures) > 0:
            enclosure = enclosures[0]
            if enclosure.href:
                return '%s%s' % (self.prefix, enclosure.href)


class guid_by_link(addins.base):
    pass

class guid_by_date(addins.base):
    pass