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


class DatabaseProxy(object):
    """Proxy an object that shall be created on demand, when accessed,
    by the creator function passed to ``__init__``.

    Necessary since some database objects like the Store cannot be
    instantiated without a valid connection.

    Futher, we explicitly fail with an exception if no database
    connection data is available at all.
    """

    def __init__(self, create_func):
        self.__dict__['obj'] = None
        self.__dict__['create_func'] = create_func

    def _connect(self):
        if not self.obj:
            if not config.DATABASE:
                raise ValueError('The database is not configured (see '
                    'the DATABASE setting)')
            self.__dict__['obj'] = self.create_func()

    def __getattr__(self, name):
        self._connect()
        return getattr(self.obj, name)

    def __setattr__(self, name, value):
        self._connect()
        return setattr(self.obj, name, value)


def reconfigure():
    """Reconfigure database connection and models based on the current
    configuration.

    This is only necessary if the database objects already have been
    accessed (since they are created on demand), or if the available
    models have changed.
    """

    # Setup the database connection and store; note that at this point
    # no valid connection data is required; it will be checked only
    # when someone first attempts to use the objects.
    global database, store
    database = DatabaseProxy(lambda: create_database(config.DATABASE))
    store = DatabaseProxy(lambda: Store(database))

    # collect fields for all the models
    model_fields = AVAILABLE_MODELS.copy()
    for addin in config.ADDINS:
        for name, new_fields in addin.get_columns():
            if not table in AVAILABLE_MODELS:
                raise ValueError('"%s" is not a valid model name' % table)
            fields[addin].update(new_fields)

    # "Unregister" current models from storm - otherwise we'll see stuff
    # like "PropertyPathError: Path 'feed_id' matches multiple properties".
    Storm._storm_property_registry.clear()

    # create the actual model objects
    new_models = {}
    for name, fields in model_fields.items():
        model_name = name.capitalize()
        attrs = {'__storm_table__': name}
        attrs.update(fields)
        model = type(model_name, (Storm,), attrs)

        # make available on module level
        setattr(sys.modules[__name__], model_name, model)
        new_models[model_name] = model

    global models
    models = new_models

    # update __all__ with all models
    global __all__
    __all__ = tuple([m for m in models.keys()] + ['store', 'database'])

reconfigure()