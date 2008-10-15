from feedplatform import test as feedev
from feedplatform import addins

class test_addin(addins.base):
    called = False
    def on_get_guid(self, feed, item_dict):
        self.__class__.called = True

ADDINS = [test_addin()]

class TestFeed(feedev.Feed):
    content = """
    <rss><item><guid>guid-exists</guid></item></rss>
    """

    def pass1(feed):
        # called even for items that have guids
        assert ADDINS[0].called == True

def test():
    feedev.testmod()