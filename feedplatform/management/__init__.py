"""Backend for management and control functionality.

Inspired by Django's ``core.management`` module.
"""

import sys, os
from optparse import OptionParser, make_option
from feedplatform.addins import get_addins


__all__ = ('CommandError', 'UnknownCommandError',
           'reload_commands', 'get_command', 'call_command',
           'BaseCommand', 'NoArgsCommand',)


class CommandError(Exception):
    """Use to indicate an invalid or unknown command, or a problem with
    the command configuration, the arguments etc.
    """

class UnknownCommandError(Exception):
    """Use to indicate the use of an invalid command name.

    Makes the erroneous name available as an attribute.
    """
    def __init__(self, message, name):
        CommandError.__init__(self, message)
        self.name = name


_COMMANDS = None


def reload_commands():
    global _COMMANDS;
    _COMMANDS = None


def get_commands():
    """Returns a dictionary mapping all available command names to
    either a Command class, or the module name in which the command
    class is defined.

    Commands can be defined:

        - in ``feedplatform/management/commands``, each file
          representing an individual command.

        - by addins.

    The list is loaded once, and then cached.
    """
    global _COMMANDS
    if _COMMANDS is None:
        _COMMANDS = {}
        # load from filesystem
        try:
            command_dir = os.path.join(__path__[0], 'commands')
            _COMMANDS.update(
                dict([(file[:-3], 'feedplatform.management.commands')
                      for file in os.listdir(command_dir)
                        if not file.startswith('_')
                           and file.endswith('.py')]))
        except OSError:
            pass

        # load from addins
        for addin in get_addins():
            if hasattr(addin, 'get_commands'):
                _COMMANDS.update(addin.get_commands());

    return _COMMANDS


def get_command(name):
    """Return a command instance by name.

    The command module is loaded and the command instantiated, and
    will be reused if accessed again.
    """
    global _COMMANDS
    try:
        module_name = get_commands()[name]
        if isinstance(module_name, BaseCommand):
            # if the command is already loaded, use it directly
            return module_name
        if isinstance(module_name, type) and issubclass(module_name, BaseCommand):
            # probably comes from an addin
            return module_name()
        else:
            module = __import__('%s.%s' % (module_name, name),
                                {}, {}, ['Command'])
            cmd = getattr(module, 'Command')()
            _COMMANDS[name] = cmd  # use directly next time
            return cmd
    except KeyError:
        raise UnknownCommandError("Unknown command: %r" % name, name)


def call_command(command, *args, **options):
    """Manually runs a command. This is the primary API you should
    use for calling specific commands from your own code.

    ``command`` may be a string specifiying the command name, or
    a ``BaseCommand`` instance.

    Examples:
        call_command('tables')
        call_command('start', '--daemonize')
        call_command('stop')
    """
    if not isinstance(command, BaseCommand):
        command = get_command(command)
    return command.execute(*args, **options)


class LaxOptionParser(OptionParser):
    """Option parser that doesn't raise errors on unknown options.

    Used to preprocess the --config and --pythonpath options.
    """
    def error(self, msg):
        pass


class ManagementUtility(object):
    """Encapsulates the logic of the ``feedplatform.py`` control script.
    """

    def __init__(self, argv=None):
        self.argv = argv or sys.argv[:]
        self.prog_name = os.path.basename(self.argv[0])

    def show_help(self):
        """Returns the script's main help text, as a string.
        """
        usage = ['%s <subcommand> [options] [args]' % self.prog_name]
        usage.append('FeedPlatform command line tool')
        usage.append('')
        usage.append("Type '%s help <subcommand>' for help on a specific "
            "subcommand." % self.prog_name)
        usage.append('')
        usage.append('Available subcommands:')
        commands = get_commands().keys()
        commands.sort()
        for cmd in commands:
            usage.append('  %s' % cmd)
        sys.stdout.write('\n'.join(usage)+'\n')
        return 1

    def execute(self):
        """Using the command-line arguments given to the instance,
        this figures out which command was requested, creates a parser
        appropriate to that command, and runs it.
        """

        # Preprocess options to handle --config and --pythonpath. Right
        # now, this is not strictly necessary, but in the future those
        # options could affect the commands that are available (e.g. a
        # config file could provide custom commands), so they would have
        # to be processed early.
        parser = LaxOptionParser(option_list=BaseCommand.option_list)
        try:
            options, args = parser.parse_args(self.argv)
            if options.config:
                from feedplatform.conf import ENVIRONMENT_VARIABLE
                os.environ[ENVIRONMENT_VARIABLE] = options.config
            if options.pythonpath:
                sys.path.insert(0, options.pythonpath)
        except:
            pass  # ignore option errors at this point

        try:
            if len(self.argv) <= 1:
                raise CommandError()
            command = self.argv[1]

            # special case the help command
            if command == 'help':
                if len(args) > 2:
                    return get_command(args[2]).print_help(self.prog_name, args[2])
                else:
                    return self.show_help()
            elif self.argv[1:] == ['--help']:
                return self.show_help()

            # run the requested command
            return get_command(command).run_from_argv(self.argv)
        except CommandError, e:
            if str(e):
                sys.stderr.write("%s\n" % e)
            sys.stderr.write("Type '%s help' for usage.\n" % self.prog_name)
            return 1

    @classmethod
    def execute_from_command_line(cls, argv=None):
        sys.exit(cls(argv).execute() or 0)


class BaseCommand(object):
    # metadata about this command: amend or overwrite in subclasses.
    option_list = (
        make_option('--config',
            help='The path (filesystem or python) to a config file. '
                 'If this isn\'t provided, the FEEDPLATFORM_CONFIG '
                 'environment variable will be used.'),
        make_option('--pythonpath',
            help='A directory to add to the Python path, e.g. '
                 '/usr/local/myapp".'),
    )
    help = ''
    args = ''

    def usage(self, subcommand):
        usage = '%%prog %s [options] %s' % (subcommand, self.args)
        if self.help:
            return '%s\n\n%s' % (usage, self.help)
        else:
            return usage

    def create_parser(self, prog_name, subcommand):
        return OptionParser(prog=prog_name,
                            usage=self.usage(subcommand),
                            option_list=self.option_list)

    def print_help(self, prog_name, subcommand):
        parser = self.create_parser(prog_name, subcommand)
        parser.print_help()

    def run_from_argv(self, argv):
        parser = self.create_parser(os.path.basename(argv[0]), argv[1])
        options, args = parser.parse_args(argv[2:])
        return self.execute(*args, **options.__dict__)

    def execute(self, *args, **options):
        try:
            output = self.handle(*args, **options)
            if output:
                print output
            return 0
        except CommandError, e:
            sys.stderr.write(str('Error: %s\n' % e))
            return 1

    def handle(self, *args, **options):
        raise NotImplementedError()


class NoArgsCommand(BaseCommand):
    args = ''

    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")
        return self.handle_noargs(**options)

    def handle_noargs(self, **options):
        raise NotImplementedError()