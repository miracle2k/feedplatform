"""Stuff that is used by multiple test modules in this package.
"""

from feedplatform import addins

class image_hook_counter(addins.base):
    """Test helper addin that counts feed image events.
    """
    called = 0
    success = 0
    def on_update_feed_image(self, feed, image_dict, image):
        self.called += 1
    def on_feed_image_updated(self, feed, image_dict, image):
        self.success += 1


class image_reader(addins.base):
    """Cause possible exceptions during image read() to occur.

    Since we don't want to involve any of the other, more functional
    addins at this point, this mock addin just accesses the image so that
    a potential ImageTooLarge exception may be raised.
    """
    def on_update_feed_image(self, feed, image_dict, image):
        image.data.read()


FeedWithImage = """
    <rss><channel>
        <title>test-feed</title>
        <image><url>%s</url></image>
    </channel></rss>
"""

# "textfield.png" from FamFamFam Silk
ValidPNGImage = (
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10'
    '\x08\x04\x00\x00\x00\xb5\xfa7\xea\x00\x00\x00\x04gAMA\x00\x00\xaf'
    '\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq'
    '\xc9e<\x00\x00\x00+IDAT(\xcfc\xf8\xcf\x80\x1f2\xd0A\xc1\xc9\xff\xf8'
    '!P\xc1\x1f<\xf0\x05D\xc1\xc9A\xa0\x00\xaf#_\xfc\xc7\x0f\x19\x06A\\'
    '\x00\x00+\x8av*\xb3\xce\xe6\x93\x00\x00\x00\x00IEND\xaeB`\x82'
)