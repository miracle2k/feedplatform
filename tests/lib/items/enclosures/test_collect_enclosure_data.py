from storm.locals import Unicode
from feedplatform import test as feedev
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
                    {% =1 %}length="1000"{% end %}
                    {% =2 %}length="5000"{% end %}
                    {% =3 %}length=""{% end %}
                    {% =4 %}{% end %}
                    {% =5 %}length="-1"{% end %}

                    {% =1 %}type="text/html"{% end %}
                    {% =2 %}type="audio/mpeg"{% end %}
                    {% =3 %}type=""{% end %}
                    {% >4 %}{% end %}
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

    def pass3(feed):
        # the values may also be empty (in the case of length, where
        # a number is expected, that means invalid)
        enclosure = feed.items.one().enclosures.one()
        assert enclosure.type == ''
        assert enclosure.length == None

    def pass4(feed):
        # or, the attributes may be  missing completely
        enclosure = feed.items.one().enclosures.one()
        assert enclosure.type == None
        assert enclosure.length == None

    def pass5(feed):
        # in some rare cases feeds contain enclosures with a length
        # value of "-1". As a convienience, the addin considers all
        # negative length values invalid and ignores them
        enclosure = feed.items.one().enclosures.one()
        assert enclosure.length == None


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
        # even though the feed is bozo, the collector still
        # works. there is little danger that non-feed data will
        # end up with enclosures in the feedparser.
        assert feed.items.one().enclosures.one().length == 10

def test():
    feedev.testmod()