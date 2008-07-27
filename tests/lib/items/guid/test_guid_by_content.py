"""Test the guid handling of the core parser.

Addins may add additional guid sources, and those will be tested
separately. Here, we simply deal with whether guids have the desired
effect at all: identifying items.
"""

from tests import feedev
from feedplatform.db import Item
from feedplatform.lib import guid_by_content

ADDINS = [guid_by_content(prefix='cnt::', fields=('title', 'link'))]

class TestFeed(feedev.Feed):
    content = """
        <rss><channel>
            <item>
                <title>Foo</title>
                {% 2 %}<description>The foo item.</description>{% end %}
            </item>

            <item>
                <title>Bar</title>
                {% <3 %}<link>http://example.org/posts/bar</link>{% end %}
                {% 3 %}<link>http://example.org/posts/bar-fixed</link>{% end %}
            </item>

            <item>
                {% <4 %}<title>Good item with an id</title>{% end %}
                {% 4 %}<title>Good item with a guid</title>{% end %}
                <guid>123456</guid>
            </item>
        </channel></rss>
    """

    def pass1(feed):
        # found three items
        assert feed.items.count() == 3

        # the guids generated by our addin should have the requested prefix
        assert any([item.guid.startswith('cnt::') for item in feed.items])

    def pass2(feed):
        # the change in "foo" was detected correctly
        assert feed.items.count() == 3

    def pass3(feed):
        # the change in "bar" was not, since <link> is in the guid.
        # thus, we pick up a duplicate.
        assert feed.items.count() == 4

    def pass4(feed):
        # the third item is using a guid; thus, the change is detected
        assert feed.items.count() == 4

        # we also want to make sure that the <guid> element is indeed
        # use, i.e. preferred over the content hash.
        assert feed.items.find(Item.guid == u'123456').count() == 1

def test():
    feedev.testmod()