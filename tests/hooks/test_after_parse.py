from tests import feedev
from feedplatform import addins

class test_addin(addins.base):
    called = 0
    def on_after_parse(self, feed, data_dict):
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
        # called once per feed...
        assert ADDINS[0].called == 1

    def pass2(feed):
        # ...everytime one is parsed
        assert ADDINS[0].called == 2

def test():
    feedev.testmod()