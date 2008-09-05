import datetime
from feedplatform import test as feedev
from feedplatform.test.mock import MockDateTime
from feedplatform.lib import feed_image_restrict_frequency
from _image_test_utils import image_hook_counter, FeedWithImage


def test_update_every():
    """Test timed update restriction.
    """
    counter = image_hook_counter()
    ADDINS = [feed_image_restrict_frequency(delta=20), counter]

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