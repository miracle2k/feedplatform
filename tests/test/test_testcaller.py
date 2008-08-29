from nose.tools import assert_raises
from feedplatform import test as feedev


called = 0

class GlobalFeed(feedev.Feed):
    content = "<rss />"

    def pass1(feed):
        global called
        called += 1


def test_basic():
    """
    Only the feeds in this local namespace are used, ``GlobalFeed``
    is ignored.
    """

    class LocalFeed1(GlobalFeed):
        pass

    class LocalFeed2(GlobalFeed):
        pass

    feedev.testcaller()
    assert called == 2


def test_no_passes():
    try:
        feedev.testcaller()
    except Exception, e:
        assert 'nothing to test' in str(e)
    else:
        raise AssertionError("testcaller() did not fail on pass-less namespace")