from feedplatform import test as feedev
from feedplatform.lib import feed_image_restrict_mediatypes
from _image_test_utils import image_hook_counter, FeedWithImage


def test_restrict_mediatype():
    """Test mime type validation.
    """
    counter = image_hook_counter()
    ADDINS = [feed_image_restrict_mediatypes(('image/png', 'image/gif')), counter]

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