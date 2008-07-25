"""Manage configuration.

Loads the configuration file as specified by the user through an
environment variable, and merges it with the default config. Makes
the result available for other parts of the library to use.

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
            # we do not enforce a configuration file, although certain
            # settings, like the database connection, will be required
            # at some point.
            config = None

        self._target = Configuration(config)

    def configure(self, **options):
        """Manually setup the configuration.

        This makes setting up a config dynamically much easier, since
        you don't have to create a dummy module.

        If a config is already set up, the options you specifiy will
        simply be applied (i.e. added, or existing values overwritten).
        """
        if not self.configured:
            self._target = Configuration()
        for name, value in options.items():
            setattr(self._target, name, value)

    def reset(self):
        """Reset a currently loaded configuration. On next access, a
        new configuration file will be loaded based your current
        environment.

        This allows switching to a different configuration file.

        Note that when you set the environement variable after having
        already accessed the configuration, your custom config file will
        not be loaded. This is where a reset will help.
        """
        self._target = None

    @property
    def configured(self):
        return self._target is not None


class Configuration(object):

    def __init__(self, config=None):
        # initialize self with default settings
        for setting in dir(default_config):
            if setting == setting.upper():
                setattr(self, setting, getattr(default_config, setting))

        # if no config file was provided, skip the rest
        if config is None:
            return

        # load the config file, either from a file path or
        # dotted python module notation.
        try:
            if ('/' in config or '\\' in config) and (config.endswith('.py')):
                basedir = path.dirname(path.normpath(path.abspath(config)))
                name = path.basename(config)
                sys.path += [basedir]
                try:
                    mod = __import__(name[:-3], {}, {}, [''])
                finally:
                    sys.path.remove(basedir)

            else:
                mod = __import__(config, {}, {}, [''])
        except ImportError, e:
            raise ImportError, ("Could not import configuration '%s'. It "
                "might not a valid path, or not a module name available "
                "via sys.path, or contain syntax errors (%s)") % (config, e)

        # override with user's config
        for setting in dir(mod):
            if setting == setting.upper():
                setattr(self, setting, getattr(mod, setting))


config = LazyConfig()