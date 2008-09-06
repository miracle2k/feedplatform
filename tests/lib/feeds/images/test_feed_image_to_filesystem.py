import tempfile
from os import path
from feedplatform import test as feedev
from feedplatform.lib import handle_feed_images, feed_image_to_filesystem
from _image_test_utils import FeedWithImage, ValidPNGImage


tempdir = tempfile.mkdtemp()


def test_original_format():
    # handle_feed_images not specified, this tests the dependency
    ADDINS = [feed_image_to_filesystem((tempdir, '%(model_id)s.%(extension)s'))]

    class TestImage(feedev.File):
        content = ValidPNGImage
        url = 'http://bla/stuff.png'

    class TestFeed(feedev.Feed):
        content = FeedWithImage % TestImage.url

        def pass1(feed):
            # check that the image was stored
            imgfile = path.join(tempdir, '%s.%s' % (feed.id, 'png'))
            assert path.exists(imgfile)

            # Make sure it was written correctly; this will usually not
            # be true if the image was saved using PIL, which is the
            # reason why we explicitely specify a url with an extension
            # to ``TestImage`` (otherwise, the image would be loaded into
            # PIL to defer the extension from the content), and PIL
            # subsequently used to save the file.
            assert open(imgfile, 'rb').read() == TestImage.content


    feedev.testcaller()


def test_force_format():
    ADDINS = [handle_feed_images,
              feed_image_to_filesystem((tempdir, '%(model_id)s.gif'), format='gif')]

    class TestImage(feedev.File):
        content = ValidPNGImage

    class TestFeed(feedev.Feed):
        content = FeedWithImage % TestImage.url

        def pass1(feed):
            # check that the image was stored
            imgfile = path.join(tempdir, '%s.%s' % (feed.id, 'gif'))
            assert path.exists(imgfile)

            # check that it was stored as a true gif file
            from PIL import Image
            assert Image.open(imgfile).format == 'GIF'


    feedev.testcaller()