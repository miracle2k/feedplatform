"""Hook infrastructure.

This is a central part of the library, since it's what allows addins
to modify and extend the feed parsing process.

It is mainly a gateway between the core library functionality that calls
hooks, and addins that register the callbacks.

It is possible for addins to register their own hooks to make available
in turn to other addins.
"""


__all__  = (
    'SUPPORTED_HOOKS',
    'reset',
    'add_callback',
    'trigger',
)


# simple method to validate names and avoid bugs due to misspellings
SUPPORTED_HOOKS = [
    # Determine item guid BEFORE the default
    # <guid> tag is chosen.
    'get_guid',

    # Determine item guid AFTER <guid> was
    # found missing missing - provided that
    # ``get_guid`` did not return a match.
    'need_guid',

    # No guid was found by any of the addins.
    # At this point, it is already determined
    # that the item will be skipped, but you
    # may add further handling beyond that.
    'no_guid',

    # Try to find an existing item for the
    # guid determined. This runs BEFORE the
    # default attempt to find the item.
    'get_item',

    # Try to find an item for the guid after
    # both ``get_item`` and the default code
    # failed.
    'need_item',
]


# store registered callbacks: dict of (callable => priority) dicts
_HOOKS = {}


def reset():
    """Remove all registered callbacks.
    """
    global _HOOKS
    _HOOKS = {}


def add_callback(name, func, priority=0):
    """Register a hook callback.

    Raises exceptions if the hook name is invalid, or the function
    is already registered.
    """

    _validate_hook_name(name)

    if not name in _HOOKS:
        _HOOKS[name] = {}

    if func in _HOOKS[name]:
        raise ValueError('The callback (%s) is already registered' % func)

    _HOOKS[name][func] = priority
    _HOOKS[name] = dict(sorted(_HOOKS[name].iteritems(),
                               key=lambda (k,v): v,
                               reverse=True))


def trigger(name, args=[], kwargs={}, all=False):
    """Run call the callbacks registered by the hook with the given
    arguments.

    By the default, once any of the callbacks returns a True value,
    further processing will stop. Set ``all`` to True to ensure that
    all callbacks will run.
    """

    _validate_hook_name(name)

    for func, priority in _HOOKS.get(name, {}).iteritems():
        result = func(*args, **kwargs)
        if result and not all:
            return result


def _validate_hook_name(name):
    if not name in SUPPORTED_HOOKS:
        raise KeyError('No hook named "%s"' % name)