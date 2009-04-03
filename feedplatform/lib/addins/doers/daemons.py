import os
import logging
import threading
from optparse import make_option
from feedplatform import parse
from feedplatform import log
from feedplatform.deps import daemon
from feedplatform.management import BaseCommand, CommandError
from feedplatform import addins
from feedplatform import db


__all__ = ('base_daemon', 'provide_daemons', 'provide_loop_daemon',)


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
            # TODO: parse the rest of the args, pass along as args/options
            # TODO: does it make sense to make the daemon addin subclasses
            # of Thread?
            thread = threading.Thread(target=daemon_to_start.run)
            thread.start()
            while thread.isAlive():
                thread.join(0.5)
        except KeyboardInterrupt:
            daemon_to_start.stop()


class provide_daemons(addins.base):
    """Core addin that provides the ``start`` command and the base
    daemon infrastructure.
    """

    def get_commands(self):
        return {'start': StartDaemonCommand}


class base_daemon(addins.base):
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

    def __init__(self, once=False, callback=None):
        self.once = once
        self.callback = callback
        super(provide_loop_daemon, self).__init__()

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
