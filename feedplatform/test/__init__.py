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

The module provides multiple entrypoints like ``testmod`` or
``testscustom``, all of which runs a specific set of "feed evolution"
tests (e.g. as defined in the module), meaning it will cause the defined
feeds to be added to the database, parsed through multiple passes as
requested, and the test callbacks being called.

Example of a nose test module using this infrastructure (not using
real feed contents for simplicity):

    from feedplatform import test as feedev

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

Futher, the following class attributes are supported for such a test
feed:

    * ``url``: A (fake) url for the feed. Needed, for example, for
      testing redirects.
    * ``status``: The HTTP status code to use for the response.
    * ``headers``: Headers to pass along with the response (as a dict).
"""

import os, sys
import re
import types
import logging
import operator
import inspect
import urllib, urllib2
import httplib

# cStringIO is not subclassable and doesn't allow attribute assignment
import StringIO

from storm import variables as stormvars

from feedplatform.conf import config
from feedplatform import parse
from feedplatform import db
from feedplatform import log
from feedplatform import addins


__all__ = ('testmod', 'testcaller', 'testcustom', 'Feed')


def testmod(module=None):
    """Test the caller's module.

    Differs from doctest's ``testmod``` in that it actually tests
    the **caller** if not explicit module reference was passed,
    whereas doctest would just use ``__main__``.
    """

    # If no explicit module was passed, try to find the caller's
    # module by inspecting the stack.
    # Use the try-finally pattern explained in the docs:
    # http://docs.python.org/lib/inspect-stack.html
    if not module:
        frame = inspect.stack()[1][0]
        try:
            module = sys.modules[frame.f_globals['__name__']]
        finally:
            del frame

    namespace = dict([(name, getattr(module, name)) for name in dir(module)])
    return _collect_and_test(namespace)


def testcaller():
    """Test the caller's local namespace.

    The global namespace is **ignored** by this.
    """

    # Use the try-finally pattern explained in the docs:
    # http://docs.python.org/lib/inspect-stack.html
    frame = inspect.stack()[1][0]
    try:
        namespace = frame.f_locals
        name = "%s in %s" % (frame.f_code.co_name, frame.f_globals['__name__'])
    finally:
        del frame

    return _collect_and_test(namespace)


def _collect_and_test(ident_dict):
    # find all the test feeds defined in the module
    feeds = {}
    for name, obj in ident_dict.iteritems():
        if isinstance(obj, type):
           if issubclass(obj, Feed):
               feeds[obj.name] = obj

    # a testcase usually defines which addins it uses
    addins = ident_dict.get('ADDINS', [])

    return testcustom(feeds, addins)


def testcustom(feeds, addins=[]):
    """Test a custom set of feed classes, using the specified addins.

    Instead of a set of feed classes, you may also pass a dict of
    name => class pairs. Otherwise the name is deferred from the class.

    Example:

        testcustom([Feed1, Feed2, Feed3], addins=[myaddin])
        testcustom({'Feed1:': Feed1}, addins=[myaddin])
    """

    if not feeds:
        raise RuntimeError('No feeds specificed, nothing to test.')

    if not isinstance(feeds, dict):
        feed_dict = {}
        for feed in feeds:
            feed_dict[feed.__name__] = feed
        feeds = feed_dict

    # By this time the nose testrunner has redirected stdout. Reset
    # the log (it might still point to the real stdout) to make sure
    # that any messages will indeed be captured by nose.
    log.reset(level=logging.DEBUG)

    # run the test case
    test = FeedEvolutionTest(feeds, addins)
    test.run()


class Feed(object):
    """Baseclass for a single feed of an evolution.

    Uses a metaclass to convert all functions to static methods,
    which makes testing easier since we don't have to deal with
    instances, or ``self`` arguments. Classes are merely used
    here to structure the testing code in a manner that easily
    allows multiple feeds per testcase.
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

        def __getattr__(cls, name):
            # provide default values for attributes a test feed
            # doesn't explicitely specify
            if name == 'name':
                return cls.__name__
            elif name == 'url':
                return u'http://feeds/%s' % cls.name
            elif name == 'status':
                return 200
            elif name == 'headers':
                return {}
            else:
                raise AttributeError("%s" % name)


