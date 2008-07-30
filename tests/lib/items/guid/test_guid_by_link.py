from tests import feedev
from feedplatform.db import Item
from feedplatform.lib import guid_by_link

ADDINS = [guid_by_link(prefix='lnk::')]

class TestFeed(feedev.Feed):
    content = """
        <rss><channel>
            <item>
                <title>Post #4</title>
                <link>http://example.org/posts/4</link>
            </item>

            <!-- empty link -->
            <item>
                <title>Post #3</title>
                <link></link>
            </item>

            <!-- no link -->
            <item>
                <title>Post #2</title>
            </item>
        </channel></rss>
    """

    def pass1(feed):
        # found one item (two ignored due to missing/empty link)
        assert feed.items.count() == 1

        # the guid generated by our addin has the requested prefix
        print feed.items.one().guid
        assert feed.items.one().guid.startswith('lnk::')

def test():
    feedev.testmod()