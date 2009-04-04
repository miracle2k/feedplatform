import os
import logging
import threading
import SocketServer, select
from optparse import make_option
import Queue
from itertools import chain
from feedplatform import parse
from feedplatform import log
from feedplatform.deps import daemon
from feedplatform.management import BaseCommand, CommandError
from feedplatform import addins
from feedplatform import db


__all__ = ('base_daemon', 'provide_daemons', 'provide_loop_daemon',
           'provide_queue_daemon', 'provide_socket_queue_controller',
           'provide_multi_daemon',)


class StartDaemonCommand(BaseCommand):
    """Run the FeedPlatform bot, optionally as a daemon.

    TODO: Add a remote control to enable people to inspect and interact
    with an active bot. Imaginable are features like:

        #   get last X updated feeds
        #   get last X found items
        #   get last X log messages
        #   search for feeds
        #   prioritize a feed (e.g. update now) (and report log result/log)
    """

    option_list = BaseCommand.option_list + (
        make_option('--log', default=None,
            help='A file where log and status messages will be emitted. If '
                 'not given, stdout is used.'),
        make_option('--level', default="info",
            help='The minimum log level to output, e.g. "debug" or '
                  '"warning". Messages below this are ignored.'),
        make_option('--daemonize', action='store_true', default=False,
            help='Fork off and run as a daemon. Not available on all OSes.'),
    )
    help = 'Runs the FeedPlatform bot.'

    def handle(self, *args, **options):

        # setup the log according to the options requested
        loglevel = options.get('level')
        if loglevel:
            try:
                loglevel = logging._levelNames[loglevel.upper()]
            except KeyError:
                raise CommandError('invalid value for --level: %s' % loglevel)

        logfile = options.get('log')
        if logfile:
            filehandler = logging.FileHandler(logfile)
            filehandler.setFormatter(logging.Formatter(
                '%(asctime)-18s %(name)-12s: %(levelname)-8s %(message)s',
                '%m-%d-%y %H:%M:%S'))
            handlers=[filehandler]
        else:
            handlers = None

        if loglevel or handlers:
            log.reset(level=loglevel, handlers=handlers)


        # determine which daemons are available, and which one to run
        # TODO: better handle duplicate names
        named_daemons = {}
        unnamed_daemons = []
        for addin in addins.get_addins():
            if isinstance(addin, base_daemon):
                if addin.name:
                    named_daemons[addin.name] = addin
                else:
                    unnamed_daemons.append(addin)

        args = list(args)   # make mutable

        if len(named_daemons) + len(unnamed_daemons) == 1:
            # If only one daemon is available, we can start it pretty
            # much right away.
            if named_daemons and named_daemons.keys()[0] == args[0]:
                # If the user specified the only existing daemon by
                # name, we make sure that name is not passed along
                # as a subargument to the daemon itself.
                args.remove(args[0])
            daemon_to_start = unnamed_daemons and \
                unnamed_daemons[0] or \
                named_daemons.values()[0]
        # Otherwise, we have to determine which one the use wants to start
        else:
            s_daemon_list = ''
            for name in named_daemons.keys():
                s_daemon_list += '    %s\n' % name
            if unnamed_daemons:
                s_daemon_list += 'Additionally, %d unnamed daemons are '+\
                    'installed.\n' % len(unnamed_daemons)

            if len(args) == 0:
                raise CommandError('multiple daemons are installed, you '
                                   'need to specify which one to run:\n%s' %
                                        s_daemon_list)
            else:
                daemon_name = args[0]
                args.remove(args[0])
                if not daemon_name in named_daemons:
                    raise CommandError('"%s" is not a known daemon, '+
                                       'installed are:\n%s' % s_daemon_list)
                else:
                    daemon_to_start = named_daemons[daemon_name]

        # fork off as daemon, if requested
        if options.get('daemonize'):
            if os.name != 'posix':
                raise CommandError('--daemonize not supported on this platform')
            daemon.daemonize()

        try:
            # If daemon threads make trouble (http://bugs.python.org/issue1856),
            # we can always disable it. It's there for convenience's sake,
            # but our daemons/threads have a stop-flag mechanism that should
            # work just fine as well.
            daemon_to_start.setDaemon(True)
            # TODO: parse the rest of the args, pass along as args/options
            daemon_to_start.start()
            while daemon_to_start.isAlive():
                daemon_to_start.join(0.5)
        except KeyboardInterrupt:
            daemon_to_start.stop()


