"""Test mocking utilities.
"""

import datetime


__all__ = ('MockDateTime',)


class MockDateTime(datetime.datetime):
    """Fake datetime class that supports moving through time.

    Example:

        MockDateTime.install()
        try:
            datetime.datetime.utcnow()
            datetime.datetime.modify(days=2, seconds=30)
            datetime.datetime.utcnow()
        finally:
            MockDateTime.uninstall()
    """

    delta = None

    @classmethod
    def install(self):
        self._datetime = datetime.datetime
        datetime.datetime = MockDateTime

    @classmethod
    def uninstall(self):
        datetime.datetime = self._datetime

    @classmethod
    def modify(self, *args, **kwargs):
        self.delta = datetime.timedelta(*args, **kwargs)

    @classmethod
    def utcnow(self):
        r = super(MockDateTime, self).utcnow()
        if self.delta:
            r += self.delta
        return r