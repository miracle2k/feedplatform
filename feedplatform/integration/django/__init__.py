import os
from django.conf import settings
from feedplatform.conf import ENVIRONMENT_VARIABLE

from models import make_dsn

__all__ = ('make_dsn',)


config = getattr(settings, 'FEEDPLATFORM_CONFIG', None)
if not config:
    raise Exception('The FeedPlatform integration app requires the '
        '"FEEDPLATFORM_CONFIG" option to be set in your Django '
        'settings module.')
else:
    os.environ[ENVIRONMENT_VARIABLE] = config