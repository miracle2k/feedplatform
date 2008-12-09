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

    To test this, we are replacing the "urlopen()" function used by the
    addin, and cause these exceptions to raised there. We need to do this
    since we cannot generate those exceptions by just specifying a
    specific URL:

        - Due to our test setup and the custom HTTP handler,
          ``InvalidURL`` is NOT raised during testing.

        - We don't really depend on an external ftp server to raise
          the IOError.

    Note that in order to be able to replace urlopen(), we require the
    addin to be written in a certain way (late-binding the function),
    so we need to make sure that a badly written addin will not bypass
    these tests.
    """

    import urllib2
    from feedplatform import util

    class simulate_exception(addins.base):
        def on_update_feed_image(self, feed, image_dict, image):
            def new_urlopen(self, *args, **kwargs):
                # Mark somewhere that our custom urlopen() function was
                # indeed called - we assert this later. This allows us
                # to check that this test indeed did it's job rather
                # than being accidentally bypassed.
                ADDINS[1].called = True

                # call the test function (we do multiple times)
                test_func()


            old_urlopen = util.urlopen
            util.urlopen = new_urlopen
            try:
                # Cause the request to be made and our fake urlopen()
                # function to be (hopefully) called.
                image.request
            finally:
                util.urlopen = old_urlopen

    ADDINS = [handle_feed_images(), simulate_exception()]

    class TestFeed(feedev.Feed):
        content = """
        <rss><channel>
            <image><url>http://placeholder-url</url></image>
        </channel></rss>
        """

        def pass1(feed):
            # Assert that our custom urlopen() function was indeed
            # called. If this fails, then our urlopen() function was
            # not injected, and these tests were bascially bypassed.
            # The addin would have to be rewritten to allow us to
            # replace the function, so that we can test this behavior.
            assert ADDINS[1].called == True

            # reset for next test
            ADDINS[1].called = False

    #### 1) Test httplib.InvalidURL exception #####

    def test_func():
        # we still don't do it directly, since we want to
        # test this situation, not just a specific exception
        # type (which e.g. may change in future python versions).
        urllib2.urlopen('http://host:invalidportnum/path')
    feedev.testcaller()


    #### 2) Test IOError exception #####

    def test_func():
        raise IOError('[Errno ftp error] 530 Login incorrect')
    feedev.testcaller()

    #### 3) Test that an unknown exception is not caught #####

    class MyException(Exception): pass
    def test_func():
        raise MyException()
    assert_raises(MyException, feedev.testcustom, [TestFeed], addins=ADDINS)
