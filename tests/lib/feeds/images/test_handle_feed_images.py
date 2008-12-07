from feedplatform import test as feedev
from feedplatform import addins
from feedplatform.lib import handle_feed_images
from _image_test_utils import image_hook_counter


def test_basic():
    """Test that hooks are triggered correctly, depending on whether a
    feed image is given or not.

    This is in addition to the specific tests for each hook.
    """
    counter = image_hook_counter()
    ADDINS = [handle_feed_images(), counter]

    class TestFeed(feedev.Feed):
        content = """
        <rss><channel>
            <title>test-feed</title>
            {% =2 %}<image></image>{% end %}
            {% =3 %}<image><url></url></image>{% end %}
            {% =4 %}<image><url>http://host/image.gif</url></image>{% end %}
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

        def pass4(feed):
            # finally, everything is ok!
            assert counter.called == 1

    feedev.testcaller()


def test_bug_invalid_url():
    """Regression test for a specific bug that caused us to crash
    when a image url was invalid and a httplib.InvalidURL exception
    was raised (rather than a "normal" URLError).
    """
    import urllib2, httplib

    class cause_exception(addins.base):
        def on_update_feed_image(self, feed, image_dict, image):
            self.called = True
            # Accessing image.request would normally raise the
            # exception we're looking for, but not while running
            # the tests, where we have our own custom http handler
            # installed. Instead, we cause it manually to raise,
            # but we still don't do it directly, since we want to
            # test this situation, not just a specific exception
            # type (which e.g. may change in future python versions).
            urllib2.urlopen(image.url)
    ADDINS = [handle_feed_images(), cause_exception()]

    class TestFeed(feedev.Feed):
        content = """
        <rss><channel>
            <!-- uses an invalid url, a non-numeric port number -->
            <image><url>http://localhost:sdf/image.gif</url></image>
        </channel></rss>
        """

        def pass1(feed):
            assert ADDINS[1].called == True

    feedev.testcaller()
