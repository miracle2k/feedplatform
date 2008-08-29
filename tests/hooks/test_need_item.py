from feedplatform import test as feedev
from feedplatform import addins

class test_addin(addins.base):
    called = 0
    def on_need_item(self, feed, entry_dict, guid):
        self.__class__.called += 1
        if guid == 'neverfind':
            return feed.items.one()

ADDINS = [test_addin()]

class TestFeed(feedev.Feed):
    content = """
    <rss><channel>
        <item><guid>i-1</guid></item>
        <item><guid isPermaLink="False">neverfind</guid></item>   <!-- special guid value -->
    </channel></rss>
    """

    def pass1(feed):
        # called once per *new* item, everytime the feed is passed...
        assert ADDINS[0].called == 2

    def pass2(feed):
        # ...but since due to our addin the second item is never
        # added as such (but rather points the first), it is never
        # picked up and the hook triggers for it everytime...
        assert ADDINS[0].called == 3

    def pass3(feed):
        # ...for the same reason, we never find more than one (the first)
        # item.
        assert feed.items.count() == 1

def test():
    feedev.testmod()