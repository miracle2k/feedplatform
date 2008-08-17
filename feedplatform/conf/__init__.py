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
        self._target._apply()

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
        self._target._apply()

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

    def _apply(self):
        """Apply configuration options that cannot be resolved on demand
        to the environment.

        Right now, this means mostly ADDINS.

        Due to the way addins have to register their callbacks with the
        hook registry (e.g. they need to be installed), we need to let
        them do just that at some point.

        Not sure if this is the right place (it introduces a dependency
        from the config to other code, this was previously not the case),
        but it seems like the most practical.
        Other options would include:

            * Addins shouldn't do it on instantiation, since that would
              invalidate the whole ADDINS config option. Only what is
              listed there should be used.

            * There are multiple entry points that rely on addins being
              installed, including multiple inside the parsing code as
              well. We don't want each of those having to take care of
              ensuring addin installation themselves. Also, there is no
              good way currently to check whether that installation has
              already happened.

            * Moving it to the module import level of modules that
              contain those entry points isn't that great either - now
              the user might have to make sure he has is imports in the
              right order, e.g. first import config, setup the config,
              only then import then rest.

        Therefore, right now the addins are installed the first time the
        configuration is actually loaded (remember: it's lazy loaded).

        """
        from feedplatform import addins
        addins.install()


config = LazyConfig()