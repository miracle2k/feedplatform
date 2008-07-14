"""Hook infrastructure.

This is a central part of the library, since it's what allows addins
to modify and extend the feed parsing process.

It is mainly a gateway between the core library functionality that calls
hooks, and addins that register the callbacks.

It is possible for addins to register their own hooks to make available
in turn to other addins.
"""

# simple method to validate names and avoid bugs due to misspellings
SUPPORTED_HOOKS = [
]

# store registered callbacks: dict of lists of callables
_HOOKS = {}

def add_callback(name, func, priority=None):
    pass

def register_hook(name):
    pass