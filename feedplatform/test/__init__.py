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
import inspect
import urllib, urllib2
import httplib
import traceback

# cStringIO is not subclassable and doesn't allow attribute assignment
import StringIO

from storm import variables as stormvars

from feedplatform.conf import config
from feedplatform import parse
from feedplatform import db
from feedplatform import log
from feedplatform import addins
from feedplatform.test import template


__all__ = ('testmod', 'testcaller', 'testcustom', 'File', 'Feed')


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
    # find all the files/feeds defined in the module
    files = {}
    for name, obj in ident_dict.iteritems():
        if isinstance(obj, type):
           if issubclass(obj, File):
               files[obj.name] = obj

    # a testcase usually defines which addins it uses
    addins = ident_dict.get('ADDINS', [])

    return testcustom(files, addins)


def testcustom(files, addins=[], run=True):
    """Test a custom set of feed and file classes, using the specified
    addins.

    Instead of a set of classes, you may also pass a dict of
    name => class pairs. Otherwise the name is deferred from the class.

    Example:

        testcustom([Feed1, Feed2, Feed3], addins=[myaddin])
        testcustom({'Feed1:': Feed1}, addins=[myaddin])
    """

    # internally, we need the name -> class syntax
    if not isinstance(files, dict):
        files_dict = {}
        for f in files:
            files_dict[f.__name__] = f
        files = files_dict

    # By this time the nose testrunner has redirected stdout. Reset
    # the log (it might still point to the real stdout) to make sure
    # that any messages will indeed be captured by nose.
    log.reset(level=logging.DEBUG)

    # run the test case
    test = FeedEvolutionTest(files, addins)
    if run:
        test.run()
    return test


