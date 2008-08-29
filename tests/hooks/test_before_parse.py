from feedplatform import test as feedev
from feedplatform import addins

class test_addin(addins.base):
    called = 0
    # TODO: custom parser args not tested right now, but this is
    # difficult to do without getting to much into specifics of a
    # certain piece of functionality.
    def on_before_parse(self, feed, parser_args):
        self.__class__.called += 1
        return True  # skip

ADDINS = [test_addin()]

class TestFeed(feedev.Feed):
    content = """
    <rss>
        <item><guid>xyz</guid></item>
    </rss>
    """

    def pass1(feed):
        # called once per feed...
        assert ADDINS[0].called == 1

    def pass2(feed):
        # ...everytime one is parsed
        assert ADDINS[0].called == 2

    def pass3(feed):
        # although since we return True, we never
        # actually parse a feed, but skip everytime.
        assert feed.items.count() == 0

def test():
    feedev.testmod()