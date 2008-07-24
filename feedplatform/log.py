"""Exposes Python logging facilities especially customized for use
within FeedPlatform.
"""

import sys
import logging

__all__ = ('log', 'reset')


log = None

def reset():
    """(Re)configure the default logger."""

    new_logger = logging.getLogger('feedplatform')

    # might be an existing object, reset it
    for handler in new_logger.handlers:
        new_logger.removeHandler(handler)
    for filter in new_logger.filters:
        new_logger.removeFilter(filter)

    # configure
    new_logger.addHandler(logging.StreamHandler(sys.stdout))
    new_logger.level = logging.INFO

    # use
    global log
    log = new_logger

reset()