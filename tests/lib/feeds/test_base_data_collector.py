"""``_base_data_collector`` is the base class for the ``collect_*_data``
addins.

Most of it's funtionality is already ensured to be working by the tests
for those other addins, but we want to specifically test some scenarios
here that are relevant for people writing custom addins based on it.
"""

from storm.locals import Unicode

from feedplatform import test
from feedplatform import db
from feedplatform.lib.addins.feeds.collect_feed_data \
    import _base_data_collector


def test_custom_fieldname():
    """[bug] Make sure that the extended syntax, that allows the collector
    to support a "standard field" field by the name X, but map it to a
    model field with a different name, works as expected.

    In particular we had a bug initially that caused the wrong field to be
    added to the generated models.
    """

    class my_collector(_base_data_collector):
        model_name = 'feed'
        standard_fields = {
            'title': {'target': 'my_title_field', 'field': (Unicode, (), {})}
        }

    ADDINS = [my_collector('title')]

    class MyFeed(test.Feed):
        def pass1(feed):
            assert hasattr(feed, 'my_title_field')
            assert hasattr(db.models.Feed, 'my_title_field')

    test.testcaller()