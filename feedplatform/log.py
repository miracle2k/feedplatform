"""Exposes Python logging facilities especially customized for use
within FeedPlatform.
"""

import sys
import logging

__all__ = ('log', 'set_logger', 'reset')


_logger = None

# using a proxy allows switching the logger instance even for
# code that has already imported an older instance.
class logger_proxy(object):
    def __getattribute__(self, name):
        return getattr(_logger, name)
log = logger_proxy()

def set_logger(l):
    """Fully replace the logger. This works well only a proxy
    object is exposed.
    """
    global _logger
    _logger = l

def reset():
    """(Re)configure the default logger."""

    log = logging.getLogger('feedplatform')

    # might be an existing object, reset it
    for handler in log.handlers:
        log.removeHandler(handler)
    for filter in log.filters:
        log.removeFilter(filter)

    # configure & use
    log.addHandler(logging.StreamHandler(sys.stdout))
    log.level = logging.INFO
    set_logger(log)

reset()