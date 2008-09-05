from xml.sax import saxutils
from feedplatform import test as feedev
from feedplatform.lib import feed_image_restrict_extensions
from _image_test_utils import image_hook_counter, \
    FeedWithImage, ValidPNGImage


def test_restrict_extensions():
    """Test file extension validation.
    """
    counter = image_hook_counter()
    ADDINS = [feed_image_restrict_extensions(('png', 'gif')), counter]

    class JpegImage(feedev.File):
        url = 'http://images/image.jpeg'
    class NonImageFile(feedev.File):
        url = 'http://documents/stuff.xml'
    class PngImage(feedev.File):
        url = 'http://images/image.png'
    class ImageWithQueryString(feedev.File):
        url = 'http://images/image.png?q=x&r=3'
    class ImageWitoutExtension(feedev.File):
        url = 'http://images/image'
    class ImageWithExtensionInQuery(feedev.File):
        url = 'http://images/image?x=66&filename=.png'
    class ImageWithoutExtensionButValidContent(feedev.File):
        url = 'http://images/validimage'
        content = ValidPNGImage

    class TestFeed(feedev.Feed):
        def content(p):
            if p == 1:   image = JpegImage
            elif p == 2: image = NonImageFile
            elif p == 3: image = PngImage
            elif p == 4: image = ImageWithQueryString
            elif p == 5: image = ImageWitoutExtension
            elif p == 6: image = ImageWithExtensionInQuery
            elif p == 7: image = ImageWithoutExtensionButValidContent
            return FeedWithImage % saxutils.escape(image.url)

        def pass1(feed):
            assert counter.success == 0
        def pass2(feed):
            assert counter.success == 0
        def pass3(feed):
            assert counter.success == 1
        def pass4(feed):
            assert counter.success == 2
        def pass5(feed):
            # Image has no extension in URL, and extension cannot be
            # determined via content type or content (since the former
            # is missing and the latter is invalid). In this case,
            # we fail, the image is not handled.
            assert counter.success == 2
        def pass6(feed):
            # As in pass5, no extension is available. The extension
            # from the querystring is currently ignored.
            assert counter.success == 2
        def pass7(feed):
            # the image is once again lacking an extension, but this
            # time the content is valid and the extension can be
            # deferred from it.
            assert counter.success == 3

    feedev.testcaller()