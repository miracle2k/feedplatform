"""Very simple model registry.

Simply stores and makes available a list of model names that are valid,
as well as those model's base fields (e.g. not added by addins).

Apart from it's role in model construction, it is mainly intended as
a simple way to validate identifiers in places where model names are
expected, while at the same time allowing addins to easily register
new models:

    from feedplatform import models
    models.AVAILABLE += ['enclosures']
"""

from storm.locals import *

AVAILABLE = {
    'feed': {
        'id': Int(primary=True),
        'url': Unicode(),
    },
    'item': {
        'id': Int(primary=True),
        'feed_id': Int(),
        'feed': Reference('feed_id', 'Feed.id'),
        'guid': Unicode(),
    },
}