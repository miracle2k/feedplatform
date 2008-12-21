from storm.locals import Unicode
from feedplatform import test as feedev
from feedplatform.lib import collect_enclosure_data


ADDINS = [
    # type is a normal string field, length and duration have
    # special handling behind them
    collect_enclosure_data('length', 'type', 'duration')
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
        # or, the attributes may be missing completely; for string
        # values, there is no difference between empty and missing.
        enclosure = feed.items.one().enclosures.one()
        assert enclosure.type == ''
        assert enclosure.length == None

    def pass5(feed):
        # in some rare cases feeds contain enclosures with a length
        # value of "-1". As a convienience, the addin considers all
        # negative length values invalid and ignores them
        enclosure = feed.items.one().enclosures.one()
        assert enclosure.length == None


def enc(feed): return feed.items.one().enclosures.one()
class DurationFeed(feedev.Feed):
    """Test various scenarios regarding reading the duration value.
    """

    content = """
        <rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
        <channel>
            <item>
                <guid>item-1</guid>
                <enclosure href="http://example.org/files/item-1"/>
                {% =1 %}<itunes:duration>33</itunes:duration>{% end %}
                {% =2 %}<itunes:duration>00:33</itunes:duration>{% end %}
                {% =3 %}<itunes:duration>01:51</itunes:duration>{% end %}
                {% =4 %}<itunes:duration>03:59:00</itunes:duration>{% end %}
                {% =5 %}<itunes:duration></itunes:duration>{% end %}
                {% =6 %}{% end %}
                {% =7 %}<itunes:duration>1:1</itunes:duration>{% end %}
                {% =8 %}<itunes:duration>01:01:33:12:99</itunes:duration>{% end %}
                {% =9 %}<itunes:duration>99</itunes:duration>{% end %}
                {% =10 %}<itunes:duration>sdf</itunes:duration>{% end %}
                {% =11 %}<itunes:duration>11:</itunes:duration>{% end %}
                {% =12 %}<itunes:duration>-12</itunes:duration>{% end %}

                {% =13 %}
                <enclosure href="http://example.org/files/item-2"/>
                <itunes:duration>1</itunes:duration>
                {% end %}
            </item>
        </channel></rss>
    """

    def pass1(f): assert enc(f).duration == 33      # simple second count
    def pass2(f): assert enc(f).duration == 33      # null-value prefixes don't make difference
    def pass3(f): assert enc(f).duration == 111     # MM:SS syntax
    def pass4(f): assert enc(f).duration == 14340   # HH:MM:SS syntax
    def pass5(f): assert enc(f).duration == None    # no value, empty tag
    def pass6(f): assert enc(f).duration == None    # tag missing completely
    def pass7(f): assert enc(f).duration == 61      # single-digits without a 0-prefix work
    def pass8(f): assert enc(f).duration == 3693    # per spec, additional numbers to the right are ignored
    def pass9(f): assert enc(f).duration == 99      # individual values may exceed their range
    def pass10(f): assert enc(f).duration == None   # invalid value 1
    def pass11(f): assert enc(f).duration == None   # invalid value 2
    def pass12(f): assert enc(f).duration == None   # negative values are considered invalid as well

    def pass13(feed):
        # if multiple enclosures are present, a duration value
        # applies to all of them.
        e1, e2 = list(feed.items.one().enclosures)
        assert e1.duration == e2.duration == 1


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