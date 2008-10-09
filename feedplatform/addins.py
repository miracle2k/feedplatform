"""Addins are the primary way of extending FeedPlatform the add
additional aggregator functionality.

You'll find a number of them in the builtin ``feedplatform.lib``
module, although custom addins can easily be created, and
generally, when extended or specialized customization is required,
creating an addin will be a common thing to do.

Addins require an installation process to register their hooks and
other modifiers, so that addins can be loaded and reloaded at any
time. If you change the list of addins at any point afterwards,
use ``reinstall()`` to put it into effect.

It is recommended that addins subclass ``base``, though it is not
required and an addin may in fact be any object that features a
``setup`` method. Addins can also specify a tuple attribute
``depends``, referring to other addin classes that are required
for an addin to function, too. If the user hasn't specified those
addins, they will be added implicitely, so long their constructor
allows parameterless instantiation. Otherwise, an error would be
raised, asking the user to manually add the dependency.
Currently, the ``depends`` tuple may refer to the other addins only
via a class reference.
"""

import types
import inspect
from copy import copy
from feedplatform import hooks
from feedplatform import log
from feedplatform.conf import config


__all__ = ('base', 'install', 'reinstall', 'get_addins')


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

        # register new hook that the addin wants to define
        if hasattr(self, 'get_hooks'):
            new_hooks = self.get_hooks()
            if hooks:
                for name in new_hooks:
                    hooks.register(name)

        # auto-register all hook callbacks ('on_*'-pattern)
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


_ADDINS = None

def get_addins():
    """Return the actual list of currently active addin instances,
    as opposed to config.ADDINS, which is just the original user input.
    """
    global _ADDINS
    if  _ADDINS is None:
        reinstall()
    return _ADDINS


def _make_addin(addin):
    """Normalizes addin's given by the user - makes sure an instance
    is returned.

    If ``addin`` is a class, an instance is created, if possible.
    Otherwise, an error is raised, or ``addin`` is returned unmodified.
    """
    if isinstance(addin, type):
        if not addin.__init__ is object.__init__: # won't work with getargspec
            args, _, _, defaults = inspect.getargspec(addin.__init__)
            # for method types, the first argument will be the
            # self-pointer, which we know will get filled, so we
            # may ignore it.
            if isinstance(addin.__init__, types.MethodType) and args:
                args = args[1:]

            if (not defaults and args) or (defaults and len(args) != len(defaults)):
                raise ValueError('The addin "%s" was given as a class, '
                    'rather than an instance, but requires arguments '
                    'to be constructed.' % addin.__name__)

        addin = addin()
    return addin

def reinstall(addins=None):
    """Install the addins specified by the configuration, or via
    ``addins`.

    The addin installation process consists mainly if letting each
    adding register it's hook callbacks, as well as rebuilding the
    models.

    Addins that were previously installed will automatically be
    removed.

    The function returns the list of addins installed. It may
    differ from the explicitly specified list due to dependencies,
    and will contain only addin instances, not classes.
    """

    if addins is None:
        addins = copy(config.ADDINS)

    # Start by making sure all addins are available as instances,
    # and use a separate list that we may modify going further.
    # Note that by starting with an initial list of all specified
    # addins, dependency order is not enforced for those. E.g. if
    # ``b`` depends on ``a`, but the user puts ``b`` before ``a``,
    # then that will be accepted by this installation process. In
    # contrast, if he only specifies ``b``, the ``a`` dependency
    # would automatically be inserted before it.
    to_be_setup = []
    for addin in addins:
        to_be_setup.append(_make_addin(addin))

    # resolve dependencies
    for i in range(0, len(to_be_setup)):
        def resolve_dependencies(addin, index):
            dependencies = getattr(addin, 'depends', ())
            for dependency in dependencies:
                exists = False
                # Check if the dependency is already installed. Note
                # that dependencies may be both classes and instances.
                for existing in to_be_setup:
                    if not isinstance(dependency, type):
                        if isinstance(existing, type(dependency)):
                            exists = True
                    elif isinstance(existing, dependency):
                        exists = True

                # if not, insert it at the right position, and
                # recursively resolve it's own dependencies.
                if not exists:
                    dependency = _make_addin(dependency)
                    to_be_setup.insert(index, dependency)
                    index = resolve_dependencies(dependency, index)
                    index += 1
            return index

        i = resolve_dependencies(to_be_setup[i], i)

    # finally, setup all the addins we determined to be installed
    hooks.reset()
    for addin in to_be_setup:
        addin.setup()

    global _ADDINS
    _ADDINS = to_be_setup
    return to_be_setup


def install(*args, **kwargs):
    """Like ``reinstall``, but only works the very first time the
    addins need to be installed. If they already are, this is a noop.

    Useful if you need to ensure that addins are active.
    """
    global _ADDINS
    if _ADDINS is None:
        return reinstall(*args, **kwargs)