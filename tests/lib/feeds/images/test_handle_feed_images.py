import datetime
from xml.sax import saxutils

from feedplatform import test as feedev
from feedplatform.lib import handle_feed_images
from feedplatform import addins
from feedplatform.test.mock import MockDateTime


class image_update_counter(addins.base):
    """Test helper addin that counts feed image events.
    """
    called = 0
    success = 0
    def on_update_feed_image(self, feed, image_dict, image):
        self.called += 1
    def on_feed_image_updated(self, feed, image_dict, image):
        self.success += 1


class image_reader(addins.base):
    """Cause exceptions that occur during image read() to occur.

    Since we don't want to involve any of the other, more functional
    addins at this point, this mock addin just accesses the image so that
    a potential ImageTooLarge exception may be raised.
    """
    def on_update_feed_image(self, feed, image_dict, image):
        image.read()


FeedWithImage = """
    <rss><channel>
        <title>test-feed</title>
        <image><url>%s</url></image>
    </channel></rss>
"""


def test_no_image():
    """If no feed image is give, the addin doesn't do anything, it's
    hooks are not triggered.
    """
    counter = image_update_counter()
    ADDINS = [handle_feed_images(max_size=10), counter]

    class TestFeed(feedev.Feed):
        content = """
        <rss><channel>
            <title>test-feed</title>
            {% =2 %}<image></image>{% end %}
            {% =3 %}<image><url></url></image>{% end %}
        </channel></rss>
        """

        def pass1(feed):
            # no tag at all
            assert counter.called == 0

        def pass2(feed):
            # no url tag
            assert counter.called == 0

        def pass3(feed):
            # empty url
            assert counter.called == 0

    feedev.testcaller()


def test_update_every():
    """Test timed update restriction.
    """
    counter = image_update_counter()
    ADDINS = [handle_feed_images(update_every=20), counter]

    class TestFeedImage(feedev.File):
        pass

    class TestFeed(feedev.Feed):
        content = FeedWithImage % TestFeedImage.url

        def pass1(feed):
            assert counter.success == 1

        def pass2(feed):
            # we're not yet updating the image again...
            assert counter.success == 1
            # ...but let's advance the clock for the next pass
            datetime.datetime.modify(seconds=30)

        def pass3(feed):
            assert counter.success == 2

    MockDateTime.install()
    try:
        feedev.testcaller()
    finally:
        MockDateTime.uninstall()


def test_restrict_extensions():
    """Test file extension validation.
    """
    counter = image_update_counter()
    ADDINS = [handle_feed_images(restrict_extensions=('png', 'gif')), counter]

    class JpegImage(feedev.File):
        url = 'http://images/image.jpeg'
    class NonImageFile(feedev.File):
        url = 'http://documents/stuff.xml'
    class PngImage(feedev.File):
        url = 'http://images/image.png'
    class ImageWithQueryString(feedev.File):
        url = 'http://images/image.png?q=x&r=3'
    class ImageWitoutExtension(feedev.File):
        url = 'http://images/image'
    class ImageWithExtensionInQuery(feedev.File):
        url = 'http://images/image?x=66&filename=.png'

    class TestFeed(feedev.Feed):
        def content(p):
            if p == 1:   image = JpegImage
            elif p == 2: image = NonImageFile
            elif p == 3: image = PngImage
            elif p == 4: image = ImageWithQueryString
            elif p == 5: image = ImageWitoutExtension
            elif p == 6: image = ImageWithExtensionInQuery
            return FeedWithImage % saxutils.escape(image.url)

        def pass1(feed):
            assert counter.success == 0
        def pass2(feed):
            assert counter.success == 0
        def pass3(feed):
            assert counter.success == 1
        def pass4(feed):
            assert counter.success == 2
        def pass5(feed):
            assert counter.success == 3
        def pass6(feed):
            assert counter.success == 4

    feedev.testcaller()

def test_restrict_mediatype():
    """Test mime type validation.
    """
    counter = image_update_counter()
    ADDINS = [handle_feed_images(restrict_mediatypes=('image/png', 'image/gif')), counter]

    class TestFeedImage(feedev.File):
        content = ""
        def headers(p):
            if p == 1:   return {'Content-Type': 'text/plain'}
            elif p == 2: return {'Content-Type': 'image/jpeg'}
            elif p == 3: return {'Content-Type': 'image/png; charset=ISO-8859-1'}  # charsets are correctly parsed out
            elif p == 4: return {'Content-Type': 'image/png'}

    class TestFeed(feedev.Feed):
        content = FeedWithImage % (TestFeedImage.url)

        def pass1(feed):
            assert counter.success == 0
        def pass2(feed):
            assert counter.success == 0
        def pass3(feed):
            assert counter.success == 1
        def pass4(feed):
            assert counter.success == 2

    feedev.testcaller()


def test_max_size_by_content_length():
    """Test validation against ``Content-Length`` header.
    """
    counter = image_update_counter()
    ADDINS = [handle_feed_images(max_size=10), counter]

    class TestFeedImage(feedev.File):
        content = ""
        def headers(p):
            if p == 1: return {'Content-Length': '15'}  # nose that those are strings, just like real headers # TODO: make the testframework ensure that header values are always strings
            else: return {'Content-Length': '5'}

    class TestFeed(feedev.Feed):
        content = FeedWithImage % (TestFeedImage.url)

        def pass1(feed):
            # at this point, the image is too large and is ignored
            assert counter.success == 0

        def pass2(feed):
            # it's been fixed, we meet the limit
            assert counter.success == 1

    feedev.testcaller()


def test_max_size():
    """Test live validation of file size, effective in case a
    Content-Length header is missing.
    """
    counter = image_update_counter()
    ADDINS = [handle_feed_images(max_size=10), image_reader, counter]

    class TestFeedImage(feedev.File):
        def content(p):
            if p == 1: return "b"*15
            else: return "b"*5

    class TestFeed(feedev.Feed):
        content = FeedWithImage % TestFeedImage.url

        def pass1(feed):
            # at this point, the image is to large and is ignored
            assert counter.success == 0

        def pass2(feed):
            # it's been fixed, we meet the limit
            assert counter.success == 1

    feedev.testcaller()