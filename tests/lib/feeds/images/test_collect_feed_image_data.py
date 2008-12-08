from storm.locals import Unicode
from feedplatform import test as feedev
from feedplatform import addins
from feedplatform import db
from feedplatform.lib import collect_feed_image_data
from feedplatform.lib.addins.feeds.images import ImageError
from _image_test_utils import ValidPNGImage


def test_basic():
    ADDINS = [
        # some unicode fields, both "special" generated fields
        collect_feed_image_data('href', 'title', 'extension', 'filename')
    ]

    class TestFeed(feedev.Feed):
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

            # [bug] Ensure those fields we are checking are actually,
            # really, model fields, avaible in the database, not just
            # attributes, while the real fields are using their standard
            # name (i.e. "title" instead of "image_title").
            assert 'image_title' in [c._detect_attr_name(feed.__class__)
                                     for c in feed._storm_columns.keys()]

        def pass2(feed):
            # changed values are picked up
            assert feed.image_title == None
            assert feed.image_href == 'http://example.org/new-cover.png'
            assert feed.image_extension == 'png'
            assert feed.image_filename == 'new-cover.png'

    feedev.testcaller()


def test_failure_reset():
    """Image data is cleared if the image fails to process.
    """

    class FailDummy(addins.base):
        active = False
        def on_update_feed_image(self, *a, **kw):
            if self.active:
                raise ImageError()
    fail_dummy = FailDummy
    ADDINS = [collect_feed_image_data('href', ), fail_dummy]

    class TestFeed(feedev.Feed):
        content = """
        <rss><channel>
            <title>test-feed</title>
            <image>
                <url>http://example.org/blog/image.jpg</url>
                <title>Example.org Cover</title>
                <link>http://example.org/</link>
            </image>
        </channel></rss>
        """

        def pass1(feed):
            # initially, the value is picked up
            assert feed.image_href == 'http://example.org/blog/image.jpg'

            # ...but in the next pass, image handling will fail...
            fail_dummy.active = True

        def pass2(feed):
            # ...and the value is removed.
            assert feed.image_href == None

    feedev.testcaller()


def test_bozo():
    ADDINS = [collect_feed_image_data('href')]

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

    feedev.testcaller()


def test_unicode():
    """Regression test for a bug that caused storm to raise an
    "Expected unicode" TypeError in certain circumstances (the addin
    was trying to assign a str).
    """
    ADDINS = [collect_feed_image_data('href', 'extension')]

    class ImgWithExtByContent(feedev.File):
        url = 'http://images/validimage'
        content = ValidPNGImage

    class ImgWithExtByHeaders(feedev.File):
        url = 'http://images/validimage'
        headers = {'Content-Type': 'image/gif; charset=utf8'}

    class BozoFeed(feedev.Feed):
        content = """
        <rss><channel>
            <image>
                <!-- extension from url is unicode -->
                {% =1 %}<url>http://example.org/blog/image.jpg</url>{% end %}
                <!-- extension read from headers is unicode -->
                {% =2 %}<url>"""+ImgWithExtByHeaders.url+"""</url>{% end %}
                <!-- extension from pil content is unicode -->
                {% =3 %}<url>"""+ImgWithExtByContent.url+"""</url>{% end %}
            </image>
        </channel></rss>
        """

        # These assertions are here for completion's sake, but
        # normally shouldn't ever fail, since the bug we are
        # regression here really raises a TypeError.
        def pass1(feed):
            assert type(feed.image_href) == unicode
            assert type(feed.image_extension) == unicode

        def pass2(feed):
            assert type(feed.image_extension) == unicode

        def pass3(feed):
            assert type(feed.image_extension) == unicode


    feedev.testcaller()