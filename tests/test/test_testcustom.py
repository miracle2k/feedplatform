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
    Only the explicitly specified feeds are used.
    """

    class LocalFeed1(GlobalFeed):
        pass

    class LocalFeed2(GlobalFeed):
        pass

    feedev.testcustom([LocalFeed1])
    assert called == 1


def test_no_passes():
    try:
        feedev.testcustom([])
    except Exception, e:
        assert 'nothing to test' in str(e)
    else:
        raise AssertionError("testcustom() did not fail on pass-less call")