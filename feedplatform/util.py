"""Generally helpful stuff, to be used by library code and addins.
"""

import urllib2
import datetime
import calendar

from feedplatform.conf import config


__all__ = (
    'struct_to_datetime',
    'datetime_to_struct',
    'to_unicode',
    'urlopen', 'UrlOpenError',
)


def struct_to_datetime(structt):
    """Convert timestructs/9-tuples, as returned by feedparser, to
    naive, UTC-based datetime objects.

    See also:
        http://www.deadlybloodyserious.com/2007/09/feedparser-v-django/
        http://www.intertwingly.net/blog/2007/09/02/Dealing-With-Dates
    """
    if not structt:
        return structt
    return datetime.datetime.utcfromtimestamp(calendar.timegm(structt))


def datetime_to_struct(datetime):
    """Convert a datetime object to an UTC-based 9-tuple.

    The reverse of ``struct_to_datetime``.
    """
    if not datetime:
        return datetime
    return datetime.utctimetuple()


def to_unicode(s):
    """Convert ``s`` to a unicode object if not None.

    This is helpful in scenarios where you want to assign to a nullable
    Storm ``Unicode`` column (Storm enforces a unicode string type),
    without checking the source for a ``None`` value manually.
    """

    if s is None or isinstance(s, unicode):
        return s
    else:
        return unicode(s)


class UrlOpenError(Exception):
    pass

def urlopen(*args, **kwargs):
    """Wrapper around ``urllib2.urlopen`` that uses the handlers and user
    agent string defined in the feedplatform configuration.

    This should be used whenever network access is required as part of the
    aggregator functionality.

    It also normalizes exception handling, which is slightly challenging,
    and reraises ``UrlOpenError``s for exceptions that you likely want to
    handle was potentially expected.
    """
    opener = urllib2.build_opener(*config.URLLIB2_HANDLERS)
    try:
        request = urllib2.Request(*args, **kwargs)
        request.add_header('User-Agent', config.USER_AGENT)
        try:
            return opener.open(request)
        except Exception, e:
            # At least five different exceptions may occur here:
            #    - urllib2.URLError
            #    - httplib.HTTPException, e.g. "nun-numeric port"
            #    - IOError, e.g. "[Errno ftp error] 530 Login incorrect"
            #    - WindowsError, e.g. when opening from filesystem
            #    - ValueError, e.g. "unknown url type"
            # There are likely more. Instead of listing them explicitely,
            # we simple allow ourselves to capture everything.
            raise UrlOpenError("%s" % e)
    finally:
        opener.close()