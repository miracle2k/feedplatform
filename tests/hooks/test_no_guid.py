from tests import feedev
from feedplatform import addins

class test_addin(addins.base):
    called = 0
    def on_no_guid(self, feeds, item_dict):
        self.__class__.called += 1

ADDINS = [test_addin()]

class TestFeed(feedev.Feed):
    content = """
    <rss>
        <item></item>
        <item><guid>xyz</guid></item>
    </rss>
    """

    def pass1(feed):
        # called only once, the other item has a guid
        assert ADDINS[0].called == 1

def test():
    feedev.testmod()