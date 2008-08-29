"""When a guid has isPermaLink="false", it is not forced into an
absolute URL.
"""

from feedplatform import test as feedev
from feedplatform import db

class TestFeed(feedev.Feed):
    url = u"http://base.com/feed"
    content = """
    <rss><channel>
        <item><guid isPermaLink="false">xyz</guid></item>
        <item><guid>xyz</guid></item>
    </channel></rss>
    """

    def pass1(feed):
        assert feed.items.find(db.models.Item.guid == u'xyz').count() == 1
        assert feed.items.find(db.models.Item.guid == u'http://base.com/xyz').count() == 1

def test():
    feedev.testmod()