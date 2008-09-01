"""Make the code that returns the data for a fake HTTP response
based on the feed or file requested and it's attributes like ``content``,
``headers`` etc.
"""

from nose.tools import assert_raises
from feedplatform import test


def _get_file(File):
    return test.testcustom([File], run=False).get_file(File.url)


def test_values_rendered():
    """Test that all relevant values are rendered.
    """

    v_content = '{% <5 %}bla{% end %}'
    v_headers = {'foo': '{% <5 %}bar{% end %}'}
    v_status = '{% <5 %}200{% end %}'

    class TestFile(test.File):
        content = v_content
        headers = v_headers
        status = v_status

    assert _get_file(TestFile) == (200, {'foo': 'bar'}, 'bla')


def test_callables_unrendered():
    """Test that all the attributes may be callables, and their
    results not rendered by default.
    """

    v_content = '{% =5 %}foo{% end %}'
    v_headers = {'A-Header': '{% =5 %}bar{% end %}'}

    class TestFile(test.File):
        content = lambda p: v_content
        headers = lambda p: v_headers

    assert _get_file(TestFile)[1:] == (v_headers, v_content)


    # This is more though to test for the status code, where a rendered
    # template would have to return a string that represents a valid
    # number. however, we don't know in this case whether it was passed
    # though the rendering engine. Instead, we deliberately cause an error.
    class StatusTestFile(test.File):
        content = ""
        status = '{% =5 %}200{% end %}'
    assert_raises(ValueError, _get_file, StatusTestFile)


def test_callables_rendered():
    """Test that a callable can have it's result rendered.
    """
    v_content = '{% <5 %}bla{% end %}'
    v_headers = {'foo': '{% <5 %}bar{% end %}'}
    v_status = '{% <5 %}999{% end %}'

    class TestFile(test.File):
        content = lambda p: (v_content, True)
        headers = lambda p: (v_headers, True)
        status = lambda p: (v_status, True)

    assert _get_file(TestFile) == (999, {'foo': 'bar'}, 'bla')


def test_render_dicts():
    """Test that if a dict is returned, all of it's values will be
    rendered instead.

    Used in previous tests, but test explicitly.
    """

    class TestFile(test.File):
        content = ""
        headers = {'foo': '{% <5 %}bar{% end %}'}

    assert _get_file(TestFile)[1] == {'foo': 'bar'}


def test_status_int_coercion():
    """Test that the status code may be returned as a string type.

    Used in previous tests, but test explicitly.
    """

    class TestFile(test.File):
        content = ""
        headers = '200'
    assert _get_file(TestFile)[0] == 200

    # if the string is invalid, an error is raised
    class BadStatusFile(test.File):
        content = ""
        status = 'abc'
    assert_raises(ValueError, _get_file, BadStatusFile)