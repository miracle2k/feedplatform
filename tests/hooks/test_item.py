from feedplatform import test as feedev
from feedplatform import addins

class test_addin(addins.base):
    item = 0
    need_item = 0
    get_guid = 0
    skip = False
    def on_item(self, feed, data_dict, item_dict):
        self.item += 1
        if self.skip:
            return True
    def on_get_guid(self, feed, item_dict):
        self.get_guid += 1
    def on_need_item(self, feed, entry_dict, guid):
        self.need_item += 1

ADDINS = [test_addin()]

class TestFeed(feedev.Feed):
    content = """
    <rss><channel>
        <item><guid>a-item-abc</guid></item>
        {% =3 %}<item><guid>b-item-def</guid></item>{% end %}
    </channel></rss>
    """

    def pass1(feed):
        # in a normal case, all callbacks are called normally
        assert ADDINS[0].item == 1
        assert ADDINS[0].need_item == 1
        assert ADDINS[0].get_guid == 1

        # but if on_item returns "True" to indicate skipping...
        ADDINS[0].skip = True

    def pass2(feed):
        # ...the follow-up hooks are in fact never triggered
        assert ADDINS[0].item == 2
        assert ADDINS[0].need_item == 1
        assert ADDINS[0].get_guid == 1

    def pass3(feed):
        # [bug] only the current item is skipped, not the whole
        # feed. we just added a new item, which means in this
        # pass we will get two "item" events - but nothing else,
        # since skipping is still enabled.
        assert ADDINS[0].item == 4
        assert ADDINS[0].need_item == 1
        assert ADDINS[0].get_guid == 1


def test():
    feedev.testmod()