"""FeedParser has a bug that causes an empty feed not to be flagged
as bozo.

Here we test the fix for this problem.
"""

from feedplatform.deps import feedparser


def test_149():
    # Test the problem with feedparser module directly.
    f = feedparser.parse("")
    assert f.bozo

    # The first version of this patch had a bug that would raise a
    # ``TypeError`` on the following call (whenever an exception
    # occured during feed download, e.g. a normal IOError, host not
    # available). We can simulate this by simply passing None.
    f = feedparser.parse(None)
    assert f.bozo