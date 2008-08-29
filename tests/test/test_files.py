from nose.tools import assert_raises
from feedplatform import test as feedev

def test_different_default_url():
    # File and Feed default urls use different prefixes, so even if they
    # have the same name, they are uniquely addressable.
    foo1 = type('Foo', (feedev.Feed,), {})
    foo2 = type('Foo', (feedev.File,), {})

    print foo1.url, foo2.url
    assert foo1.url != foo2.url


def test_files_no_passes():
    # passes are not executed on files...
    class Foo(feedev.File):
        def pass1(feed):
            pass

    # ...therefore, we'll get a "no passes" exception here.
    assert_raises(RuntimeError, feedev.testcaller)