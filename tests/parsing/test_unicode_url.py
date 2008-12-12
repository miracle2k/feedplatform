"""Test that we properly support unicode urls.

TODO: Currently, this tests only ``urlopen``, not normal feed access
through FeedParser.
"""

from feedplatform import test as feedev


class UnicodeFile(feedev.File):
    query_url = u"http://rüdiger.de/persönlich.html"
    url = u"http://xn--rdiger-3ya.de/pers%C3%B6nlich.html"
    content = "a"

# as usual we need a dummy feed because only while running a evolution
# do we have access to ``UnicodeFile``.
class TestFeed(feedev.Feed):
    content = """"""
    def pass1(feed):
        from feedplatform.util import urlopen
        assert urlopen(UnicodeFile.query_url).read() == UnicodeFile.content


def test():
    feedev.testmod()