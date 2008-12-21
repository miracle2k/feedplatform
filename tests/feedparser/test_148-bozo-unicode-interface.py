"""FeedParser has a bug due to which it occasionally returns some data
a bytestrings in certain cases, for example if the feed is bozo. We've
patched this in our custom version, and here we test the scenario.
"""

from feedplatform import test as feedev
from feedplatform.lib import store_enclosures, collect_enclosure_data
from feedplatform.deps import feedparser


def test_native():
    """Test the the problem with feedparser module directly."""
    # bozo: final closing ">" chars are missing

    f = feedparser.parse(
        '<rss><channel><item><enclosure href="http://h.com/p/f.mp3" length="10" /></item></channel></rss')
    assert type(f.entries[0].enclosures[0].href) == unicode

    f = feedparser.parse(
        '<rss><channel><itunes:image href="http://image.example.com/a.gif" /></channel></rss')
    assert type(f.feed.image.href) == unicode


def test_enclosure_addin():
    """Test the problem through and in the context of the enclosure
    handling addins (enclosures are one of the problem areas with respect
    to this bug.
    """

    ADDINS = [
        # both plugins separately exhibited the bug in the passed,
        # though note that ``collect_enclosure_data`` depends on
        # ``store_encloures`` and cannot be used without it
        store_enclosures(),
        collect_enclosure_data('length', 'type'),
    ]

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
            # If the patch were not applied, we'd expect a Storm
            # "unicode expected" exception to be raised during
            # addin execution, the assertion here is just for
            # completeness sake.
            href = feed.items.one().enclosures.one().href
            assert href == 'http://h.com/p/f.mp3'
            assert type(href) == unicode

    feedev.testcaller()