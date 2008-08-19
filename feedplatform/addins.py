"""TODO: Addins are the

you'll find a number of them in feedplatform.lib

custom addins can easily be created.

addins require an installation process to register their hooks, this
currently happens whem the config is loaded.

call reinstall() if you changed ADDINS afterwards.

"""

import types
from feedplatform import hooks
from feedplatform import db


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
        addin.setup()

    db.reconfigure()

# at least for now, those are the same
reinstall = install