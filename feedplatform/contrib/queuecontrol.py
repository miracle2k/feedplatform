"""FeedPlatform includes the ``provide_socket_queue_controller`` addin,
which sets up a daemon that listens on a socket, and updates the feeds
that are sent to it there, using a simple protocol.

This module implements a simple client side to that. You can use this,
or may simple write your own version.

Example Usage:

    try:
        send_to_queue('/var/run/feedplatform.ping',
                      'http://example.org/news.xml')
    except QueueUserError, e:
        print "You did something wrong: %s", e.message
    except QueueSystemError, e:
        print "We did something wrong: %s", e.message

You can choose not to catch system errors, for example, e.g. instead
letting your logging system deal with it.

# TODO: This is in a contrib module to emphasis it's utility nature,
rather than being the "official" interface. On the other hand, keeping
related code together acounts for something as well, e.g. we could make
this a static method of the ``provide_socket_queue_controller`` addin:

    from feedplatform.lib import provide_socket_queue_controller
    provide_socket_queue_controller.send_to_queue(...)
"""

import socket


__all__ = ('send_to_queue', 'QueueError', 'QueueUserError', 'QueueSystemError',)


class QueueError(Exception):
    pass

class QueueUserError(QueueError):
    pass

class QueueSystemError(QueueError):
    pass


def send_to_queue(address, feed_id_or_url):
    s = socket.socket(isinstance(address, basestring) \
                            and socket.AF_UNIX or socket.AF_INET)
    try:
        try:
            s.connect(address)
        except socket.error, msg:
            raise PingSystemError('Unable to connect to bot, try again later')
        else:
            s.send("%s\n" % feed_id_or_url)
            response = s.recv(1024)
            code, msg = response.split(' ', 1)
            try:
                code = int(code)
            except ValueError:
                raise PingSystemError('Invalid response code from bot: %s' % code)
            if 200 <= code < 400:
                return
            elif code == 404:
                error = PingUserError('The requested feed was not found')
            elif code >= 500:
                error = PingSystemError('Bot was unable to handle the request: %s' % msg)
            error.code = code
            raise error
    finally:
        s.close()