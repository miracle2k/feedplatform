from storm.locals import Unicode
from tests import feedev
from feedplatform.lib import collect_item_data


ADDINS = [
    # one unicode one datetime field, one custom
    collect_item_data('title', 'updated', wfw_comment=(Unicode, (), {}))
]


class ValidFeed(feedev.Feed):
    content = """
        <rss xmlns:wfw="http://wellformedweb.org/CommentAPI/">
        <channel>
            <item>
                <title>
                    {% =1 %}org title{% end %}
                    {% =2 %}changed title{% end %}
                </title>
                <pubDate>
                    {% =1 %}Fri, 15 Aug 2008 23:01:39 +0200{% end %}
                    {% =2 %}Fri, 17 Aug 2008 23:01:39 +0200{% end %}
                </pubDate>
                <wfw:comment>
                    {% =1 %}http://old.org/c/52{% end %}
                    {% =2 %}http://new.org/c/52{% end %}
                </wfw:comment>
                <guid>item1</guid>
            </item>
        </channel></rss>
    """

    def pass1(feed):
        # initial values are picked up
        item = feed.items.one()
        assert item.title == 'org title'
        assert item.updated.day == 15
        assert item.wfw_comment == 'http://old.org/c/52'

    def pass2(feed):
        # changed values are picked up
        item = feed.items.one()
        assert item.title == 'changed title'
        assert item.updated.day == 17
        assert item.wfw_comment == 'http://new.org/c/52'


class BozoFeed(feedev.Feed):
    content = """
        <rss xmlns:wfw="http://wellformedweb.org/CommentAPI/">
        <channel>
            <item>
                <title>org title</title>
                <guid>item1</guid>
            <!-- item closing tag missing -->
        </channel></rss>
    """

    def pass1(feed):
        # even though the feed is bozo, the item colletor still
        # works. there is little danger that non-feed data will
        # end up with items in the feedparser.
        assert feed.items.one().title == 'org title'

def test():
    feedev.testmod()