"""FeedParser has a bug that causes an empty feed not to be flagged
as bozo.

Here we test the fix for this problem.
"""

from feedplatform.deps import feedparser


def test_149():
    # Test the the problem with feedparser module directly.
    f = feedparser.parse("")
    assert f.bozo