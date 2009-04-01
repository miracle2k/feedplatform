from nose.plugins.skip import SkipTest

import os, sys
import copy
import subprocess
from StringIO import StringIO

from storm.uri import URI
from feedplatform.management import call_command
from feedplatform import conf


def setup_module():
    # if django is not installed, don't bother with these tests
    try:
        import django
    except ImportError:
        raise SkipTest()


def test_django_integration():
    """Check that the output of a manual "call_command" matches what
    we get from executing ./manage.py.
    """

    # 1. get via process
    managepy = os.path.join(os.path.dirname(__file__), 'proj', 'manage.py')
    process = subprocess.Popen([managepy, 'feedplatform', 'models'],
                               stdout=subprocess.PIPE,
                               shell=os.name == 'nt' and True or False,
                               universal_newlines=True)
    stdout, stderr = process.communicate()
    process_output = stdout

    # 2. get via callcommand
    oldconfig = conf.config._target
    try:
        conf.config.reset()
        sys.path.append(os.path.join(os.path.dirname(__file__), 'proj'))
        try:
            os.environ['FEEDPLATFORM_CONFIG'] = 'feedplatform_config'
            real_stdout = sys.stdout
            sys.stdout = StringIO()
            try:
                call_command('models')
                sys.stdout.seek(0)
                command_output = sys.stdout.read()
            finally:
                # set back to real stdout
                sys.stdout = real_stdout
        finally:
            # remove test django project from path
            sys.path.pop()
    finally:
        # reset to previously used config
        conf.config._target = oldconfig

    # 3. check that the two are the same
    print "command: (%s)" % repr(command_output), len(command_output)
    print "process: (%s)" % repr(process_output), len(process_output)
    assert process_output ==  command_output


def test_make_dsn():
    """Test the Django DSN string builder."""

    # Setup django in the current thread; other tests just
    # used it via an external process.
    from django.core.management import setup_environ
    import proj.settings
    setup_environ(proj.settings)
    from feedplatform.integration.django.models import make_dsn

    # Automatically generate a list of all possible variations
    # of missing connection data. Test both with None and ''
    # values.
    base = ['michael', 'xyz123', 'localhost', '3600', 'foo']

    def yield_variants(value, collector, pos=0, blackout=None):
        collector.append(value)
        for i in range(pos, len(value)):
            v = copy.copy(value)
            v[i] = blackout
            yield_variants(v, collector, i+1, blackout)

    variants_to_test = []
    yield_variants(base, variants_to_test, blackout=None)
    yield_variants(base, variants_to_test, blackout='')

    # Check that the decoded version of what we encode matches the
    # original, for all possible variations.
    for user, password, host, port, database in variants_to_test:
        obj = type('FakeSettings', (), {})()
        obj.DATABASE_ENGINE = 'mysql'
        obj.DATABASE_USER = user
        obj.DATABASE_PASSWORD = password
        obj.DATABASE_HOST = host
        obj.DATABASE_PORT = port
        obj.DATABASE_NAME = database
        uri = URI(make_dsn(obj))

        for a, b in zip(
            (uri.username, uri.password, uri.host, uri.port, uri.database),
            (user, password, host, port, database)
        ):
            assert str(a) == str(b) or (a in (None, '') and b in (None, ''))