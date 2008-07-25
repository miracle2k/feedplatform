DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

ROOT_URLCONF = 'proj.urls'

FEEDPLATFORM_CONFIG = 'proj.feedplatform_config'

INSTALLED_APPS = (
    'feedplatform.integration.django'
)
