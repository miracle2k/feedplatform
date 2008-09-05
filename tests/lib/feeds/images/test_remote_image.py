"""Test the image wrapper class used internally.
"""

import os, tempfile
from StringIO import StringIO

from nose.tools import assert_raises

from feedplatform import test as feedev
from feedplatform.lib.addins.feeds.images import RemoteImage, handle_feed_images
from _image_test_utils import ValidPNGImage


def _test_image(image):
    """We'd like to use our fake HTTP handler to test images, but it
    is only enabled by the test framework while the tests are running.
    There is currently no real good way to have the handler active and
    serving some files files without going through the motions of
    using feeds with pass-level test functions.

    To make things in this particular test module easier, this utility
    function creates a dummy feed with one pass to give to the test
    framework, and then calls a ``test`` function on the ``image`` object
    you passed in, with a ``RemoteImage`` instance hooked up to the
    url of ``image`` passed in, for convenience.
    """

    class FakeFeed(feedev.Feed):
        def pass1(feed):
            image.test(RemoteImage(image.url))

    # TODO: do not require handle_feed_images to test RemoteImage
    feedev.testcustom([image, FakeFeed], addins=[handle_feed_images])


def test_content_type():
    class FeedImage(feedev.File):
        headers = None
        def test(image):
            assert image.content_type == 'foo/bar'

    # test with standard content type
    FeedImage.headers = {'Content-Type': 'foo/bar'}
    _test_image(FeedImage)

    # adding a charset makes no difference
    FeedImage.headers = {'Content-Type': 'foo/bar; charset=utf8'}
    _test_image(FeedImage)


def test_content_length():
    class FeedImage(feedev.File):
        headers = {'Content-Length': '9999'}
        def test(image):
            assert image.content_length == 9999

    _test_image(FeedImage)


def test_filename():
    class Normal(feedev.File):
        url = 'http://images/imgs/cover.png'
        def test(image):
            assert image.filename == 'cover.png'
            assert image.filename_with_ext == 'cover.png'
    _test_image(Normal)

    class NoName(feedev.File):
        url = 'http://images/'
        content = ValidPNGImage
        def test(image):
            # TODO: should those really return None?
            assert image.filename == ''
            assert image.filename_with_ext == '.png'
    _test_image(NoName)


def test_extension():
    class ByUrl(feedev.File):
        url = 'http://images/imgs/cover.png'
        def test(image):
            assert image.extension_by_contenttype == None
            assert image.extension_by_url == 'png'
            assert image.extension == 'png'
    _test_image(ByUrl)

    class ByContentType(feedev.File):
        url = 'http://images/imgs/'
        headers = {'Content-Type': 'image/png; charset=utf8'}
        def test(image):
            assert image.extension_by_url == None
            assert image.extension_by_contenttype == 'png'
            assert image.extension == 'png'
    _test_image(ByContentType)

    class ByPIL(feedev.File):
        url = 'http://images/imgs/'
        content = ValidPNGImage
        def test(image):
            assert image.extension_by_url == None
            assert image.extension_by_contenttype == None
            assert image.extension_by_pil == 'png'
            assert image.extension == 'png'
    _test_image(ByPIL)


def test_data():
    """Test the ``data`` file-object.
    """
    class FeedImage(feedev.File):
        content = 'a'*10

        def test(image):
            # the data gives us the full content
            image.chunk_size = 1
            assert image.data.read() == FeedImage.content

    _test_image(FeedImage)


def test_chunks():
    """Test the chunks() iterator.
    """
    class FeedImage(feedev.File):
        content = 'a'*10

        def test(image):
            # with a chunk size of 3 we'll have 4 chunks in total,
            # while we're initially downloading the image.
            image.chunk_size = 3
            assert len(list(image.chunks())) == 4

            # however, once the data is in memory, it's returned as
            # a single chunk.
            assert len(list(image.chunks())) == 1

            # the content happens to match too
            assert "".join(image.chunks()) == FeedImage.content

    _test_image(FeedImage)


def test_pil():
    class FeedImage(feedev.File):
        content = ValidPNGImage
        def test(image):
            assert image.pil_loaded == False
            assert image.pil.format == 'PNG'
            assert image.pil_loaded == True
    _test_image(FeedImage)


def test_save():
    # test a normal file
    class FeedImage(feedev.File):
        content = 'a'*10
        def test(image):
            name = tempfile.mktemp()
            image.save(name)
            assert os.path.exists(name)
            assert open(name).read() == FeedImage.content
    _test_image(FeedImage)

    # test a file saved through pil
    class FeedImage(feedev.File):
        content = ValidPNGImage
        def test(image):
            name = tempfile.mktemp() + '.png'
            image.pil   # make sure pil will be used
            assert image.pil_loaded
            image.save(name)
            assert os.path.exists(name)
            # the content usually won't match in this case, though
    _test_image(FeedImage)

    # test a file saved through pil with format request
    class FeedImage(feedev.File):
        content = ValidPNGImage
        def test(image):
            name = tempfile.mktemp()
            image.save(name, 'gif')
            assert os.path.exists(name)
            from PIL import Image
            assert Image.open(name).format == 'GIF'
    _test_image(FeedImage)
