"""Test the image wrapper class used internally.
"""

from feedplatform.lib.addins.feeds.images import Image
from StringIO import StringIO


def test_read_incremental():
    """Test incremental use of read() method.
    """

    data = 'b'*50

    direct = StringIO(data)
    image = Image(StringIO(data))
    image.chunk_size = 32

    # seeking through both the StringIO and the Image wrapping
    # around one yields the same results.
    for c in [25,15,15]:
        assert image.read(c) == direct.read(c)


def test_read_full():
    """Test using read() to get the full contents at once.
    """

    data = 'b'*50

    direct = StringIO(data)
    image = Image(StringIO(data))
    image.chunk_size = 32

    assert image.read() == direct.read()