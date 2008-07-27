"""Feed evolution test framework.

Due to the complexities involved when testing aggregator functionality,
we try to streamline the process by strongly linking the "feed
evolutions" involved with a test to the testcase implementation itself.

"Feed evolution", because a feed is not necessarily static, but often
needs to change throughout a test. Imagine for example a new entry is
added, and we have to make sure that it is picked up right.

Such a test case will thus involve multiple "passes", i.e. the feed is
parsed multiple times, and every time the test code needs to make sure
that the necessary conditions are met.

Example of a nose test module using this infrastructure (not using
real feed contents for simplicity):

    from tests import feedev

    class GuidTest(feedev.Feed):
        content = \"""
            <item guid="abcdefg" />
            {% 2 %}
            <item guid="ehijklm" />
            {% end %}
        \"""

        def pass1(feed):
            assert feed.items.count() == 1

        def pass2(feed):
            assert feed.items.count() == 2

    def test():
        feedev.testmod()
"""

import os, sys
import re
import types
import operator
import inspect
import urllib, urllib2
import httplib

# cStringIO is not subclassable and doesn't allow attribute assignment
import StringIO

from feedplatform.conf import config
from feedplatform import parse
from feedplatform import db
from feedplatform import log


__all__ = ('feedev',)


class FeedEvolutionTestFramework(object):

    def __init__(self):
        # if the user hasn't specified anything, we'll use a
        # memory-based sqlite database.
        if not (config.configured and config.DATABASE):
            config.configure(**{'DATABASE': 'sqlite:'})
            db.reconfigure()

        # Remember the original handlers, so that we can *add* our
        # fake handler on each, instead of overwriting handlers
        # that are defined in the configration file - i.e. it is
        # possible to run the test with additional custom handlers.
        self.urllib2_handlers = config.URLLIB2_HANDLERS

    def testmod(self, module=None):
        """Test the caller's module.

        Runs the "feed evolution" test defined by the module, e.g. will
        cause the defined feeds to be added to the database, parsed
        through multiple passes as requested, and the test callbacks
        being called.

        Differs from doctest's ``testmod``` in that it actually tests
        the **caller** if not explicit module reference was passed,
        whereas doctest would just use ``__main__``.
        """

        # For some strange reason currently beyond my comprehension,
        # but possible due to nose magic, by the time a test function
        # in one of the testcase files calls ``testmod()`` (us),
        # ``globals()`` now contains entries for all subdirectories of
        # the ``tests`` directory (i.e. the modules of the "tests"
        # package) that we have nose test.
        # Because there is a subdirectory "config" which contains tests
        # that are supposed to test FeedPlatform's configuration
        # facilites within ``feedplatform.conf``, the ``config`` we have
        # imported in this module from there is overwritten: It now points
        # to the module containing the tests, rather than to the
        # configuration object.
        # Thus, from this point on, the code in this module would use
        # to the wrong object when referring to ``config``.
        #
        # Note that while the test function is executed (our caller, one
        # level up the call stack), this stuff is not yet in globals().
        #
        # For now, our solution is to import the config again to put the
        # right object once again inside the global scope.
        #
        # In the future, there might be problems with other identifers
        # as well, as we are adding more tests.
        global config
        from feedplatform.conf import config

        # By this time the nose testrunner as redirected stdout. Reset
        # the log (it might still point to the real stdout) to make sure
        # that any messages will indeed be captured by nose.
        log.reset()

        # If no explicit module was passed, try to find the caller's
        # module by inspecting the stack.
        # Use tbe try-finally pattern explained in the docs:
        # http://docs.python.org/lib/inspect-stack.html
        if not module:
            frame = inspect.stack()[1][0]
            try:
                module = sys.modules[frame.f_globals['__name__']]
            finally:
                del frame

        # find all the test feeds defined in the module
        feeds = {}
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type):
               if issubclass(obj, FeedEvolutionTestFramework.Feed):
                   feeds[obj.name()] = obj

        # run the test case
        test = FeedEvolutionTest(feeds, module)
        config.URLLIB2_HANDLERS = list(self.urllib2_handlers) +\
                                  [MockHTTPHandler(test),]
        test.run()

    class Feed(object):
        """Baseclass for a single feed of an evolution.

        Uses a metaclass to convert all functions to static methods,
        which makes testing easier since we don't have to deal with
        instances, or ``self`` arguments. Classes are merely used
        here to structure the testing code in a manner that easily
        allows multiple feeds per testcase.

        We make this an inner class because it is exposed to the test
        writer, which allows them to reference this namespace-like
        using:

            from tests import feedev   (feedev is the outer object)
            class MyFeed(feedev.Feed):
                pass
        """

        class __metaclass__(type):
            def __new__(cls, name, bases, attrs):
                new_attrs = {}
                for key, value in attrs.items():
                    if isinstance(value, types.FunctionType):
                        new_attrs[key] = staticmethod(value)
                    else:
                        new_attrs[key] = value
                return type.__new__(cls, name, bases, new_attrs)

        @classmethod
        def name(cls):
            return cls.__name__

