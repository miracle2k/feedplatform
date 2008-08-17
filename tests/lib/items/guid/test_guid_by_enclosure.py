from tests import feedev
from feedplatform.lib import guid_by_enclosure

ADDINS = [guid_by_enclosure(prefix='enc::')]

class TestFeed(feedev.Feed):
    content = """
        <rss><channel>
            <item>
                <title>The Podcast, Episode #4</title>
                <enclosure url="http://example.org/files/ep4.mp3" length="32066412" type="audio/mpeg" />
            </item>

            {% 2 %}
            <!-- multiple enclosures -->
            <item>
                <title>The Podcast, Episode #3</title>
                <enclosure url="http://example.org/files/ep3-part1.mp3" length="121341" type="audio/mpeg" />
                {% <=3 %}
                <enclosure url="http://example.org/files/ep3-part2.mp3" length="121341" type="audio/mpeg" />
                {% end %}
            </item>
            {% end %}

            {% 4 %}
            <!-- lacking an url -->
            <item>
                <title>The Podcast, Episode #2</title>
                <enclosure length="121341" type="audio/mpeg" />
            </item>
            {% end %}

            {% 5 %}
            <!-- no enclosure -->
            <item>
                <title>The Podcast, Episode #2</title>
            </item>
            {% end %}
        </channel></rss>
    """

    def pass1(feed):
        # found one item
        assert feed.items.count() == 1

        # the guid generated by our addin has the requested prefix
        print feed.items.one().guid
        assert feed.items.one().guid.startswith('enc::')

    def pass2(feed):
        # the second item has multiple enclosures, but only the first
        # one is used, as is evident...
        assert feed.items.count() == 2
    def pass3(feed):
        # ...by the following pass, were we remove the second one,
        # but should see no change.
        assert feed.items.count() == 2

    def pass4(feed):
        # item not picked up, as there is no url
        assert feed.items.count() == 2

    def pass5(feed):
        # item not picked up, as there is no enclosure
        assert feed.items.count() == 2

def test():
    feedev.testmod()