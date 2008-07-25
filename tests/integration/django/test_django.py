import os, sys
import subprocess
from StringIO import StringIO

from feedplatform.management import call_command
from feedplatform import conf

def test_django_integration():
    """Check that the output of a manual "call_command" matches what we
    get from executing ./manage.py.
    """

    # if django is not installed, don't bother with this test
    try:
        import django
    except ImportError:
        return

    # 1. get via process
    managepy = os.path.join(os.path.dirname(__file__), 'proj', 'manage.py')
    process = subprocess.Popen([managepy, 'feedplatform', 'models'],
                               stdout=subprocess.PIPE, shell=True,
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