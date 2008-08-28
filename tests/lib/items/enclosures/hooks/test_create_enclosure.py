from tests import feedev
from feedplatform import addins
from feedplatform import db
from feedplatform.lib import store_enclosures

class test_addin(addins.base):
    called = 0
    def on_create_enclosure(self, item, enclosure_dict, href):
        self.__class__.called += 1
        # custom bake the enclosure instance
        enclosure = db.models.Enclosure()
        enclosure.item = item
        enclosure.href = href
        # XXX: test that this is instance will actually be used
        return enclosure

ADDINS = [store_enclosures, test_addin]

class TestFeed(feedev.Feed):
    content = """
    <rss><channel>
        <item><guid>i-1</guid><enclosure href="http://h.com/p/enc1" /></item>
    </channel></rss>
    """

    def pass1(feed):
        # called for a new enclosure...
        assert ADDINS[1].called == 1

    def pass2(feed):
        # but not an existing one
        assert ADDINS[1].called == 1

def test():
    feedev.testmod()