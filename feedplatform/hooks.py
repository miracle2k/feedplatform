"""Hook infrastructure.

This is a central part of the library, since it's what allows addins
to modify and extend the feed parsing process.

It is mainly a gateway between the core library functionality that calls
hooks, and addins that register the callbacks.

It is possible for addins to register their own hooks to make available
in turn to other addins.

# TODO: the list of hooks needs to be updated with more info.
"""

import copy


__all__  = (
    'SUPPORTED_HOOKS',
    'reset',
    'add_callback',
    'any',
    'trigger',
    'register',
    'exists',
)


_DEFAULT_HOOKS = [
    # Called before a feed is downloaded and
    # parsed. Gets passed the feed db object
    # and a parser argument dict. Can return
    # True if further processing should be
    # stopped. Can modify the feedparser
    # arguments.
    'before_parse',

    # Called after a feed was successfully
    # retrieved and parsed, though note that it
    # still may be bozo. Gets passed the feed
    # db object, as well as the parsed data dict.
    # Can return True if further processing
    # should be stopped.
    # To collect feed-wide data, this is the
    # right place. TODO: or is this better
    # done in a separate hook (say 'feed',
    # 'handle_feed'/'while_feed'/'do_feed', 'process_feed'?
    # depends on how error handling is going to work.
    'after_parse',

    # The first thing that runs for every entry in
    # a feed; can return True to stop processing
    # of this entry.
    'item',

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

    # A new item was found in a feed, and now
    # needs to be initialized. This allows to
    # customize instantiation of the Item model,
    # e.g. by using a subclass.
    # Note that you are fully responsible of
    # initializing the instance, e.g. hooking
    # it up to the parent feed, and setting
    # the guid.
    'create_item',

    # Follows 'create_item' after a new item was
    # found in a feed, but the Item instance is
    # created already (though not yet flushed).
    # See also found_item, which is usually
    # combined with this to update item metadata.
    'new_item',

    # Basically the opposing hook to new_item.
    # This gets called if an item in a feed was
    # detected to be already in the database.
    # Usually combined with new_item to update
    # item metadata.
    'found_item',

    # Called when an item is processed, both for
    # new and existing items. The ``created``
    # argument let's you distinguish.
    # Note the difference between this an
    # new_item/found_item, and the reason the latter
    # two exist: in new_item, the item does not yet
    # have a primary key, but it does here. If
    # you need a primary key, for example for
    # associating information in a separate model,
    # and put your code into new_item instead, you
    # would cause an implicit flush() for the item,
    # which in combination with other addins following
    # that change the instance too could lead two two
    # flushes()/two queries, instead of only one:
    #       unflushed item
    #       process_item hook causes implicit flush() -> query!
    #       process_item hook changes item
    #       default flush() on changed item           -> query!
    # XXX: Test this situation.
    #
    # The lowdown: If you don't need a primary key,
    # hook into new_item/found_item instead.
    'process_item',

    # Dummy test hook. Never actually called,
    # provides no useful functionality. Ignore.
    'alien_invasion',
]

# simple method to validate names and avoid bugs due to misspellings
SUPPORTED_HOOKS = None

# store registered callbacks: dict of (callable => priority) dicts
_CALLBACKS = None


def reset():
    """Remove all registered callbacks and custom hooks.
    """
    global _CALLBACKS, SUPPORTED_HOOKS
    _CALLBACKS = {}
    SUPPORTED_HOOKS = copy.copy(_DEFAULT_HOOKS)


def add_callback(name, func, priority=0):
    """Register a hook callback.

    Raises exceptions if the hook name is invalid, or the function
    is already registered.
    """

    _validate_hook_name(name)

    if not name in _CALLBACKS:
        _CALLBACKS[name] = {}

    if func in _CALLBACKS[name]:
        raise ValueError('The callback (%s) is already registered' % func)

    _CALLBACKS[name][func] = priority
    _CALLBACKS[name] = dict(sorted(_CALLBACKS[name].iteritems(),
                                   key=lambda (k,v): v,
                                   reverse=True))


def any(name):
    """Returns True if at least one callback has been registered for
    ``name``, otherwise ``False``.

    Can be used if triggering a hook requires preparation work that
    you want to avoid unless necessary.
    """
    _validate_hook_name(name)
    return len(_CALLBACKS.get(name, {})) > 0


def trigger(name, args=[], kwargs={}, all=False):
    """Run call the callbacks registered by the hook with the given
    arguments.

    By the default, once any of the callbacks returns a non-None
    value, further processing will stop. Set ``all`` to True to
    ensure that all callbacks will run.
    """

    _validate_hook_name(name)

    for func, priority in _CALLBACKS.get(name, {}).iteritems():
        result = func(*args, **kwargs)
        if result is not None and not all:
            return result


def _validate_hook_name(name):
    if not name in SUPPORTED_HOOKS:
        raise KeyError('No hook named "%s"' % name)


def register(name):
    """Register a new hook name.

    This will simply mark that particular name as available.
    """
    global SUPPORTED_HOOKS
    if not name in SUPPORTED_HOOKS:
        SUPPORTED_HOOKS.append(name)


def exists(name):
    """Return True if a hook name is valid, False otherwise.
    """
    global SUPPORTED_HOOKS
    return name in SUPPORTED_HOOKS


# initialize the module
reset()