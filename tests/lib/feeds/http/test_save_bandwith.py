from nose.tools import assert_raises
from storm.locals import Unicode, DateTime
from feedplatform import test as feedev
from feedplatform.lib import save_bandwith
from feedplatform import db, addins
from feedplatform.db import models
from feedplatform.util import struct_to_datetime, to_unicode


def test(*args, **kwargs):
    _run_test(etag=True, modified=True, *args, **kwargs)
    _run_test(etag=False, modified=True, *args, **kwargs)
    _run_test(etag=True, modified=False, *args, **kwargs)


def test_inheritance():
    """The addin provides functionality aiming to help subclassing.

    Run the same tests as in the standard run, but with our custom
    version of the addin.
    """

    # adds the columns to store etag and modified
    class provide_columns(addins.base):
        def get_columns(self):
            return {
                'feed': {
                    'my_etag': (Unicode, (), {}),
                    'my_modified': (DateTime, (), {}),
                }
            }

    # collect etag and modified info from the server
    class collector(addins.base):
        def on_after_parse(self, feed, data_dict):
            feed.my_etag = to_unicode(data_dict.get('etag'))
            feed.my_modified = struct_to_datetime(data_dict.get('modified'))

    # custom version of bandwith addin that builds on the work
    # of the previous two
    class my_save_bandwith_addin(save_bandwith):
        custom_storage = True

        def _get_etag(self, feed):
            return feed.my_etag
        def _get_modified(self, feed):
            return feed.my_modified

    test(custom_addin=my_save_bandwith_addin,
         additional_addins=[provide_columns, collector])


def _run_test(etag, modified, custom_addin=None, additional_addins=[]):
    """Run the ``save_bandwith`` test with the given options.

    ``etag`` and ``modified`` are passed on to it's constructor.

    The class in ``custom_addin``, if specified, will be used instead
    of the default ``save_bandwith`` addin.

    ``additional_addins`` will also be used, if given.
    """
    addin_klass = custom_addin or save_bandwith
    ADDINS = [addin_klass(etag=etag, modified=modified)] + additional_addins

    class TestFeed(feedev.Feed):
        def headers(p):
            # headers change in pass 3
            if p >= 3:
                return {
                    'Last-Modified': 'Sun, 08 Jan 2008 12:01:02 GMT',
                    'Etag': '"171856323"',
                }
            else:
                return {
                    'Last-Modified': 'Sun, 06 Jan 2008 21:02:30 GMT',
                    'Etag': '"179331154"',
                }

        # no item added in pass2
        content = """
        <rss><channel>
            <item><guid>item-1</guid></item>
            {% 2 %}<item><guid>item-2</guid></item>{% end %}
        </channel></rss>
        """

        def pass1(feed):
            # initial parse, we pick up the http headers
            assert feed.items.count() == 1

        def pass2(feed):
            # A new item was added, but since the headers have
            # not changed (a scenario that is exactly the opposite
            # of what reality should look like, but useful for
            # testing here), that item is not picked up by us yet.
            assert feed.items.count() == 1

        def pass3(feed):
            # At this point the headers DO have changed, causing us
            # to do a full reparse and as a result, we now have
            # found the second item.
            assert feed.items.count() == 2

    feedev.testcaller()