class FeedEvolutionTest(object):
    """Represents a single test case exceution with one or many
    evolving feeds, i.e. a single run through multiple parsing passes.

    We use one instance of this to have it run exactly one test.
    """

    def __init__(self, feeds, addins):
        self.feeds = feeds
        self.addins = addins
        self.current_pass = 0
        self.num_passes = self._determine_pass_count()

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

        This also creates the feeds as rows in the database, and
        assigns the a **database feed object** to each **test feed
        definition/class**, i.e.

            feed.dbobj for feed in self.feeds
        """

        # Drop all existing tables; normally, since we are using a memory
        # sqlite db, a ``db.reconfigure()`` would be enough; we want to
        # optionally support other db setups as well, though.
        result = db.store.execute("""SELECT name FROM sqlite_master
                                  WHERE type='table' ORDER BY name""")
        for row in result.get_all():
            db.store.execute('DROP TABLE "%s"' % row[0])

        # recreate tables - since storm can't do schema creation, we
        # have to implement this in a very basic version ourselfs.
        for model_name, model in db.models.iteritems():
            field_sql = []
            # TODO: all this is untested with model inheritance
            for field in model._storm_columns:
                field_name = field._detect_attr_name(model)  # field._name is None?
                modifers = field._primary and ' PRIMARY KEY' or ''
                try:
                    ctype = {stormvars.IntVariable: 'INTEGER',
                             stormvars.UnicodeVariable: 'VARCHAR',
                             stormvars.DateTimeVariable: 'TIMESTAMP',
                                }[field._variable_class]
                except KeyError:
                    raise TypeError(('Cannot build %s table, unknow field '
                        'type %s of %s. You probably want to extend the '
                        'test framework''s schema builder to support this '
                        'type.') % (model_name, field, field_name))
                field_sql.append("%s %s%s" % (field_name, ctype, modifers))

            create_stmt = 'CREATE TABLE %s (%s)' % (
                model_name.lower(), ", ".join(field_sql))
            db.store.execute(create_stmt)

        # create feed rows
        for feed in self.feeds.values():
            dbobj = db.models.Feed()
            dbobj.url = feed.url
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

        # if the user hasn't specified anything, we'll use a
        # memory-based sqlite database.
        if not (config.configured and config.DATABASE):
            config.configure(**{'DATABASE': 'sqlite:'})
            db.reconfigure()

        # Remember the original handlers, so that we can *add* our
        # fake handler on each test, instead of overwriting handlers
        # that are defined in the configration file - i.e. it is
        # possible to run tests with additional custom handlers.
        old_urllib2_handlers = config.URLLIB2_HANDLERS
        config.URLLIB2_HANDLERS = list(old_urllib2_handlers) +\
                                  [MockHTTPHandler(self),]

        try:
            config.ADDINS = self.addins
            addins.reinstall()

            self._initdb()

            for self.current_pass in range(1, self.num_passes+1):
                for feed in self.feeds.values():
                    testfunc = getattr(feed, 'pass%d'%self.current_pass, None)
                    # Try to be speedier by only parsing feeds when they
                    # actually have a handler for the current pass.
                    if testfunc:
                        parse.update_feed(feed.dbobj)

                        try:
                            testfunc(feed.dbobj)
                        except Exception, e:
                            emsg = e.__class__.__name__
                            if str(e):
                                emsg = '%s (%s)' % (e, emsg)
                            raise Exception('Pass %d for "%s" failed: %s' %
                                (self.current_pass, feed.name, emsg))
        finally:
            config.URLLIB2_HANDLERS = old_urllib2_handlers


    tag_re = re.compile('{%(.*?)%}')
    def get_feed(self, url):
        """Returns feed contents of ``url``, rendered for the current
        pass.

        Because a test feed content may differ in different stages of
        the test, this function passes the feed content through a very
        simple templating engine.

        Used by ``MockHTTPHandler`` when feeds are requested through
        urllib2.
        """

        fs = [f for f in self.feeds.values() if f.url == url]
        if not fs:
            raise KeyError('No feed for "%s"' % key)  # KeyError = 404
        # possibly multiple feeds with the same urls could exist, as
        # is required by some tests.
        feed = fs[0]

        # get response code and headers
        status = feed.status
        headers = feed.headers

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
                   '>=': (operator.gt, operator.eq),
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
                open_tags -= 1
                if open_tags < 0:
                    raise Exception('end tag mismatch')
                if open_tags < skipping:
                    skipping = False

            elif is_tag:
                open_tags += 1
                if not skipping:
                    if not evaluate_tag(token):
                       # skip until tag-level falls below current state
                       # again, e.g. account for nested tags to find
                       # the right "end", from where we'll pick it up.
                       skipping = open_tags

            elif skipping:
                continue

            else:
                output += bit

        if open_tags != 0:
            raise Exception('not all tags closed')

        return status, headers, output

class MockHTTPMessage(httplib.HTTPMessage):
    """Encapsulates access to the (response) headers.

    Overridden to be initialized directly with a finished header
    dictionary instead of a file object that is read and parsed.

    The base class then provides methods like ``getheader()``` on
    top of the dict.

    The feedparser library expects those features, so we deliver.
    """
    def __init__(self, headers):
        self.dict = dict([(k.lower(), v) for k, v in headers.iteritems()])
        # MRO goes up to ``rfc822.Message``, some of which's
        # methods depend on self.headers (example: ``getheaders()``,
        # which is supposed to be a *list*. Others use ``self.dict``.
        # The base classes generate ``dict`` based on ``headers``,
        # we do the reverse.
        self.headers = ["%s: %s" % (k, v) for k, v in headers.iteritems()]


class MockHTTPResponse(urllib.addinfourl):
    """Fake HTTP response that looks just like the real one, but
    initialized with the caller's custom data.

    Inherits from ``addinfourl`` but adds the capability to initialize
    using a string, instead of requiring a file-like object. It also adds
    the attributes required by urllib2's HTTP processing (eg.``code``).
    """
    def __init__(self, code, msg, headers, data, url):
        if isinstance(data, basestring):
            data = StringIO.StringIO(data)
        urllib.addinfourl.__init__(self, data, MockHTTPMessage(headers), url)

        self.code, self.msg = code, msg

# just to be extra nice, in reality the message doesn't matter
HTTP_RESPONSE_MSGS = {
    200: 'OK',
    301: 'Permanent redirect',
    302: 'Temporary redirect',
}

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
        url = req.get_full_url()
        try:
            status, headers, content = self.store.get_feed(url)
        except Exception, e:
            # Exception will be swallowed by the feedparser lib anyway,
            # try to get some attention through a message (to stderr, or
            # it will be captured by nose).
            print >> sys.stderr, 'ERROR: Failed to render "%s": %s' % (url, e)
            raise
        return MockHTTPResponse(status,
            HTTP_RESPONSE_MSGS.get(status, 'Unknown'), headers, content, url)

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