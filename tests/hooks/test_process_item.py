from feedplatform import test as feedev
from feedplatform import addins

class test_addin(addins.base):
    called = 0
    called_created = 0
    def on_process_item(self, item, entry_dict, created):
        self.__class__.called += 1
        if created:
            self.__class__.called_created += 1

ADDINS = [test_addin()]

class TestFeed(feedev.Feed):
    content = """
    <rss><channel>
        <item><guid>i-1</guid></item>
    </channel></rss>
    """

    def pass1(feed):
        # called for all items
        assert ADDINS[0].called == 1
        # ...with a special value for one's that are created
        assert ADDINS[0].called_created == 1

    def pass2(feed):
        # "called for all items" includes existing ones
        assert ADDINS[0].called == 2
        # but the created flag is not set this time
        assert ADDINS[0].called_created == 1

def test():
    feedev.testmod()