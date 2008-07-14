"""Sets up the database, models, connections etc. based on the
user's configuration file.

The Storm ORM is used as the backend.
"""

from storm.locals import *

from feedplatform.conf import models
from feedplatform.conf import config

def __init_db():
    pass
    """
    go through addins, build list of columns

    create model/table objects

    setup database connections, store
        (possibly lazy, check database config as late as possible?)
    """

__init_db()