from feedplatform import test as feedev
from feedplatform import addins
from feedplatform import db

class test_addin(addins.base):
    called = 0
    def on_create_item(self, feed, entry_dict, guid):
        self.__class__.called += 1
        # custom bake the item instance
        item = db.models.Item()
        item.feed = feed
        item.guid = guid
        # XXX: test that this is instance will actually be used
        return item

ADDINS = [test_addin()]

class TestFeed(feedev.Feed):
    content = """
    <rss><channel>
        <item><guid>i-1</guid></item>
    </channel></rss>
    """

    def pass1(feed):
        # called for a new item...
        assert ADDINS[0].called == 1

    def pass2(feed):
        # but not an existing one
        assert ADDINS[0].called == 1

def test():
    feedev.testmod()