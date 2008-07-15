"""Sets up the database, models, connections etc. based on the
user's configuration file.

The Storm ORM is used as the backend.
"""

import sys

from storm.locals import Store, create_database, Storm

from feedplatform.models import AVAILABLE as AVAILABLE_MODELS
from feedplatform.conf import config


# all of those are dynamically constructed during module setup
__all__ = []
database = None
store = None
models = {}


class LazyStore(object):
    """Simple wrapper object for a Storm database store that defers
    actual instantiation until first accessed.
    """

    def __init__(self, database):
        self._database = database
        self._store = None

    def __getattr__(self, name):
        if self._store is None:
            self._init_store()
        return getattr(self._store, name)

    def __setattr__(self, name, value):
        if name in ['_store', '_database']:
            self.__dict__[name] = value
        else:
            if self._store is None:
                self._init_store()
            return setattr(self._store, name)

    def _init_store(self):
        self._store = Store(self._database)

class NoDatabaseErrorProxy(object):
    def __getattr__(self, *args, **kwargs):
        raise ValueError('The database is not configured (see the '
            'DATABASE setting)')
    __setattr__ = __getattr__


# TODO: do we need to take more care to ensure this isn't run more than
# once, and that there are no race conditions?
def reconfigure():
    """Reconfigure database connection and models based on the current
    configuration.
    """

    # setup the database connection and store; note that at this point
    # no connection data is required; it will be checked only when someone
    # first attempts to use the store.
    global database, store
    if config.DATABASE:
        database = create_database(config.DATABASE)
        store = LazyStore(database)
    else:
        database = NoDatabaseErrorProxy()
        store = NoDatabaseErrorProxy()

    # collect fields for all the models
    model_fields = AVAILABLE_MODELS.copy()
    for addin in config.ADDINS:
        for name, new_fields in addin.get_columns():
            if not table in AVAILABLE_MODELS:
                raise ValueError('"%s" is not a valid model name' % table)
            fields[addin].update(new_fields)

    # create the actual model objects
    global models
    for name, fields in model_fields.items():
        model_name = name.capitalize()
        attrs = {'__storm_table__': name}
        attrs.update(fields)
        model = type(model_name, (Storm,), attrs)

        # make available on module level
        setattr(sys.modules[__name__], model_name, model)
        models[model_name] = model

    # update __all__ with all models
    global __all__
    __all__ = tuple([m for m in models.keys()] + ['store', 'database'])

reconfigure()