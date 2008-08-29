from feedplatform import test as feedev
from feedplatform import addins

class test_addin(addins.base):
    called = 0
    def on_get_item(self, feed, entry_dict, guid):
        self.__class__.called += 1
        if guid == 'neverfind':
            return False   # never return an item in this case

ADDINS = [test_addin()]

class TestFeed(feedev.Feed):
    content = """
    <rss><channel>
        <item><guid>i-1</guid></item>
        <item><guid isPermaLink="False">neverfind</guid></item>   <!-- special guid value -->
    </channel></rss>
    """

    def pass1(feed):
        # called once per item...
        assert ADDINS[0].called == 2

    def pass2(feed):
        # ...everytime the feed is parsed
        assert ADDINS[0].called == 4

    def pass3(feed):
        # since our addin makes sure that the second item is always
        # detected as new, at this point we will have four items in
        # the database.
        assert feed.items.count() == 4

def test():
    feedev.testmod()