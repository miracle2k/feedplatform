from os import path

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = path.join(path.dirname(__file__), 'data.db')             

MEDIA_ROOT = ''
MEDIA_URL = ''

ROOT_URLCONF = 'aggregator.urls'

FEEDPLATFORM_CONFIG = 'aggregator.feedplatform_config'

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'feedplatform.integration.django',
    'aggregator',
)
