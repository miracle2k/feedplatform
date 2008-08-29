"""Test the guid handling of the core parser.

Addins may add additional guid sources, and those will be tested
separately. Here, we simply deal with whether guids have the desired
effect at all: identifying items.
"""

from feedplatform import test as feedev

class FooFeed(feedev.Feed):
    content = """
        <rss><channel>
            <item>
                <title>Foo Nr. 1</title>
                <guid>foo-1</guid>
            </item>
            {% =2 %}
            <item>
                <title>Foo Nr. 2</title>
                <guid>foo-2</guid>
            </item>
            {% end %}
        </channel></rss>
    """

    def pass1(feed):
        # found the first item
        assert feed.items.count() == 1

    def pass2(feed):
        # found the second item
        assert feed.items.count() == 2

    def pass3(feed):
        # the second item disappeared again, but is still in the db
        assert feed.items.count() == 2

class MixFeed(feedev.Feed):
    """Uses some of the same guid's as FooFeed.
    """
    content = """
        <rss><channel>
            <item>
                <title>A Mix</title>
                <guid>bar-1</guid>
            </item>
            {% 3 %}
            <item>
                <title>Another Mix</title>
                <guid>foo-1</guid>    <!-- used in BarFeed! -->
            </item>
            {% end %}
        </channel></rss>
    """

    def pass3(feed):
        # The feed's second item has an guid already used in BarFeed
        # in a previous pass (and is thus already in the database).
        # However, since we only require guids to be feed-locally
        # unique, rather than actually globally, hte item is still
        # picked up.
        assert feed.items.count() == 2

def test():
    feedev.testmod()