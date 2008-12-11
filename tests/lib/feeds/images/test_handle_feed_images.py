from nose.tools import assert_raises
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


def test_bug_urls_that_result_in_strange_exceptions():
    """Regression tests for two specific bugs that caused us to crash
    for certain unhandled exceptions raised during image downloading:

        - httplib.InvalidURL: raised e.g. for nun-numeric port numbers
        - IOError: e.g. "[Errno ftp error] 530 Login incorrect"

    To test this, we are raising the exceptions in an image's
    ``content()`` function. This is necessary because we cannot
    just generate them specifying a specific URL:

        - Due to our test setup and the custom HTTP handler,
          ``InvalidURL`` is NOT raised during testing.

        - We don't really depend on an external ftp server to raise
          the IOError.
    """

    class cause_request_open(addins.base):
        def on_update_feed_image(self, feed, image_dict, image):
            # cause the request and the image to be downloaded
            image.request

    ADDINS = [handle_feed_images(), cause_request_open()]

    def test_image(image):
        class TestFeed(feedev.Feed):
            content = """
            <rss><channel>
                <image><url>"""+image.url+"""</url></image>
            </channel></rss>
            """

            def pass1(feed):
                # no exception raised
                pass

        feedev.testcustom([TestFeed, image], addins=ADDINS)


    class InvalidUrlImage(feedev.File):
        def content(self):
            # We still don't do it directly, since we want to
            # test this situation, not just a specific exception
            # type (which e.g. may change in future python versions).
            import urllib2
            urllib2.urlopen('http://host:invalidportnum/path')
    test_image(InvalidUrlImage)


    class IOErrorImage(feedev.File):
        def content(self):
            raise IOError('[Errno ftp error] 530 Login incorrect')
    test_image(IOErrorImage)