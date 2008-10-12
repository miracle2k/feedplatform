"""Run the FeedPlatform bot, optionally as a daemon.

TODO: Add a remote control to enable people to inspect and interact
with an active bot. Imaginable are features like:

    #   get last X updated feeds
    #   get last X found items
    #   get last X log messages
    #   search for feeds
    #   prioritize a feed (e.g. update now) (and report log result/log)
"""

import os
import logging
from optparse import make_option

from feedplatform.management import BaseCommand, CommandError
from feedplatform import parse
from feedplatform import log
from feedplatform.deps import daemon


class Command(BaseCommand):
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

        # fork off as daemon, if requested
        if options.get('daemonize'):
            if os.name != 'posix':
                raise CommandError('--daemonize not supported on this platform')
            daemon.daemonize()

        try:
            parse.simple_loop()
        except KeyboardInterrupt:
            pass