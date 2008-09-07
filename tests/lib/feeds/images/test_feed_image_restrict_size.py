from feedplatform import test as feedev
from feedplatform.lib import feed_image_restrict_size
from _image_test_utils import image_hook_counter, image_reader, FeedWithImage


def test_max_size_by_content_length():
    """Test validation against ``Content-Length`` header.
    """
    counter = image_hook_counter()
    ADDINS = [feed_image_restrict_size(max_size=10), counter]

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
            # also, processing failed (=no image)
            assert counter.failure == 1

        def pass2(feed):
            # it's been fixed, we meet the limit
            assert counter.success == 1

    feedev.testcaller()


def test_max_size():
    """Test live validation of file size, effective in case a
    Content-Length header is missing.
    """
    counter = image_hook_counter()
    ADDINS = [feed_image_restrict_size(max_size=10), image_reader, counter]

    class TestFeedImage(feedev.File):
        def content(p):
            if p == 1: return "b"*15
            else: return "b"*5

    class TestFeed(feedev.Feed):
        content = FeedWithImage % TestFeedImage.url

        def pass1(feed):
            # at this point, the image is to large and is ignored
            assert counter.success == 0
            # also, processing failed (=no image)
            assert counter.failure == 1

        def pass2(feed):
            # it's been fixed, we meet the limit
            assert counter.success == 1

    feedev.testcaller()