from storm.locals import Unicode
from feedplatform import test as feedev
from feedplatform.lib import collect_feed_data


ADDINS = [
    # one unicode one datetime field, one custom
    collect_feed_data('title', 'updated', prism_issn=(Unicode, (), {}))
]


class ValidFeed(feedev.Feed):
    content = """
        <rss xmlns:prism="http://prismstandard.org/namespaces/1.2/basic/">
        <channel>
            <title>
                {% =1 %}org title{% end %}
                {% =2 %}changed title{% end %}
            </title>
            <pubDate>
                {% =1 %}Fri, 15 Aug 2008 23:01:39 +0200{% end %}
                {% =2 %}Fri, 17 Aug 2008 23:01:39 +0200{% end %}
            </pubDate>
            <prism:issn>
                {% =1 %}0066-6666{% end %}
                {% =2 %}0099-9999{% end %}
            </prism:issn>
        </channel></rss>
    """

    def pass1(feed):
        # initial values are picked up
        assert feed.title == 'org title'
        assert feed.updated.day == 15
        assert feed.prism_issn == '0066-6666'

    def pass2(feed):
        # changed values are picked up
        assert feed.title == 'changed title'
        assert feed.updated.day == 17
        assert feed.prism_issn == '0099-9999'


class BozoFeed(feedev.Feed):
    content = """
        <rss><channel>
            <title>the-title</title>
            <author>michael
        </channel></rss>
    """

    def pass1(feed):
        # because the feed is bozo (author tag not closed), no data is
        # being stored right now to avoid keeping invalid data. this
        # behaviour might change at some point.
        assert not feed.title


def test():
    feedev.testmod()