class provide_daemons(addins.base):
    """Core addin that provides the ``start`` command and the base
    daemon infrastructure.
    """

    def get_commands(self):
        return {'start': StartDaemonCommand}


class base_daemon(addins.base, threading.Thread):
    """Base class for run daemons.

    Inheriting from this class makes sure your daemon can be found by the
    ``start`` command. At the same time, it will also ensure that the
    command is installed in the first place when your addin is used.

    ``run()`` is called when the daemon is supposed to execute. In the
    same way as commands, the method is passed positional arguments (as
    ``args``) and command line options (``options``). If you write a
    subclass, make sure that your ``run`` method checks ``stop_requested``
    in regular intervals, and exits when asked to.

    While not strictly necessary, it is strongly recommended that you name
    your daemons (``name`` argument to ``__init__``). If you have more than
    one daemon installed, you will not be able to start unnamed daemons
    from the command line.
    """

    abstract = True
    depends = (provide_daemons,)

    def __init__(self, name=None):
        super(base_daemon, self).__init__()
        self.name = name
        self.stop_requested = False

    def run(self, *args, **options):
        raise NotImplementedError()

    def stop(self):
        self.stop_requested = True


class provide_loop_daemon(base_daemon):
    """Simple daemon that loops through all available feeds.

    If ``once`` is enabled, the daemon will stop after going through
    the database the first time, rather than starting over.

    ``callback``, if set, will be run every time a feed was updated,
    and is expected to take one argument, the number of iterations so
    far. If it returns ``True``, the loop will stop.
    """

    def __init__(self, once=False, callback=None, *args, **kwargs):
        self.once = once
        self.callback = callback
        super(provide_loop_daemon, self).__init__(*args, **kwargs)

    def run(self, *args, **options):
        """Loop forever, and update feeds.

        # TODO: take options from the command line that we pass on to
        ``update_feed``, changing the parsing behavior (addins can
        use the options to adjust their behavior).
        """
        # Code below fails in sqlite because we can't update a row
        # while it is still part of queryset, IIRC:
        #feed = db.store.get_next_feed()
        #while feed:
        #    update_feed(feed)
        #    feed = db.store.get_next_feed()
        callback = self.callback
        do_return = lambda: callback and callback(counter)
        counter = 0
        while True:
            feeds = db.store.find(db.models.Feed)
            for i in xrange(0, feeds.count()):  # XXX: only do this in sqlite
                feed = feeds[i]
                counter += 1
                parse.update_feed(feed)
                if do_return() or self.stop_requested:
                    return
            if do_return() or self.stop_requested:
                return
            if self.once:
                return


class provide_queue_daemon(base_daemon):
    """Parses the feeds that are in the given queue. If the queue is
    empty, it waits until new feeds are added.

    Python's ``Queue`` module is used (``queue`` in Python 3).

    This addin is commonly used to support "ping"-like services.

    Example:

        queue = collections.deque()
        [...
         provide_queue_daemon(queue),
        ...]

    # TODO: add option to work as a LIFO stack.

    TODO: Support a mgmt command to add stuff to a queue (and possibly
    other actions, like query, pop). This should probably be implemented
    as another addin, and needs to support multiple queues.
    """

    def __init__(self, queue, *args, **kwargs):
        super(provide_queue_daemon, self).__init__(*args, **kwargs)
        self.queue = queue

    def run(self):
        while not self.stop_requested:
            try:
                # Since Queue itself just uses an infinite loop,
                # we don't have to bother with using a large timeout
                # and can instead check stop_requested more often.
                feed = self.queue.get(timeout=0.1)
                try:
                    # we need to be careful here, there's really no guarantee
                    # that the feed still exists.
                    parse.update_feed(feed)
                except:
                    # TODO: do not catch all exceptions
                    # TODO: log an error
                    pass
            except Queue.Empty:
                pass


