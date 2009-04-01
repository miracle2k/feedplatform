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
    we get from executing through a Django project.
    """

    def _capture_with_fake_syspath(path, call, *args, **kwargs):
        sys.path.append(path)
        try:
            real_stdout = sys.stdout
            sys.stdout = StringIO()
            try:
                call(*args, **kwargs)
                sys.stdout.seek(0)
                return sys.stdout.read()
            finally:
                sys.stdout = real_stdout
        finally:
            sys.path.pop()

    # 1. get through Django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'proj.settings'
    from django.core.management import call_command as dj_call_command
    django_output = _capture_with_fake_syspath(
                          os.path.join(os.path.dirname(__file__)),
                          dj_call_command, 'feedplatform', 'models')

    # 2. get via own callcommand
    oldconfig = conf.config._target
    try:
        conf.config.reset()
        os.environ['FEEDPLATFORM_CONFIG'] = 'feedplatform_config'
        local_output = _capture_with_fake_syspath(
                            os.path.join(os.path.dirname(__file__), 'proj'),
                            call_command, 'models')
    finally:
        # reset to previously used config
        conf.config._target = oldconfig

    # 3. check that the two are the same
    print "command: (%s)" % repr(django_output), len(django_output)
    print "process: (%s)" % repr(local_output), len(local_output)
    assert django_output == local_output


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