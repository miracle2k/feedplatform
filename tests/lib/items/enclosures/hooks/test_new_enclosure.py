from feedplatform import test as feedev
from feedplatform import addins
from feedplatform.lib import store_enclosures

class test_addin(addins.base):
    called = 0
    def on_new_enclosure(self, feed, enclosure, enclosure_dict):
        self.__class__.called += 1

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