class provide_socket_queue_controller(base_daemon):
    """Provides a socket (TCP or UNIX local) which can be used to put
    feeds on a queue, as processed by ``provide_queue_daemon``.

    ``socket`` must be either a filename, or 2-tuple of (hostname, port).

    If your queue ``queue_timeout``

    The protocol spoken is pretty simple: The daemon expects each queue
    put request on a separate line, and each line may either consist
    of the feed's id or an url. In the latter case the url column should
    be unique - if multiple feeds currently match such a request, the
    daemon will respond with a 500 error.
    The response is a status line in HTTP format ("CODE MSG"), with CODE
    being one of the following:

        200    ok, feed was added to queue
        304    the feed is already in the queue, nothing was done
        404    the given feed does not exist in the database
        500    something unexpected went wrong
        507    queue is full (if limited)

    The encoding used is utf8.
    """

    class SocketControllerHandler(SocketServer.StreamRequestHandler):
        def handle(self):
            result = '200 Ok'
            try:
                rstr = self.rfile.readline().strip()
                if rstr.isdigit():
                    feed = db.store.get(db.models.Feed, int(rstr))
                else:
                    feed = db.get_one(db.store.find(
                        db.models.Feed, db.models.Feed.url == \
                            unicode(rstr, 'utf8')))

                if not feed:
                    result = '404 Feed not found'
                else:
                    # We're accessing queue's internal ``deque`` object
                    # here, in order to be able to use "in". Since we're
                    # locking with the mutex, we should be perfectly safe
                    # (it might not even be necessary).
                    self.server.queue.mutex.acquire()
                    try:
                        exists = feed in self.server.queue.queue
                    finally:
                        self.server.queue.mutex.release()
                    if not exists:
                        try:
                            self.server.queue.put(feed,
                                self.server.queue_timeout)
                        except Queue.Full:
                            result = '507 Queue is full'
                    else:
                        result = '304 Feed already in queue'
            except Exception, e:
                result = '500 %s' % e
            self.wfile.write("%s\n"%result)

    def __init__(self, queue, socket, timeout=None, *args, **kwargs):
        super(provide_socket_queue_controller, self).__init__(*args, **kwargs)
        self.queue = queue
        self.socket = socket
        self.queue_timeout = timeout

    def run(self, *args, **options):
        server_class = isinstance(self.socket, basestring) and \
            SocketServer.ThreadingUnixStreamServer or \
            SocketServer.ThreadingTCPServer
        server = server_class(self.socket,
            provide_socket_queue_controller.SocketControllerHandler)
        server.queue = self.queue
        server.queue_timeout = self.queue_timeout
        while not self.stop_requested:
            r,w,e = select.select([server.socket], [], [], 0.5)
            if r:
                server.handle_request()


class provide_multi_daemon(base_daemon):
    """Virtual daemon that can consolidate a number of other daemons,
    and run them under the same label.

    Any number of daemons can be passed. If a single daemon is designated
    the "main daemon", it will be passed along the given arguments.
    Otherwise, no arguments are supported.

    For example, the following is a common use case that installs
    a queue daemon, and a controller daemon that allows putting stuff
    on that queue from the outside:

        [...
        provide_multi_daemon(
            provide_queue_daemon(...),
            [provide_socket_queue_controller(...)],
            name='queue'
        )
        ...]

    # TODO: an alternative implementation could override start() isAlive()
    join() etc. and instead of acting like a thread itself, would merely
    fake one. isALive/join() would return once all threads return False.
    """

    def __init__(self, main_daemon=None, daemons=[],
                 *args, **kwargs):
        assert main_daemon or daemons
        super(provide_multi_daemon, self).__init__(*args, **kwargs)
        self.main_daemon = main_daemon
        self.other_daemons = daemons

    @property
    def all_daemons(self):
        return [d for d in chain([self.main_daemon], self.other_daemons) if d]

    def run(self, *args, **options):
        for d in self.all_daemons:
            d.start()
        while any([d.isAlive() for d in self.all_daemons]) and \
              not self.stop_requested:
            pass
        for d in self.all_daemons:
            d.stop()
        while any([d.isAlive() for d in self.all_daemons]):
            # wait until they all stopped
            pass