class File(object):
    """A file needed due testing, made available through HTTP, like
    a feed image. It is also the baseclass of ``Feed``.

    Note that you should subclass ``Feed`` to write your testcases.
    No passes will be executed for a ``File`` class.

    Uses a metaclass to convert all functions to static methods,
    which makes testing easier since we don't have to deal with
    instances, or ``self`` arguments. Classes are merely used
    here to structure the testing code in a manner that easily
    allows multiple feeds (and files) per testcase.
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
                return u'http://files/%s' % cls.name
            elif name == 'status':
                return 200
            elif name == 'headers':
                return {}
            elif name == 'content':
                return ""
            else:
                raise AttributeError("%s" % name)


class Feed(File):
    """Baseclass for a single feed of an evolution.

    Currently, this is not much different than ``File``, but only
    subclasses of ``Feed`` are tested, i.e. it's passes run, whereas
    ``File`` simply makes it's content available, not more.
    """

    class __metaclass__(type(File)):

        def __getattr__(cls, name):
            # use a different default url for feeds
            if name == 'url':
                return u'http://feeds/%s' % cls.name
            else:
                return type(File).__getattr__(cls, name)


class FeedEvolutionTest(object):
    """Represents a single test case excecution with one or many
    evolving feeds, i.e. a single run through multiple parsing passes.

    We use one instance of this to have it run exactly one test.
    """

    def __init__(self, files, addins):
        self._files = files
        self.addins = addins
        self.current_pass = 0
        self.num_passes = self._determine_pass_count()

    @property
    def feeds(self):
        """Iterator that returns only the feeds from the set of
        specified ``File`` classes.
        """
        for obj in self._files.itervalues():
            if issubclass(obj, Feed):
                yield obj

    @property
    def files(self):
        """Iterate over all files. Analogous to ``feeds``.
        """
        for obj in self._files.itervalues():
            yield obj

    re_passfunc = re.compile(r'^pass(\d+)$')
    def _determine_pass_count(self):
        max_pass = 0
        for feed in self.feeds:
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
        for feed in self.feeds:
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

        if self.num_passes < 1:
            raise RuntimeError('No passes defined - nothing to test')

        # If the user hasn't specified anything, we'll use a
        # memory-based sqlite database.
        if not (config.configured and config.DATABASE):
            config.configure(**{'DATABASE': 'sqlite:'})

        # Remember the original handlers, so that we can *add* our
        # fake handler on each test, instead of overwriting handlers
        # that are defined in the configuration file - i.e. it is
        # possible to run tests with additional custom handlers.
        old_urllib2_handlers = config.URLLIB2_HANDLERS
        config.URLLIB2_HANDLERS = list(old_urllib2_handlers) +\
                                  [MockHTTPHandler(self),]

        try:
            config.ADDINS = self.addins
            addins.reinstall()

            # Bring both the database definition (models) as well as
            # the actual database (tables) up-to-date with this test's
            # requirements.
            db.reconfigure()
            self._initdb()

            for self.current_pass in range(1, self.num_passes+1):
                for feed in self.feeds:
                    testfunc = getattr(feed, 'pass%d'%self.current_pass, None)
                    # Try to be speedier by only parsing feeds when they
                    # actually have a handler for the current pass.
                    if testfunc:
                        parse.update_feed(feed.dbobj)

                        try:
                            testfunc(feed.dbobj)
                        except Exception, e:
                            # Re-raise the error as a new exception object
                            # with details about which feed/pass failed,
                            # as well as the traceback of the original
                            # exception.
                            emsg = e.__class__.__name__
                            if str(e):
                                emsg = '%s (%s)' % (e, emsg)
                            tb = re.sub(r'(^|\n)', r'\1    ', traceback.format_exc())
                            raise Exception('Pass %d for "%s" failed: %s\n\n'
                                'The test traceback was:\n%s' % (
                                    self.current_pass, feed.name, emsg, tb))
        finally:
            config.URLLIB2_HANDLERS = old_urllib2_handlers

    def get_file(self, url):
        """Return contents of ``url``, rendered for the current
        pass.

        Because a test feed/file content may differ in different
        stages of the test, this function passes the content
        through a very simple templating engine.

        Used by ``MockHTTPHandler`` when requests are made
        through urllib2.
        """

        fs = [f for f in self.files if f.url == url]
        if not fs:
            raise KeyError('No file for "%s"' % url)  # KeyError = 404
        # possibly multiple feeds with the same urls could exist, as
        # is required by some tests.
        feed = fs[0]

        def _resolve_from_feed(value):
            """Resolve a feed attribute that may also be a callable.

            If ``value`` is not a callable, it is passed through the
            template engine and returned.

            Otherwise, it is given the current pass number. If the
            return value is a 2-tuple of (content, render) where
            ``render`` is True, then content will be rendered before
            it is returned. Otherwise, the value is returned without
            rendering.

            Note that in the case of dicts, the dict values are
            rendered. Other non-string values are never rendered.
            """
            if callable(value):
                value = value(self.current_pass)
                if isinstance(value, (list, tuple,)):
                    value, do_render = value
                    if not do_render:
                        return value
                else:
                    return value
            if isinstance(value, dict):
                value = value.copy()
                for key in value:
                    value[key] = template.render(value[key], self.current_pass)
                return value
            elif not isinstance(value, basestring):
                return value
            return template.render(value, self.current_pass)

        try:
            status = int(_resolve_from_feed(feed.status))
        except ValueError, e:
            raise ValueError('status code must be a number (%s)' % e)
        headers = _resolve_from_feed(feed.headers)
        content = _resolve_from_feed(feed.content)
        return status, headers, content


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
    404: 'Not found',
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
            status, headers, content = self.store.get_file(url)
        except KeyError, e:
            # KeyError is meant as a 404
            status, headers, content = 404, {}, ""
        except Exception, e:
            # Exception will be swallowed by the feedparser lib anyway,
            # try to get some attention through a message (to stderr, or
            # it will be captured by nose).
            print >> sys.stderr, 'ERROR: Failed to render "%s": %s' % (url, e)
            raise
        else:
            # HTTP responses that contain unicode object's aren't really
            # what Univeral Feed Parser expects (lots of "Unicode equal
            # comparison failed" to stderr).
            if isinstance(content, unicode):
                content = content.encode('utf8')

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