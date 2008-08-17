"""Sets up the database, models, connections etc. based on the
user's configuration file.

The Storm ORM is used as the backend.
"""

import sys

from storm.locals import Store, create_database, Storm

from feedplatform.models import AVAILABLE as AVAILABLE_MODELS
from feedplatform.conf import config


__all__ = ('store', 'database', 'models')


# dynamically constructed during module setup
database = None
store = None
models = None


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


import types

class ModelsProxy(types.ModuleType):
    """Proxy object that constructs the model objects the first time it
    is accessed.

    This is required since we need access to the configuration to do
    this (namely, the list of addins), but are not allowed to do so
    during module initialization (see the docs in ``feedplatform.conf``
    for more information on why this is the case).
    """

    def __init__(self):
        # TODO: a simple dict would do to? from db.models import Feed
        # doesn't work anyway...
        super(ModelsProxy, self).__init__('models')

    def __getattr__(self, name):
        self._construct_models()
        try:
            return self._models[name]
        except KeyError:
            raise AttributeError(name)

    def __iter__(self):
        self._construct_models()
        return self._models.itervalues()

    def _construct_models(self):
        # only do this once
        if '_models' in self.__dict__:
            return

        # collect fields for all the models
        blueprints = AVAILABLE_MODELS.copy()
        for addin in config.ADDINS:
            # TODO: this is not working right yet
            if hasattr(addin, 'get_columns'):
                for name, new_fields in addin.get_columns():
                    if not table in AVAILABLE_MODELS:
                        raise ValueError('"%s" is not a valid model name' % table)
                    blueprints[addin].update(new_fields)

        # "Unregister" current models from storm - otherwise we'll see stuff
        # like "PropertyPathError: Path 'feed_id' matches multiple properties".
        Storm._storm_property_registry.clear()

        # create the actual model objects
        new_models = {}
        for name, fields in blueprints.items():
            model_name = name.capitalize()
            attrs = {'__storm_table__': name}
            for field_name, field_value in fields.items():
                if isinstance(field_value, tuple):
                    klass, args, kwargs = field_value
                    field_value = klass(*args, **kwargs)
                attrs[field_name] = field_value

            model = type(model_name, (Storm,), attrs)

            # make available on module level
            new_models[model_name] = model
        self._models = new_models


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

    # Setup a proxy to the models. We can't build them directly, since
    # we are not allowed to access the config at this point.
    global models
    models = ModelsProxy()

reconfigure()