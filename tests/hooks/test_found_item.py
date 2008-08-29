from feedplatform import test as feedev
from feedplatform import addins

class test_addin(addins.base):
    called = 0
    def on_found_item(self, item, entry_dict):
        self.__class__.called += 1

ADDINS = [test_addin()]

class TestFeed(feedev.Feed):
    content = """
    <rss><channel>
        <item><guid>i-1</guid></item>
    </channel></rss>
    """

    def pass1(feed):
        # not called for a new item...
        assert ADDINS[0].called == 0

    def pass2(feed):
        # but is called for an existing one, of course
        assert ADDINS[0].called == 1

def test():
    feedev.testmod()