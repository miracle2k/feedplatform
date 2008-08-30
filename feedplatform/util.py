"""Generally helpful stuff, to be used by library code and addins.
"""

import urllib2
import datetime
import calendar

from feedplatform.conf import config


__all__ = (
    'struct_to_datetime',
    'datetime_to_struct',
)


def struct_to_datetime(structt):
    """Converts timestructs/9-tuples, as returned by feedparser, to
    naive, UTC-based datetime objects.

    See also:
        http://www.deadlybloodyserious.com/2007/09/feedparser-v-django/
        http://www.intertwingly.net/blog/2007/09/02/Dealing-With-Dates
    """
    if not structt:
        return structt
    return datetime.datetime.utcfromtimestamp(calendar.timegm(structt))


def datetime_to_struct(datetime):
    """Converts a datetime object to an UTC-based 9-tuple.

    The reverse of ``struct_to_datetime``.
    """
    if not datetime:
        return datetime
    return datetime.utctimetuple()


def urlopen(*args, **kwargs):
    """
    """
    opener = urllib2.build_opener(*config.URLLIB2_HANDLERS)
    try:
        request = urllib2.Request(*args, **kwargs)
        request.add_header('User-Agent', config.USER_AGENT)
        return opener.open(request)
    finally:
        opener.close()