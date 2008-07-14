"""Manage configuration.

Loads the configuration file as specified by the user through an
environment variable, and merges it with the default config. Makes
the result available for other parts of the library to use.

Also provides validation services.

Inspired by Django configuration file implementation.

Common usage:

    from feedplatform.conf import config
"""

import os, sys
from os import path
from feedplatform.conf import default as default_config


ENVIRONMENT_VARIABLE = "FEEDPLATFORM_CONFIG"


class LazyConfig(object):
    """Loads the configuration on demand on first access, by creating
    a ``Configuration`` instance.
    """

    def __init__(self):
        self._target = None

    def __getattr__(self, name):
        if self._target is None:
            self._import_config()
        return getattr(self._target, name)

    def __setattr__(self, name, value):
        if name == '_target':
            self.__dict__['_target'] = value
        else:
            if self._target is None:
                self._import_config()
            setattr(self._target, name, value)

    def _import_config(self):
        try:
            config = os.environ[ENVIRONMENT_VARIABLE]
            if not config: # set but empty string
                raise KeyError
        except KeyError:
            raise ImportError("No configuration file found, environment "
                "variable %s is undefined." % ENVIRONMENT_VARIABLE)

        self._target = Configuration(config)


class Configuration(object):

    def __init__(self, config):
        # load the config file, either from a file path or
        # dotted python module notation.
        try:
            if ('/' in config or '\\' in config) and (config.endswith('.py')):
                basedir = path.dirname(path.normpath(path.abspath(config)))
                name = path.basename(config)
                sys.path += [basedir]
                try:
                    mod = __import__(name, {}, {}, [''])
                finally:
                    sys.path.remove(basedir)

            else:
                mod = __import__(config, {}, {}, [''])
        except ImportError, e:
            raise ImportError, ("Could not import configuration '%s'. It "
                "might not a valid path, or not a module name available "
                "via sys.path, or contain syntax errors (%s)") % (config, e)

        # initialize self with default settings
        for setting in dir(default_config):
            if setting == setting.upper():
                setattr(self, setting, getattr(default_config, setting))

        # override with user's config
        for setting in dir(mod):
            if setting == setting.upper():
                setattr(self, setting, getattr(mod, setting))


config = LazyConfig()