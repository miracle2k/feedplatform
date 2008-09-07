from storm.locals import Unicode
from feedplatform import test as feedev
from feedplatform.lib import collect_feed_image_data


ADDINS = [
    # some unicode fields, both "special" generated fields
    collect_feed_image_data('href', 'title', 'extension', 'filename')
]


class ValidFeed(feedev.Feed):
    content = """
    <rss><channel>
        <title>test-feed</title>
        <image>
            {% =1 %}
            <url>http://example.org/blog/image.jpg</url>
            <title>Example.org Cover</title>
            <link>http://example.org/</link>
            {% end %}
            {% =2 %}
            <url>http://example.org/new-cover.png</url>
            {% end %}
        </image>
    </channel></rss>
    """

    def pass1(feed):
        # initial values are picked up
        assert feed.image_title == 'Example.org Cover'
        assert feed.image_href == 'http://example.org/blog/image.jpg'
        assert feed.image_extension == 'jpg'
        assert feed.image_filename == 'image.jpg'

    def pass2(feed):
        # changed values are picked up
        assert feed.image_title == None
        assert feed.image_href == 'http://example.org/new-cover.png'
        assert feed.image_extension == 'png'
        assert feed.image_filename == 'new-cover.png'


class BozoFeed(feedev.Feed):
    content = """
    <rss><channel>
        <title>test-feed</title>
        <image>
            <url>http://example.org/blog/image.jpg</url>
    </channel></rss>
    """

    def pass1(feed):
        # feed is bozo (image tag not closed), but addin is active
        # nevertheless.
        assert feed.image_href == 'http://example.org/blog/image.jpg'


def test():
    feedev.testmod()