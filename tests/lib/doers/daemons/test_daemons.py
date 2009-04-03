"""Test the general daemon infrastructure, daemon base classes etc.
"""

import sys
import StringIO
from nose.tools import assert_raises
from feedplatform.lib import base_daemon
from feedplatform import addins
from feedplatform import management


class dummy_daemon(base_daemon):
    def __init__(self, output, *a, **kw):
        super(dummy_daemon, self).__init__(*a, **kw)
        self.output = output
    def run(self, *args, **options):
        print self.output


def test_start_cmd():
    """Make sure installing a daemon addin results in a "start" command
    being available, and that command being able to handle multiple
    daemons, named and unnamed, correctly."""

    # TODO: introduce a way to call_command without the shell layer,
    # getting stdout and CommandErrors directly rather than having to
    # go through capturing ourselfs. This could be part of the management
    # module, or the test module.

    def _call_start(addins_to_test, *args, **options):
        addins.reinstall(addins=addins_to_test)
        management.reload_commands()
        old_sys = sys.stdout
        old_err = sys.stderr
        sys.stdout = sys.stderr = StringIO.StringIO()
        try:
            management.call_command('start', *args, **options)
            sys.stdout.seek(0)
            return sys.stdout.read().strip()
        finally:
            sys.stdout = old_sys
            sys.stderr = old_err

    # with no daemons installed, the "start" command is not available
    assert_raises(management.UnknownCommandError, _call_start, [])

    # if there's only one daemon it will be started by default
    assert _call_start([dummy_daemon('1')]) == '1'

    # Even with just one daemon, you may explicitly specify it's name
    # to keep call syntax compatible with multi-daemon scenarios.
    assert _call_start([dummy_daemon('1', name="foo")], "foo") == '1'

    # With two named daemons the command needs to know which one to
    # start, so this will fail.
    assert "multiple daemons" in \
                _call_start([dummy_daemon('1', name="foo"),
                             dummy_daemon('2', name="bar")])

    # This is true even if one of the commands is unnamed. We could
    # ignore the unnamed daemons here and just start the named one,
    # since the others are currently unstartable anyway, but this may
    # not always be so: We want to keep the option open to implement
    # functionality to start unnamed daemons.

    # the daemon specified will be run
    assert _call_start([dummy_daemon('1', name="foo"),
                        dummy_daemon('2', name="bar")], "bar") == '2'

    # if an invalid name is given, an error is raised
    assert "not a known daemon" in \
                _call_start([dummy_daemon('1', name="foo"),
                             dummy_daemon('2', name="bar")], "python-rocks")