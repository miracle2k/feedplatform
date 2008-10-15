"""
Adapted from ``django.core.management.commands.shell``.
"""

import os
from feedplatform.management import NoArgsCommand
from optparse import make_option

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--plain', action='store_true', dest='plain',
            help='Tells FeedPlatform to use plain Python, not IPython.'),
    )
    help = "Runs a Python interactive interpreter. Tries to use IPython, if it's available."

    def handle_noargs(self, **options):
        use_plain = options.get('plain', False)

        try:
            if use_plain:
                raise ImportError
            import IPython
            # explicitly pass an empty list as arguments, because
            # otherwise IPython would use sys.argv from this script
            shell = IPython.Shell.IPShell(argv=[])
            shell.mainloop()

        except ImportError:
            import code

            try:
                # try activating rlcompleter, because it's handy
                import readline
            except ImportError:
                pass
            else:
                import rlcompleter
                readline.set_completer(rlcompleter.Completer(imported_objects).complete)
                readline.parse_and_bind("tab:complete")

            # We want to honor both $PYTHONSTARTUP and .pythonrc.py,
            # so follow system conventions and get $PYTHONSTARTUP first
            # then import user.
            if not use_plain:
                pythonrc = os.environ.get("PYTHONSTARTUP")
                if pythonrc and os.path.isfile(pythonrc):
                    try:
                        execfile(pythonrc)
                    except NameError:
                        pass
                # this will import .pythonrc.py as a side-effect
                import user

            imported_objects = {}
            code.interact(local=imported_objects)