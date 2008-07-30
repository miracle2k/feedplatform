from tests import feedev
from feedplatform.db import Item
from feedplatform.lib import guid_by_date

ADDINS = [guid_by_date(prefix='dt::')]

class TestFeed(feedev.Feed):
    content = """
        <rss><channel>
            <!-- date is missing -->
            <item>
                <title>The Blog, Post #1</title>
            </item>

            <!-- date is invalid -->
            <item>
                <title>The Blog, Post #2</title>
                <pubDate>Uhm, sometimes yesterday...</pubDate>
            </item>

            <item>
                <title>The Blog, Post #3</title>
                {% <3 %}
                <pubDate>Wed, 30 Jul 2008 12:03:11 GMT</pubDate>
                {% end %}
                {% =3 %}
                <!-- moved to a different timezone -->
                <pubDate>Wed, 30 Jul 2008 14:03:11 +0200</pubDate>
                {% end %}
                {% >3 %}
                <!-- switch to dc date -->
                <dc:date>2008-07-30T14:03:11+02:00</dc:date>
                {% end %}
            </item>
        </channel></rss>
    """

    def pass1(feed):
        # found one item, two ignored (due to missing and invalid date)
        assert feed.items.count() == 1

        # the guid generated by our addin has the requested prefix
        print feed.items.one().guid
        assert feed.items.one().guid.startswith('dt::')

    def pass2(feed):
        # nothing has changed, we still only have one item
        assert feed.items.count() == 1

    def pass3(feed):
        # the date string has changed, moved to a different timezone,
        # but the point in time it represents is the same - no change!
        assert feed.items.count() == 1

    def pass4(feed):
        # we now use a different attribute for specifying the date.
        # this is actually normalized by the feed parser lib we use,
        # so not strictly our business.
        assert feed.items.count() == 1

def test():
    feedev.testmod()