from feedplatform import test as feedev
from feedplatform.lib import handle_feed_images
from _image_test_utils import image_hook_counter


def test_basic():
    """Test that hooks are triggered correctly, depending on whether a
    feed image is given or not.

    This is in addition to the specific tests for each hook.
    """
    counter = image_hook_counter()
    ADDINS = [handle_feed_images(), counter]

    class TestFeed(feedev.Feed):
        content = """
        <rss><channel>
            <title>test-feed</title>
            {% =2 %}<image></image>{% end %}
            {% =3 %}<image><url></url></image>{% end %}
            {% =4 %}<image><url>http://host/image.gif</url></image>{% end %}
        </channel></rss>
        """

        def pass1(feed):
            # no tag at all
            assert counter.called == 0

        def pass2(feed):
            # no url tag
            assert counter.called == 0

        def pass3(feed):
            # empty url
            assert counter.called == 0

        def pass4(feed):
            # finally, everything is ok!
            assert counter.called == 1

    feedev.testcaller()