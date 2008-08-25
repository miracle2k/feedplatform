"""Exposes Python logging facilities especially customized for use
within FeedPlatform.
"""

import sys
import logging

__all__ = ('log', 'reset', 'get')


ROOT_NAME = 'feedplatform'
log = None

def reset(level=logging.INFO):
    """(Re)configure the default logger.
    """

    new_logger = logging.getLogger(ROOT_NAME)

    # might be an existing object, reset it
    for handler in new_logger.handlers:
        new_logger.removeHandler(handler)
    for filter in new_logger.filters:
        new_logger.removeFilter(filter)

    # configure
    new_logger.addHandler(logging.StreamHandler(sys.stdout))
    new_logger.level = level

    # use
    global log
    log = new_logger

# init module
reset()


def get(name):
    """Get a sublogger for ``name``.

    The returned logger instance will be a childlogger of your
    library-wide main logger. Parts of the library can use this to
    separate their log output.
    """
    log = logging.getLogger("%s.%s" % (ROOT_NAME, name))
    return log