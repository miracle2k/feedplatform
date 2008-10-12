from django.conf import settings


def make_dsn():
    """Returns a database connection string suitable for use with
    FeedPlatform, based on the database configuration of the Django
    project.

    # XXX: add tests for this
    """

    try:
        dsn = {
            'mysql': 'mysql',
            'postgresql': 'postgres',
            'postgresql_psycopg2': 'postgres',
            'sqlite3': 'sqlite',
        }[settings.DATABASE_ENGINE]
    except:
        raise ValueError('database engine "%s" not supported' %
                            settings.DATABASE_ENGINE)
    dsn += '://'

    if settings.DATABASE_USER:
        dsn += settings.DATABASE_USER

        if settings.DATABASE_PASSWORD:
            dsn += ':' + settings.DATABASE_PASSWORD

    if settings.DATABASE_HOST:
        if settings.DATABASE_USER or settings.DATABASE_PASSWORD:
            dsn += '@'
        dsn += settings.DATABASE_HOST

        if settings.DATABASE_PORT:
            dsn += ':%s' % DATABASE_PORT

    if settings.DATABASE_NAME:
        if settings.DATABASE_HOST or settings.DATABASE_PORT:
            dsn += '/'
        dsn += settings.DATABASE_NAME

    return dsn