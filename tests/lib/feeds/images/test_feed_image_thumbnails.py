import tempfile
from os import path
from feedplatform import test as feedev
from feedplatform.lib import feed_image_thumbnails
from _image_test_utils import FeedWithImage, ValidPNGImage


tempdir = tempfile.mkdtemp()


def test_thumbnails():
    # handle_feed_images not specified, this tests the dependency
    ADDINS = [feed_image_thumbnails(
                ((100,100),),
                (tempdir, '%(model_id)s-thumb-%(size)s.gif'),
                format='gif')]

    class TestImage(feedev.File):
        content = ValidPNGImage
        url = 'http://bla/stuff.png'

    class TestFeed(feedev.Feed):
        content = FeedWithImage % TestImage.url

        def pass1(feed):
            # check that the image was stored
            imgfile = path.join(tempdir, '%s-thumb-%s.%s' % (feed.id, '100x100', 'gif'))
            assert path.exists(imgfile)

            # check that it was stored as a true gif file, as requested
            from PIL import Image
            i = Image.open(imgfile)
            assert i.format == 'GIF'
            # ... with the requested size
            assert i.size == (100,100)

    feedev.testcaller()


def test_unsupported_extensions():
    """Regression test for a bug that caused a ``KeyError`` to be raised
    when the extension of a target filename of a thumbnail did not refer
    to a valid image format, as supported by PIL.

    Instead, we want the thumbnail to be saved with whatever format the
    image originally has.

    The same bug also affected normal saving of a feed image (via the
    ``store_feed_images`` addin) under certain circumstances (when saved
    through PIL), and this is tested in ``test_remote_image.py``.
    """
    ADDINS = [feed_image_thumbnails(
                ((100,100),),
                (tempdir, '%(model_id)s-thumb'))]  # note: without extension

    class TestImage(feedev.File):
        content = ValidPNGImage
        url = 'http://bla/strange-extension.aspx'

    class TestFeed(feedev.Feed):
        content = FeedWithImage % TestImage.url

        def pass1(feed):
            # check that the image was stored
            imgfile = path.join(tempdir, '%s-thumb' % (feed.id))
            assert path.exists(imgfile)

            # check that it was stored as a png file, the source image format
            from PIL import Image
            i = Image.open(imgfile)
            assert i.format == 'PNG'

            # and most importantly, no exception is raised

    feedev.testcaller()