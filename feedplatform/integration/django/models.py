from django.conf import settings as django_settings


def make_dsn(settings=django_settings):
    """Returns a database connection string suitable for use with
    FeedPlatform, based on the database configuration of the current
    Django project.

    Alternatively, an explit ``settings`` object/module may be
    specified.
    """

    try:
        dsn = {
            'mysql': 'mysql',
            'postgresql': 'postgres',
            'postgresql_psycopg2': 'postgres',
            'sqlite3': 'sqlite',
        }[settings.DATABASE_ENGINE]
    except:
        dsn = settings.DATABASE_ENGINE
    dsn += '://'

    if settings.DATABASE_USER:
        dsn += settings.DATABASE_USER
    dsn += ':'

    if settings.DATABASE_PASSWORD:
        dsn += settings.DATABASE_PASSWORD
    dsn += '@'

    if settings.DATABASE_HOST:
        dsn += settings.DATABASE_HOST
    dsn += ':'

    if settings.DATABASE_PORT:
        dsn += '%s' % settings.DATABASE_PORT

    if settings.DATABASE_NAME:
        dsn += '/' + settings.DATABASE_NAME

    return dsn