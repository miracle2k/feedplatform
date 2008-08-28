from tests import feedev
from feedplatform import addins
from feedplatform.lib import store_enclosures

class test_addin(addins.base):
    called = 0
    def on_found_enclosure(self, enclosure, enclosure_dict):
        self.__class__.called += 1

ADDINS = [store_enclosures, test_addin]

class TestFeed(feedev.Feed):
    content = """
    <rss><channel>
        <item><guid>i-1</guid><enclosure href="http://h.com/p/enc1" /></item>
    </channel></rss>
    """

    def pass1(feed):
        # not called for a new enclosure...
        assert ADDINS[1].called == 0

    def pass2(feed):
        # but is called for an existing one, of course
        assert ADDINS[1].called == 1

def test():
    feedev.testmod()