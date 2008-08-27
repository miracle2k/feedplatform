"""Addins are the primary way of extending FeedPlatform the add
additional aggregator functionality.

You'll find a number of them in the builtin ``feedplatform.lib``
module, although custom addins can easily be created, and
generally, when extended or specialized customization is required,
creating an addin will be a common thing to do.

Addins require an installation process to register their hooks and
other modifiers, so that addins can be loaded and reloaded at any
time - currently this process happens when the configuration file is
loaded. If you change the list of addins at any point afterwards,
use ``reinstall()`` to put it into effect.

It is recommended that addins subclass ``base``, though it is not
required and an addin may in fact be any object that features a
``setup`` method. Addins can also specify a tuple attribute
``depends``, referring to other addin classes that are required
for an addin to function, too. If the user hasn't specified those
addins, they will be added implicitely, so long their constructor
allows parameterless instantiation. Otherwise, an error would be
raised, asking the user to manually add the dependency.
Currentl, the ``depends`` tuple may refer to the other addins only
via a class reference.
"""

import types
import inspect
from feedplatform import hooks
from feedplatform import db
from feedplatform import log


__all__ = ('base', 'install', 'reinstall')


class base(object):
    """Common base class for addins.

    It's use is optional, addins are not required to use it. However,
    doing so will provide certain helpers:

        * Instead of manually registering your hook callbacks, you can
          simply write them as methods, using the hook name prefixed
          with 'on_*' - e.g. 'on_get_guid'.
          An exception will be raised if the name after 'on_' does not
          refer to a valid hook.

        * self.log provides a namespaced Python logging facility.
    """

    def setup(self):
        """Called to have the addin register it's hook callbacks.

        This is also the place for related setup jobs like setting up
        custom models.

        If an addin does not subclass ``addins.base``, it must provide
        this method itself.
        """

        # auto-register all hooks ('on_*'-pattern)
        for name in dir(self):
            if name.startswith('on_'):
                attr = getattr(self, name)
                if isinstance(attr, types.MethodType):
                    try:
                        hooks.add_callback(name[3:], attr)
                    except KeyError, e:
                        raise RuntimeError(('%s: failed to initialize '
                            'because %s method does not refer to a valid '
                            'hook (%s).') % (self.__class__, name, e))

    @property
    def log(self):
        """Provide a logger namespace for each addin, accessible
        via ``self.log``.

        This is lazy, e.g. the logger is created only when accessed.
        """
        if not hasattr(self, '_log'):
            self._log = log.get('lib.%s' % self.__class__.__name__)
        return self._log


def install(addins=None):
    """Install the addins specified by the configuration, or via
    ``addins`.

    The addin installation process consists mainly if letting each
    adding register it's hook callbacks, as well as rebuilding the
    models.

    Addins that were previously installed will automatically be
    removed.
    """

    # Don't clutter global namespace; we can't use __all__ here;
    # also, config would likely lead to recursive imports.
    from feedplatform.conf import config
    from feedplatform import hooks

    if addins is None:
        addins = config.ADDINS

    hooks.reset()
    for addin in addins:
        if isinstance(addin, type):
            # a class name was specified, check that we can
            # auto-create an instance.
            if not addin.__init__ is object.__init__: # won't work with getargspec
                args, _, _, defaults = inspect.getargspec(addin.__init__)
                if (not defaults and args) or (len(args) != len(defaults)):
                    raise ValueError('The addin "%s" was given as a class, '
                        'rather than an instance, but requires arguments '
                        'to be constructed.' % addin.__name__)

            addin = addin()
        addin.setup()

    db.reconfigure()

# at least for now, those are the same
reinstall = install