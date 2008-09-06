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

            # check that it was stored as a true gif file...
            from PIL import Image
            i = Image.open(imgfile)
            assert i.format == 'GIF'
            # ... with the requested size
            assert i.size == (100,100)

    feedev.testcaller()