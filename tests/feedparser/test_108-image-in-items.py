"""Test the fix for issue #108 - the feedparser does not crash when an item
contains an image tag (KeyError).
"""

from feedplatform import test as feedev
from feedplatform import db


class TestFeed(feedev.Feed):
    content = """
    <rss><channel>
        <item>
            <guid>sdf</guid>
            <image>
               <url>http://www.npr.org/images/npr_news_123x20.gif</url>
               <title>Morning Edition</title>
               <link>http://www.npr.org/templates/rundowns/rundown.php?prgId=3</link>
           </image>
        </item>
    </channel></rss>
    """

    def pass1(feed):
        # no need to check anything - we didn't crash so we should be ok
        assert feed.items.count() == 1


def test():
    feedev.testmod()