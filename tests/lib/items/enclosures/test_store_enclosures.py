# TODO: better test enclosure href uniqueness

from tests import feedev
from feedplatform.lib import store_enclosures
from feedplatform import db

ADDINS = [store_enclosures()]

class EnclosureFeed(feedev.Feed):
    content = """
        <rss><channel>
            <item>
                <enclosure href="http://example.org/files/1" />
                {% =2 %}<enclosure href="http://example.org/files/2" />{% end %}
                {% 4 %}<enclosure href="" />{% end %}
                {% 5 %}<enclosure />{% end %}
                <guid>item-1</guid>
            </item>
        </channel></rss>
    """

    def pass1(feed):
        # the enclosure was found
        assert feed.items.one().enclosures.count() == 1

    def pass2(feed):
        # a second enclosure was added
        assert feed.items.one().enclosures.count() == 2

    def pass3(feed):
        # the second enclosure was deleted again
        assert feed.items.one().enclosures.count() == 1

    def pass4(feed):
        # enclosures without a href value are ignored
        assert feed.items.one().enclosures.count() == 1

    def pass5(feed):
        # [bug] the attribute can also be missing completely
        assert feed.items.one().enclosures.count() == 1


class UniquenessTestFeed(feedev.Feed):
    content = """
        <rss><channel>
            <item>
                <guid>item-101</guid>
                <enclosure href="foobar" />
                <enclosure href="foobar" />
            </item>

            <item>
                <guid>item-102</guid>
                <enclosure href="foobar" />
                <enclosure href="foobar" />
            </item>
        </channel></rss>
    """

    def pass1(feed):
        """[bug] Make sure enclosure uniqueness is handled correctly:
        on a per-item level. Different items, or even different feeds,
        may have the same enclosure href.
        # TODO: support a solution to make it per-feed.
        """

        # we have two feeds, and each has exactly one enclosure
        assert feed.items.count() == 2
        for item in feed.items:
            assert item.enclosures.count() == 1

def test():
    feedev.testmod()