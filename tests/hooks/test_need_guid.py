from tests import feedev
from feedplatform import addins
from feedplatform import db

class test_addin(addins.base):
    called = 0
    def on_need_guid(self, feed, item_dict):
        self.__class__.called += 1

ADDINS = [test_addin()]

class TestFeed(feedev.Feed):
    content = """
    <rss>
        <item></item>
        <item><guid isPermaLink="false">xyz</guid></item>
    </rss>
    """

    def pass1(feed):
        # hook called only once, second item has a guid of it's own
        assert ADDINS[0].called == 1
        assert feed.items.find(db.models.Item.guid == u'xyz').count() == 1

def test():
    feedev.testmod()