"""If there is a problem with a feed that is only determined on
access, for example if the template has errors, we can not easily
tell the developer that is test is (potentially) incorrect, since
errors at this stage go through the feedparser download code, which
obviously captures those.

Our solution is to print a clear message to the output instead.

Test that this happens.
"""

import sys
from StringIO import StringIO
from feedplatform import test as feedev
from feedplatform import log


class InvalidTemplate(feedev.Feed):
    content = "{% end %}{% end %}{% end %}"

    def pass1(feed):
        pass


def test():
    old_stderr = sys.stderr
    sys.stderr = StringIO()
    try:
        feedev.testmod()
        sys.stderr.seek(0)
        stderr = sys.stderr.read()
    finally:
        sys.stderr = old_stderr

    print "stderr was: ", stderr    # already goes to nose again
    assert 'Failed to render' in stderr
