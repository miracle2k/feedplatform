"""Manage configuration.

Loads the configuration file as specified by the user through an
environment variable, and merges it with the default config. Makes
the result available for other parts of the library to use.

To access a user's configuration, you would commonly do:

    from feedplatform.conf import config
    print config.SOME_OPTION

Inspired by Django's configuration file implementation. However,
unlike Django, FeedPlatform does only require certain configuration
values instead of requiring a configuration. In other words, you
can get away without setting up a configuration as long as you don't
try to use functionality that uses values without a default (e.g.
DATABASE). In contract, Django needs a config file whenever you use
functionality that requires access to the configuration, even if a
default would exist.

Attention: The fact that a config file usually imports
``feedplatform.lib``, which in turn is free to use the whole of the
feedplatform package, introduces some circular issues when code in
the feedplatform package itself needs to refer to the config file.

For example, say that some addin needs to access the services of
``feedplatform.foo``, and ``feedplatform.foo`` needs to access config
data to provide those services. An import stack now might look
like this:

    -> feedplatform.conf.config.SOME_VALUE is accessed
    {user_config_file}    # lazy loaded for the first time
    feedplatform.lib
    feedplatform.lib.troublesome_addin
    feedplatform.foo
    -> accesses feedplatform.conf.config.ANOTHER_VALUE
    {user_config_file} -> ERROR (circular import)

In essence, there is only one solution: While being imported,
``feedplatform.foo`` may in turn import ``feedplatform.conf.config``,
but cannot use the object (i.e. access any configuration values).
The respective code should be placed inside a function, or must be
wrapped inside a proxy. For an example, see how ``feedplatform.db``
exposes the models it creates based on the config.
"""

import os, sys
from os import path
from feedplatform.conf import default as default_config


ENVIRONMENT_VARIABLE = "FEEDPLATFORM_CONFIG"


class LazyConfig(object):
    """Loads the configuration on demand on first access, by creating
    a ``Configuration`` instance.

    The latter holds the actual configuration.
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
        # TODO: The above is potentially the wrong thing to do; we should
        maybe create a whole new config based on the defaults, with just
        the requested changes, discarding the current config.
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
                "might not be a valid path, or not a module available via "
                "sys.path, or contain syntax errors (%s)") % (config, e)

        # override with user's config
        for setting in dir(mod):
            if setting == setting.upper():
                setattr(self, setting, getattr(mod, setting))


config = LazyConfig()