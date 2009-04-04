from feedplatform.lib import *
from feedplatform.integration.django.models import make_dsn

DATABASE = make_dsn()

from Queue import Queue
queue = Queue(0)

ADDINS = [
    provide_loop_daemon(name="loop"),
    provide_multi_daemon(daemons=[
	provide_queue_daemon(queue),
	provide_socket_queue_controller(queue, ('localhost', 7777))
    ], name="queue"),
    collect_feed_data('title', 'updated', 'summary', 'language'),
]
