from storm.locals import Unicode
from tests import feedev
from feedplatform.lib import collect_enclosure_data


ADDINS = [
    collect_enclosure_data('length', 'type')
]


class ValidFeed(feedev.Feed):
    content = """
        <rss>
        <channel>
            <item>
                <guid>item-1</guid>
                <enclosure
                    length="{% =1 %}1000{% end %}{% =2 %}5000{% end %}"
                    type="{% =1 %}text/html{% end %}{% =2 %}audio/mpeg{% end %}"
                    href="http://example.org/files/item-1"
                />
            </item>
        </channel></rss>
    """

    def pass1(feed):
        # initial values are picked up
        enclosure = feed.items.one().enclosures.one()
        assert enclosure.type == 'text/html'
        assert enclosure.length == 1000

    def pass2(feed):
        # changed values are picked up
        enclosure = feed.items.one().enclosures.one()
        assert enclosure.type == 'audio/mpeg'
        assert enclosure.length == 5000


class BozoFeed(feedev.Feed):
    content = """
        <rss>
        <channel>
            <item>
                <guid>item1</guid>
                <enclosure href="http://h.com/p/f.mp3" length="10" />
            <!-- item closing tag missing -->
        </channel></rss>
    """

    def pass1(feed):
        # even though the feed is bozo, the colletor still
        # works. there is little danger that non-feed data will
        # end up with enclosures in the feedparser.
        assert feed.items.one().enclosures.one().length == 10

def test():
    feedev.testmod()