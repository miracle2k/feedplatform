from nose.tools import assert_raises
from feedplatform import test as feedev
from feedplatform.lib import update_redirects
from feedplatform import db
from feedplatform.db import models


class ExistingFeedA(feedev.Feed):
    url = u"http://new.org/feeds/rss"
    content = ""

class ExistingFeedB(feedev.Feed):
    url = u"http://new.org/feeds/rss"
    content = ""

class _BasePermanentlyRedirectedFeed(feedev.Feed):
    url = u"http://myolddomain.com/feed.xml"
    status = 301
    headers = {'Location': u"http://new.org/feeds/rss"}
    content = ""

class TemporarilyRedirectedFeed(_BasePermanentlyRedirectedFeed):
    url = u"http://anotherdomain.com/feed.xml"
    status = 302

    def pass1(feed):
        # URL has NOT changed
        assert feed.url == u"http://anotherdomain.com/feed.xml"


COMMON_FEEDS = [ExistingFeedA, ExistingFeedB, TemporarilyRedirectedFeed]


def test_force():
    class PermanentlyRedirectedFeed(_BasePermanentlyRedirectedFeed):
        def pass1(feed):
            # feed url has changed
            assert feed.url == u'http://new.org/feeds/rss'

    feedev.testcustom(COMMON_FEEDS + [PermanentlyRedirectedFeed],
                      addins=[update_redirects(force=True)])


def test_ignore():
    class PermanentlyRedirectedFeed(_BasePermanentlyRedirectedFeed):
        def pass1(feed):
            # feed url has *not* changed
            assert feed.url == u'http://myolddomain.com/feed.xml'

    feedev.testcustom(COMMON_FEEDS + [PermanentlyRedirectedFeed],
                      addins=[update_redirects(ignore=True)])


def test_delete_self():
    class PermanentlyRedirectedFeed(_BasePermanentlyRedirectedFeed):
        def pass1(feed):
            # current feed object does no longer exist
            assert db.store.find(models.Feed, models.Feed.id == feed.id).count() == 0

            # there were two other feeds with the same url that we are
            # redirecting to, they both still exist (we have only deleted
            # ourselfs).
            assert db.store.find(models.Feed, models.Feed.url == u'http://new.org/feeds/rss').count() == 2

    feedev.testcustom(COMMON_FEEDS + [PermanentlyRedirectedFeed],
                      addins=[update_redirects(delete="self")])


def test_delete_other():
    class PermanentlyRedirectedFeed(_BasePermanentlyRedirectedFeed):
        def pass1(feed):
            # url has changed
            assert feed.url == u'http://new.org/feeds/rss'
            # no other feed with that url exists
            assert db.store.find(models.Feed, models.Feed.url == u'http://new.org/feeds/rss').count() == 1

    feedev.testcustom(COMMON_FEEDS + [PermanentlyRedirectedFeed],
                      addins=[update_redirects(delete="other")])


def test_instantiation():
    # must pass at least one
    assert_raises(Exception, update_redirects)

    # only certain values for delete
    assert_raises(Exception, update_redirects, delete="invalid")

    # can't pass more than one
    assert_raises(Exception, update_redirects, force=True, ignore=True)