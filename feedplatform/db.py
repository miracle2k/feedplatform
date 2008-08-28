"""Sets up the database, models, connections etc. based on the
user's configuration file.

The Storm ORM is used as the backend.
"""

import sys
import copy

from storm.locals import *
from storm.store import ResultSet as StormResultSet

from feedplatform.conf import config


__all__ = ('store', 'database', 'models',
           'MultipleObjectsReturned', 'get_one')


class MultipleObjectsReturned(Exception):
    pass

def get_one(result):
    """Expect exactly one or zero row in ``result`` and return it,
    fail on multiple rows.

    Storm appears to be lacking a ``get()`` method that retrieves
    an object and enforces exactly one result, as known from the
    Django ORM.

    This helper method intends to implement this behaviour. The
    main difference is that we do not raise an exception if no
    results are available, but instead return None.

    ``result`` should be a list, a Storm resultset, or a single
    object.

    # TODO: needs testing
    """
    if isinstance(result, StormResultSet):
        result = list(result)
    if isinstance(result, list):
        if len(result) >= 2:
           raise MultipleObjectsReturned()
        elif result:
           return result[0]
        else:
            return None
    else:
        return result


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


# Note how all columns are given as a tuple to be generated dynamically.
# For some types like ``Reference`` this is quite important, since the
# instance itself hooks up with the models it is used with - links that
# would survive model re-generation, and lead to quite cryptic errors.
BASE_MODELS = {
    'feed': {
        'id': (Int, (), {'primary': True}),
        'url': (Unicode, (), {}),
        'items': (ReferenceSet, ('Feed.id', 'Item.feed_id',), {}),
    },
    'item': {
        'id': (Int, (), {'primary': True}),
        'feed_id': (Int, (), {}),
        'feed': (Reference, ('feed_id', 'Feed.id',), {}),
        'guid': (Unicode, (), {}),
    },
}


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
        # TODO: a simple dict baseclass would do to? from db.models
        # import Feed doesn't work anyway, which was the original idea
        # behind subclassing ModuleType.
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

    def iternames(self):
        self._construct_models()
        return self._models.iterkeys()

    def iteritems(self):
        self._construct_models()
        return self._models.iteritems()

    def _construct_models(self):
        # only do this once
        if '_models' in self.__dict__:
            return

        # collect fields for all the models
        blueprints = copy.deepcopy(BASE_MODELS)
        from feedplatform import addins
        for addin in addins.get_addins():
            if hasattr(addin, 'get_columns'):
                for table, new_fields in addin.get_columns().items():
                    if not table in blueprints:
                        blueprints[table] = {}
                    blueprints[table].update(new_fields)

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