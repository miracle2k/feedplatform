from feedplatform import test as feedev
from feedplatform import addins
from feedplatform.lib import store_enclosures

class test_addin(addins.base):
    called = 0
    called_created = 0
    def on_process_enclosure(self, enclosure, enclosure_dict, created):
        self.__class__.called += 1
        if created:
            self.__class__.called_created += 1

ADDINS = [store_enclosures, test_addin]

class TestFeed(feedev.Feed):
    content = """
    <rss><channel>
         <item><guid>i-1</guid><enclosure href="http://h.com/p/enc1" /></item>
    </channel></rss>
    """

    def pass1(feed):
        # called for all enclosures
        assert ADDINS[1].called == 1
        # ...with a special value for one's that are created
        assert ADDINS[1].called_created == 1

    def pass2(feed):
        # "called for all enclosures" includes existing ones
        assert ADDINS[1].called == 2
        # but the created flag is not set this time
        assert ADDINS[1].called_created == 1

def test():
    feedev.testmod()