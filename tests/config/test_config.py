"""Test configuration handling/loading.
"""

import os
from feedplatform import conf
from feedplatform.conf import default as default_config

def setup_module(module):
    # This is though to test since the testing process has likely already
    # setup a configuration, db connection etc. We try to remember it, and
    # reset state on module teardown.
    module.old_config = conf.config._target
    conf.config.reset()
    from feedplatform import db
    db.reconfigure()

def teardown_module(module):
    conf.config._target = module.old_config
    from feedplatform import db
    db.reconfigure()

def test_imports_without_a_config():
    from feedplatform import db
    # those are accessible
    db.store
    db.database

def test_manual_configure():
    conf.config.reset()

    conf.config.configure(FOO='bar')
    assert conf.config.FOO == 'bar'

def test_load_via_pythonpath():
    conf.config.reset()
    os.environ['FEEDPLATFORM_CONFIG'] = 'tests.config.pypath_example.dummy_config'

    # custom value - checks we loaded the right config
    assert conf.config.LOADED == 'pythonpath'

    # test one overwritten option, and one that remained unchanged
    assert conf.config.USER_AGENT == 'testsuite'
    assert conf.config.ENFORCE_URI_SCHEME == default_config.ENFORCE_URI_SCHEME

def test_load_via_filesystem():
    conf.config.reset()
    os.environ['FEEDPLATFORM_CONFIG'] = \
         os.path.join(os.path.dirname(__file__), 'filesystem_example', 'dummy_config.py')

    # custom value - checks we loaded the right config
    assert conf.config.LOADED == 'filesystem'

    # test one overwritten option, and one that remained unchanged
    assert conf.config.USER_AGENT == 'testsuite'
    assert conf.config.ENFORCE_URI_SCHEME == default_config.ENFORCE_URI_SCHEME