class FeedEvolutionTest(object):
    """Represents a single test case with one or many evolving feeds,
    i.e. a single run through multiple parsing passes.
    """

    def __init__(self, feeds, module):
        self.feeds = feeds
        self.current_pass = 0
        self.num_passes = self._determine_pass_count()
        if self.num_passes <= 0:
            raise RuntimeError("Warning: Module %s has no passes" % module)

    re_passfunc = re.compile(r'^pass(\d+)$')
    def _determine_pass_count(self):
        max_pass = 0
        for feed in self.feeds.values():
            for name in dir(feed):
                match = self.re_passfunc.match(name)
                if match:
                    max_pass = max(max_pass, int(match.groups()[0]))
        return max_pass

    def _initdb(self):
        """Reset and reinitialize the database for this test.

        This also creates the feeds as rows in the database, and assigns
        the a *database feed object* to each *test feed definition/class*,
        i.e.

            feed.dbobj for feed in self.feeds
        """
        # drop all existing tables
        result = db.store.execute("""SELECT name FROM sqlite_master
                                  WHERE type='table' ORDER BY name""")
        for row in result.get_all():
            db.store.execute('DROP TABLE "%s"' % row[0])

        # recreate tables (TODO: this needs to be dynamic!)
        db.store.execute("CREATE TABLE feed (id INTEGER PRIMARY KEY, url VARCHAR)")
        db.store.execute("CREATE TABLE item (id INTEGER PRIMARY KEY, feed_id INTEGER, guid VARCHAR)")

        # create feed rows
        for feed in self.feeds.values():
            dbobj = db.Feed()
            dbobj.url = u'http://feeds/%s' % feed.name()
            db.store.add(dbobj)
            feed.dbobj = dbobj
        db.store.flush()
        db.store.commit()

    def run(self):
        """Run the feed evolution.

        Current run-state (i.e. the current pass number) is shared
        instance-wide.

        If any test raises an exception, the test halts and is
        considered failed.
        """
        self._initdb()

        for self.current_pass in range(1, self.num_passes+1):
            for feed in self.feeds.values():
                parse.update_feed(feed.dbobj)
                testfunc = getattr(feed, 'pass%d'%self.current_pass, None)
                if testfunc:
                    try:
                        testfunc(feed.dbobj)
                    except Exception, e:
                        emsg = e.__class__.__name__
                        if str(e):
                            emsg = '%s (%s)' % (e, emsg)
                        raise Exception('Pass %d for "%s" failed: %s' %
                            (self.current_pass, feed.name(), emsg))


    tag_re = re.compile('{%(.*?)%}')
    def get_feed(self, name):
        """Return feed contents of ``name`` according to current pass.

        Because a test feed content may differ in different stages of
        the test, this function passes the feed content through a very
        simple templating engine.

        Used by ``MockHTTPHandler`` when feeds are requested through
        urllib2.
        """

        feed = self.feeds.get(name)
        if not feed:
            raise KeyError('Unknown feed: "%s"' % name)  # KeyError = 404

        # Get the feed content; if it is a callable, we give it the
        # current pass number. The result may be a string representing
        # the template to use, or a 2-tuple in which the second value
        # is a bool that if set to False will cause the rendering to
        # be skipped - e.g. the first tuple value will be the final
        # feed content for this pass.
        content = feed.content
        if callable(content):
            content = content(num_passes)
            if isinstance(content, (list, tuple,)):
                content, do_render = content
                if not do_render:
                    return content

        def evaluate_tag(expr):
            """Tests ``expr`` against ``current_pass``, returns a bool.

            Example input: 1, >1, =3, <2
            """

            # normalize: '\t> 5 ' => '>5'
            expr = expr.strip().replace(' ', '')

            p, v = expr[:2], expr[2:]             # two two char ops
            if not p in ('>=', '<=',):
                p, v = expr[:1], expr[1:]         # try one char ops
                if not (p in '<>='):
                    # assume now op specified, >= is the default
                    p = '>='
                    v = expr

            # if the op is valid, the rest must be a number
            if not v.isdigit():
                raise ValueError("'%s' not a valid tag expression " % expr)

            value = int(v)
            ops = {'=': (operator.eq,),
                   '>': (operator.gt,),
                   '<': (operator.lt,),
                   '>=': (operator.lt, operator.eq),
                   '<=': (operator.lt, operator.eq)}[p]
            return any([op(self.current_pass, value) for op in ops])

        # render the content using our very simple template language
        output = ""
        is_tag = True
        open_tags = 0
        skipping = False

        for bit in self.tag_re.split(content):
            is_tag = not is_tag
            token = bit.strip()

            if is_tag and token == 'end':
                skipping = False
                open_tags -= 1
                if open_tags < 0:
                    raise Exception('end tag mismatch')

            elif skipping:
                continue

            elif is_tag:
                open_tags += 1
                skipping = not evaluate_tag(token)

            else:
                output += bit

        if open_tags != 0:
            raise Exception('not all tags closed')

        return output

