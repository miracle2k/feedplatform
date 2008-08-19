DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.

MEDIA_ROOT = ''
MEDIA_URL = ''

#ADMIN_MEDIA_PREFIX = '/media/'

ROOT_URLCONF = 'aggregator.urls'

FEEDPLATFORM_CONFIG = 'aggregator.feedplatform_config'

INSTALLED_APPS = (
    #'django.contrib.auth',
    #'django.contrib.sessions',
    'django.contrib.contenttypes',
    'feedplatform.integration.django',
    'aggregator',
)
