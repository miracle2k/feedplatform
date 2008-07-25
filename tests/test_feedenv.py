"""Self-test the feed evolution framework.
"""

from tests import feedev

tests_run = 0

class Feed1(feedev.Feed):
    def pass1(feed):
        global tests_run
        tests_run += 1

    def pass5(feed):
        global tests_run
        tests_run += 1

class Feed2(feedev.Feed):
    def pass1(feed):
        global tests_run
        tests_run += 1

    def pass199(feed):
        global tests_run
        tests_run += 1

def test_all_handlers_are_called():
    try:
        feedev.testmod()
    finally:
        assert tests_run == 4

def test_fails_if_no_passes():
    global Feed1, Feed2
    del Feed1
    del Feed2

    try:
        feedev.testmod()
    except Exception, e:
        assert "has no passes" in str(e)
    else:
        raise AssertionError("testmod() did not fail on pass-less module")