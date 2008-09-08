"""Generally test the hooks introduced by image handling, and that they
keep to the contract they promise.
"""

from feedplatform import test as feedev
from feedplatform import addins
from feedplatform.lib import handle_feed_images
from feedplatform.lib.addins.feeds.images import ImageError
from _image_test_utils import FeedWithImage


class count_addin(addins.base):
    def __init__(self):
        self.called = {}
        self.fail = None
        self.returnvalue = {}

    def _process(self, name):
        self.called[name] = self.called.setdefault(name, 0) + 1
        if self.fail == name:
            raise ImageError()
        if name in self.returnvalue:
            return self.returnvalue[name]

    def __getattr__(self, name):
        # shortcut to self.called
        if hasattr(self, 'on_%s' % name):
            return self.called.setdefault(name, 0)
        raise AttributeError(name)

    def on_feed_image(self, feed, image_dict, image):
        return self._process('feed_image')
    def on_update_feed_image(self, feed, image_dict, image):
        return self._process('update_feed_image')
    def on_feed_image_updated(self, feed, image_dict, image):
        return self._process('feed_image_updated')
    def on_feed_image_failed(self, feed, image_dict, image, e):
        return self._process('feed_image_failed')
    def on_feed_image_download_chunk(self, image, bytes_read):
        return self._process('feed_image_download_chunk')


class BaseImageTestFeed(feedev.Feed):
    content = """
    <rss><channel>
        <image><url>http://example.org/image.png</url></image>
    </channel></rss>
    """


def test_basic():
    counter = count_addin()
    ADDINS = [handle_feed_images, counter]

    class HookTestFeed(BaseImageTestFeed):
        content = """
        <rss><channel>
            <image><url>http://example.org/image.png</url></image>
        </channel></rss>
        """

        def pass1(feed):
            # pass1: test everything ok, no errors
            assert counter.feed_image == 1               # always called
            assert counter.update_feed_image == 1        # called bc prev success
            assert counter.feed_image_updated == 1       # called bc prev success
            assert counter.feed_image_failed == 0        # not called on success

            # pass2: test failure in feed_image
            counter.fail = 'feed_image'

        def pass2(feed):
            assert counter.feed_image == 2               # always called
            assert counter.update_feed_image == 1        # unchanged bc error
            assert counter.feed_image_updated == 1       # unchanged bc error
            assert counter.feed_image_failed == 1        # called due to error

            # pass3: test failure in update_feed_image
            counter.fail = 'update_feed_image'

        def pass3(feed):
            assert counter.feed_image == 3               # always called
            assert counter.update_feed_image == 2        # called bc success
            assert counter.feed_image_updated == 1       # unchanged bc error
            assert counter.feed_image_failed == 2        # called due to error

            # pass4: test failure in feed_image_updated
            # (although it really shouldn't happen)
            counter.fail = 'feed_image_updated'

        def pass4(feed):
            assert counter.feed_image == 4               # always called
            assert counter.update_feed_image == 3        # called bc success
            assert counter.feed_image_updated == 2       # called bc success
            assert counter.feed_image_failed == 3        # called due to error

            # pass5: test feed_image non-error stop
            counter.returnvalue['feed_image'] = True

        def pass5(feed):
            assert counter.feed_image == 5               # always called
            assert counter.update_feed_image == 3        # unchanged bc skip
            assert counter.feed_image_updated == 2       # unchanged bc skip
            assert counter.feed_image_failed == 3        # not called on skip

    feedev.testcaller()


def test_skip_positive():
    """The ``feed_image`` hook can enforce handling in a positive
    manner, e.g. by instructing to continue with image processing right
    away while skipping other ``feed_image`` callbacks, which then won't
    have a chance to do their validation.
    """

    addin1 = count_addin()
    addin2 = count_addin()
    ADDINS = [handle_feed_images, addin1, addin2]

    class TestFeed(BaseImageTestFeed):
        def pass1(feed):
            # first pass, everything is normal
            assert addin1.feed_image == 1
            assert addin2.feed_image == 1
            assert addin1.feed_image_updated == 1
            assert addin2.feed_image_updated == 1

            # if we instruct addin1's ``feed_image`` hook to
            # force a succeed...
            addin1.returnvalue['feed_image'] = False

        def pass2(feed):
            # ...then this time addin2's ``feed_image`` hook will
            # never even be called.
            assert addin2.feed_image == 1
            assert addin1.feed_image == 2

            # although the other handlers in both addins are still triggered.
            assert addin1.feed_image_updated == 2
            assert addin2.feed_image_updated == 2

    feedev.testcaller()


def test_download_chunk():
    """Sepcial test for the ``feed_image_download_chunk`` hook, that
    is triggered while an image is downloaded.
    """

    class force_download_dummy(addins.base):
        def on_update_feed_image(self, feed, image_dict, image):
            image.chunk_size = 10    # read 10 bytes at one time
            image.data.read()

    counter = count_addin()
    ADDINS = [handle_feed_images, force_download_dummy, counter]

    class TestImage(feedev.File):
        content = "a" * 35           # 35 bytes total size

    class TestFeed(feedev.Feed):
        content = FeedWithImage % TestImage.url

        def pass1(feed):
            # 34 bytes ala 10 byte blocks = 4 reads
            assert counter.feed_image_download_chunk == 4

    feedev.testcaller()