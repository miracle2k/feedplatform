from nose.tools import assert_raises
from feedplatform import test as feedev
from feedplatform.lib import update_redirects
from feedplatform import db
from feedplatform.db import models

ADDINS = []

class ExistingFeedA(feedev.Feed):
    url = u"http://new.org/feeds/rss"
    content = ""

class ExistingFeedB(feedev.Feed):
    url = u"http://new.org/feeds/rss"
    content = ""

class PermanentlyRedirectedFeed(feedev.Feed):
    url = u"http://myolddomain.com/feed.xml"
    status = 301
    headers = {'Location': u"http://new.org/feeds/rss"}
    content = ""

    def pass1(feed):
        # patched in dynamically by each test
        pass

class TemporarilyRedirectedFeed(PermanentlyRedirectedFeed):
    url = u"http://anotherdomain.com/feed.xml"
    status = 302

    def pass1(feed):
        # URL has NOT changed
        assert feed.url == u"http://anotherdomain.com/feed.xml"


def test_force():
    global ADDINS
    ADDINS = [update_redirects(force=True)]

    def check(feed):
        # feed url has changed
        assert feed.url == u'http://new.org/feeds/rss'
    PermanentlyRedirectedFeed.pass1 = staticmethod(check)

    feedev.testmod()

def test_ignore():
    global ADDINS
    ADDINS = [update_redirects(ignore=True)]

    def check(feed):
        # feed url has *not* changed
        assert feed.url == u'http://myolddomain.com/feed.xml'
    PermanentlyRedirectedFeed.pass1 = staticmethod(check)

    feedev.testmod()

def test_delete_self():
    global ADDINS
    ADDINS = [update_redirects(delete="self")]

    def check(feed):
        # current feed object does no longer exist
        assert db.store.find(models.Feed, models.Feed.id == feed.id).count() == 0

        # there were two other feeds with the same url that we are
        # redirecting to, they both still exist (we have only deleted
        # ourselfs).
        assert db.store.find(models.Feed, models.Feed.url == u'http://new.org/feeds/rss').count() == 2
    PermanentlyRedirectedFeed.pass1 = staticmethod(check)

    feedev.testmod()

def test_delete_other():
    global ADDINS
    ADDINS = [update_redirects(delete="other")]

    def check(feed):
        # url has changed
        assert feed.url == u'http://new.org/feeds/rss'
        # no other feed with that url exists
        assert db.store.find(models.Feed, models.Feed.url == u'http://new.org/feeds/rss').count() == 1
    PermanentlyRedirectedFeed.pass1 = staticmethod(check)

    feedev.testmod()

def test_instantiation():
    # must pass at least one
    assert_raises(Exception, update_redirects)

    # only certain values for delete
    assert_raises(Exception, update_redirects, delete="invalid")

    # can't pass more than one
    assert_raises(Exception, update_redirects, force=True, ignore=True)