class MockHTTPMessage(httplib.HTTPMessage):
    """Encapsulates access to the (response) headers.

    Overridden to be initialized directly with a finished header
    dictionary instead of a file object that is read and parsed.

    The base class then provides methods like ``getheader()```on
    top of the dict. The feedparser library expects this, so we
    deliver.
    """
    def __init__(self, headers):
        self.dict = headers

class MockHTTPResponse(urllib.addinfourl):
    """Fake HTTP response that looks just like the real one, but
    initialized with the caller's custom data.

    Inherits from ``addinfourl`` but adds the capability to initialize
    using a string, instead of requiring a file-like object. It also adds
    the attributes required by urllib2's HTTP processing (eg.``code``).
    """
    def __init__(self, code, msg, headers, data, url=None):
        if isinstance(data, basestring):
            data = StringIO.StringIO(data)
        urllib.addinfourl.__init__(self, data, MockHTTPMessage(headers), url)

        self.code, self.msg = code, msg

class MockHTTPHandler(urllib2.BaseHandler):
    """Fake HTTP handler that serves the feeds available through a
    ``FeedEvolutionTestFramework`` instance.

    Implements some basic 304 (not modified) handling.

    We can't use a custom protocol and instead have to replace HTTP,
    since the feedparser library won't use urllib2 for unknown
    protocols (and instead falls back to ``open()``). But this way
    we're closer the "real thing" anyway, since the default HTTP
    processing of urllib2 will be active as well.
    """

    # we shall replace the default handler
    handler_order = urllib2.HTTPHandler.handler_order - 20

    def __init__(self, store):
        self.store = store

    def http_open(self, req):
        name = req.get_selector()[1:]    # remove leading /
        try:
            content = self.store.get_feed(name)
        except Exception, e:
            print >> sys.stderr, 'ERROR: Failed to render "%s": %s' % (name, e)
            content = ""
        return MockHTTPResponse(200, 'OK', {}, content)

    """def handle304Response(self, lmod, etag):
        ""
        From: http://midtoad.homelinux.org/FrogComplete/snakeserver/server.py
        Checks and handles the if-modified-since and etag headers
        If the check is positive (i.e. the resource is NOT modified),
        returns a 304 status and True ("handled").
        Otherwise, does nothing, and returns False ("not handled").
        ""
        IfModifiedSince = self.headers.get("If-Modified-Since", "")
        IfNoneMatch = self.headers.get("If-None-Match", "")
        IfMatch = self.headers.get("If-Match", "")
        if IfModifiedSince:
            # strip off IE-shit
            index = IfModifiedSince.find(';')
            if index >= 0:
                IfModifiedSince = IfModifiedSince[:index]
            # check lmod
            if lmod != IfModifiedSince:
                return False
        elif IfNoneMatch or IfMatch:
            # check if-none-match
            if IfNoneMatch and IfNoneMatch != '*':
                if etag not in [tag.strip() for tag in IfNoneMatch.split(',')]:
                    return False
            # check if-match
            if IfMatch:
                if IfMatch == '*' or etag in [tag.strip() for tag in IfMatch.split(',')]:
                    return False
        else:
            return False  # no 304 relevant header in use
        # resource wasn't modified, so return 304 not modified.
        self.send_response(304)
        self.end_headers()
        return True

        if not self.handle304Response(headers.get('Last-Modified'), headers.get('Etag')):
            # otherwise, send "normal" response
            if status: self.send_response(*status)
            else: self.send_response(200, 'OK')
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write("\n".join(data))"""

# import this in your tests
feedev = FeedEvolutionTestFramework()