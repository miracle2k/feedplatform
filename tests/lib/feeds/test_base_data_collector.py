"""``base_data_collector`` is the base class for the ``collect_*_data``
addins.

Most of it's funtionality is already ensured to be working by the tests
for those other addins, but we want to specifically test some scenarios
here that are relevant for people writing custom addins based on it.
"""

import datetime
from storm.locals import Unicode

from feedplatform import test
from feedplatform import db
from feedplatform.lib.addins.feeds.collect_feed_data \
    import base_data_collector


def test_custom_fieldname():
    """[bug] Make sure that the extended syntax, that allows the collector
    to support a "standard field" field by the name X, but map it to a
    model field with a different name, works as expected.

    In particular we had a bug initially that caused the wrong field to be
    added to the generated models.
    """

    class my_collector(base_data_collector):
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


def test_special_fields():
    """Test the special fields that every subclass will be able to provide.
    """

    class my_collector(base_data_collector):
        model_name = 'feed'
        standard_fields = {}
        def on_after_parse(self, feed, data_dict):
            return self._process(feed, data_dict.feed)

    ADDINS = [my_collector(__now='last_processed')]

    class BozoFeed(test.Feed):
        # make sure the content here is not a valid feed, we want to make
        # sure that this works even when feed the is bozo.
        content = """<bozo>"""

        def pass1(feed):
            assert hasattr(feed, 'last_processed')
            assert hasattr(db.models.Feed, 'last_processed')
            # field should now have a value not too far from right now
            assert abs(feed.last_processed - datetime.datetime.utcnow()).seconds < 10

    test.testcaller()