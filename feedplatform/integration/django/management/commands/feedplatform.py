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
    CommandError as fp_CommandError

import sys, os
from django.core.management.base import BaseCommand

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

    def handle(self, *args, **options):
        try:
            subcommand = args[0]
        except IndexError:
            sys.stdout.write('Subcommand needed. Use "help" for usage.\n')
            sys.exit(1)

        try:
            if subcommand == 'help':
                if len(args) <= 1:
                    sys.stdout.write(_get_command_list()+"\n\n")
                else:
                    # let the feedplatform command print it's own help
                    fp_get_command(args[1]).print_help('feedplatform', args[1])
                sys.exit(1)

            else:
                # forward to feedplatform handler
                fp_call_command(subcommand, args[1:], **options)
        except fp_CommandError, e:
            sys.stdout.write("%s\n" %e)
            sys.exit(1)