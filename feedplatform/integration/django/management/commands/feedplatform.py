"""Attempt to make the FeedPlatform command line tools available as
a Django management subcommand.
"""

# Introducing a 2.5 dependency here so we can name our django
# command "feedplatform" (i.e. same as the top-level module).
# Unfortunately, Django names commands always after their filename.
from __future__ import absolute_import
from feedplatform.management import \
    call_command as fp_call_command, \
    get_command as fp_get_command, \
    get_commands as fp_get_commands, \
    BaseCommand as fp_BaseCommand, \
    CommandError as fp_CommandError, \
    UnknownCommandError as fp_UnknownCommandError, \
    ManagementUtility as fp_ManagementUtility

import sys, os
from django.core.management.base import BaseCommand
from django.core.management import LaxOptionParser


# The --config and --pythonpath options are useless when run
# through the django integration command; the config is fixed,
# and django's management interface itself already handled a
# --pythonpath option, if set. So we remove them.
new_options = []
for option in fp_BaseCommand.option_list:
    if not option.dest in ['config', 'pythonpath']:
        new_options.append(option)
fp_BaseCommand.option_list = tuple(new_options)


def _get_command_list():
    result = "Available subcommands:\n"
    for command in fp_get_commands():
        result += '\n  %s' % command
    return result


class Command(BaseCommand):
    help = "Gateway to the FeedPlatform management tool.\n\n" + _get_command_list()
    args = '[SUBCOMMAND]'

    def create_parser(self, prog_name, subcommand):
        # LaxOptionParser will ignore argument errors. We need this since
        # all the options that are intended for the FeedPlatform command
        # are not supported by this Django-wrapper command and would
        # otherwise cause it to fail.
        parser = super(Command, self).create_parser(prog_name, subcommand)
        parser.__class__ = LaxOptionParser
        return parser

    def handle(self, *args, **options):
        """
        When this is called, ``options`` will contain the valid
        Django-level options that have been found, including those
        potentially supported by this (Django)-command.

        ``args`` contains everything else, the arguments as well as all
        the unsupported options, which we want to give to the
        FeedPlatform-level command. If that can't handle them either,
        then we can raise an error.

        So for example, the following call:

            ./manage.py feedplatform run --daemonize --pythonpath .

        results in:

            args = ('run', '--daemonize')
            options = {'pythonpath': '.', 'traceback': None, 'settings': None}
        """

        try:
            subcommand = args[0]
        except IndexError:
            sys.stdout.write('Subcommand needed. Use "help" for usage.\n')
            sys.exit(1)

        try:
            # special case the "help" command, since the default version
            # by is unaware of the wrapping and it's subcommand status and
            # displays the "Usage: ..." line incorrectly.
            if subcommand == 'help':
                if len(args) <= 1:
                    sys.stdout.write(_get_command_list()+"\n\n")
                else:
                    # let the feedplatform command print it's own help
                    fp_get_command(args[1]).print_help('feedplatform', args[1])
                sys.exit(1)

            else:
                # forward to feedplatform handler
                fp_get_command(subcommand).run_from_argv(
                    sys.argv[:1] + [subcommand] + list(args[1:]))

        except fp_UnknownCommandError, e:
            self._fail("Unknown subcommand: %s\n" %e.name)
        except fp_CommandError, e:
            self._fail("%s\n" %e)

    def _fail(self, msg):
        sys.stdout.write(msg)
        sys.stderr.write("Type '%s feedplatform help' for usage.\n" %
            os.path.basename(sys.argv[0]))
        sys.exit(1)