from feedplatform import test as feedev
from feedplatform import addins

class test_addin(addins.base):
    called = 0
    def on_new_item(self, feed, item, entry_dict):
        self.__class__.called += 1

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