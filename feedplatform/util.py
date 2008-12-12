"""Generally helpful stuff, to be used by library code and addins.
"""

import socket
import urllib, urllib2
import urlparse
import datetime
import calendar

from feedplatform.conf import config


__all__ = (
    'struct_to_datetime',
    'datetime_to_struct',
    'to_unicode',
    'asciify_url',
    'urlopen', 'UrlOpenError',
    'with_socket_timeout',
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


def asciify_url(url, force_quote=False):
    r"""Attempts to make a unicode url usuable with ``urllib/urllib2``.

    More specifically, it attempts to convert the unicode object ``url``,
    which is meant to represent a IRI, to an unicode object that,
    containing only ASCII characters, is a valid URI. This involves:

        * IDNA/Puny-encoding the domain name.
        * UTF8-quoting the path and querystring parts.

    See also RFC 3987.

    By default, tries to avoid double-quoting.

    If ``url`` is found not to be a valid URI, the string is returned
    unchanged, allowing you to generically use this function in
    conjunction with urlopen(), even if you may want to open non-urls
    (e.g. a filesystem path) as well.

    Another implementation can be found here:
        http://code.google.com/p/httplib2/source/browse/trunk/httplib2/iri2uri.py
    It fails if username/password are used and does not avoid
    double-quoting, but has it's own quote function built after the
    spec. It also handles parts of urls, but in exchange ONLY urls
    (i.e. no filenames).

    TODO: One option would be to always quote and use a separate
    conditional "unquote" function to deal with potentially already
    quoted urls.

    TODO: The RFC mentions unicode normalization (page 9) - this
    is currently ignored.

    Normal URIs are not changed
    >>> asciify_url(u'http://www.elsdoerfer.de/')
    u'http://www.elsdoerfer.de/'
    >>> asciify_url(u'news:comp.infosystems.www.servers.unix')
    u'news:comp.infosystems.www.servers.unix'
    >>> asciify_url(u'tel:+1-816-555-1212')
    u'tel:+1-816-555-1212'
    >>> asciify_url(u'ldap://[2001:db8::7]/c=GB?objectClass?one')
    u'ldap://[2001:db8::7]/c=GB?objectClass?one'

    Domain is IDNA encoded
    >>> asciify_url(u'http://www.elsd\xf6rfer.de/')
    u'http://www.xn--elsdrfer-q4a.de/'

    Other elements are quoted
    >>> asciify_url(u'http://domain.de/\xe4')
    u'http://domain.de/%C3%A4'
    >>> asciify_url(u'http://domain.de/\xe4?m=\xf6')
    u'http://domain.de/%C3%A4?m=%C3%B6'
    >>> asciify_url(u'http://r\xfcdiger:pass@elsd\xf6rfer.de/')
    u'http://r%C3%BCdiger:pass@xn--elsdrfer-q4a.de/'

    Elements that are already quoted are ignored, unless forced; the
    domain name handling is unaffected by this. This is done
    individually for each part.
    >>> asciify_url(u'http://\xe4@elsdörfer.de/a%BCd/')
    u'http://%C3%A4@xn--elsdrfer-9na36b.de/a%BCd/'
    >>> asciify_url(u'http://\xe4@elsdörfer.de/a%BCd/', force_quote=True)
    u'http://%C3%A4@xn--elsdrfer-9na36b.de/a%25BCd/'

    Port
    >>> asciify_url(u'http://elsd\xf6rfer.de:9000/')
    u'http://xn--elsdrfer-q4a.de:9000/'

    Non-URLs are not touched
    >>> asciify_url(u'asdf')
    u'asdf'
    >>> asciify_url(u'\\\\DROKNARS-FORGE\\Public Documents\\Readme.txt')
    u'\\\\DROKNARS-FORGE\\Public Documents\\Readme.txt'
    >>> asciify_url(u'C:\\Windows\\system32')
    u'C:\\Windows\\system32'
    >>> asciify_url(u'/lib/local/python2.5')
    u'/lib/local/python2.5'
    >>> asciify_url(u'path?x=1#bcd')
    u'path?x=1#bcd'
    """
    assert type(url) == unicode

    parts = urlparse.urlsplit(url)
    if not parts.scheme or not parts.netloc:
        # apparently not an url
        return url

    # idna-encode domain
    hostname = parts.hostname.encode('idna')

    # UTF8-quote the other parts. We check each part individually if
    # if needs to be quoted - that should catch some additional user
    # errors, say for example an umlaut in the username even though
    # the path *is* already quoted.
    def quote(s, safe):
        s = s or ''
        # Triggers on non-ascii characters - another option would be:
        #     urllib.quote(s.replace('%', '')) != s.replace('%', '')
        # which would trigger on all %-characters, e.g. "&". If might
        # actually be better, since a url part that is quoted is
        # likely quoted properly and won't contain, e.g. a '&'. Thus,
        # if we find a '&', we should be able to conclude that the
        # string is unquoted and needs quoting. Currently, we would
        # miss that situation.
        if s.encode('ascii', 'replace') != s or force_quote:
            return urllib.quote(s.encode('utf8'), safe=safe)
        return s
    username = quote(parts.username, '')
    password = quote(parts.password, safe='')
    path = quote(parts.path, safe='/')
    query = quote(parts.query, safe='&=')

    # put everything back together
    netloc = hostname
    if username or password:
        netloc = '@' + netloc
        if password:
            netloc = ':' + password + netloc
        netloc = username + netloc
    if parts.port:
        netloc += ':' + str(parts.port)
    return urlparse.urlunsplit([
        parts.scheme, netloc, path, query, parts.fragment])


class UrlOpenError(Exception):
    pass

def urlopen(url, *args, **kwargs):
    """Wrapper around ``urllib2.urlopen`` that uses the handlers and the
    user agent string defined in the feedplatform configuration.

    It further attempts to support unicode URLs, i.e. non-ascii characters
    in both domain name and path.

    This should be used whenever network access is required as part of the
    aggregator functionality.

    It also normalizes exception handling, which is slightly challenging,
    and reraises ``UrlOpenError``s for exceptions that you likely want to
    handle was potentially expected.
    """
    opener = urllib2.build_opener(*config.URLLIB2_HANDLERS)
    try:
        request = urllib2.Request(url, *args, **kwargs)
        request.add_header('User-Agent', config.USER_AGENT)
        url = asciify_url(url)
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


def with_socket_timeout(func):
    """Decorator that makes sure that the wrapped function uses the socket
    timeout specified in the settings.

    Restores the original timeout value after the call.
    """
    def wrapper(*args, **kwargs):
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(config.SOCKET_TIMEOUT)
        try:
            return func(*args, **kwargs)
        finally:
            socket.setdefaulttimeout(old_timeout)
    return wrapper


if __name__ == '__main__':
    import doctest
    doctest.testmod()