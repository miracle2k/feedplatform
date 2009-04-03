from feedplatform.lib import *
from feedplatform.integration.django.models import make_dsn

DATABASE = make_dsn()

ADDINS = [
    provide_loop_daemon,
    collect_feed_data('title', 'updated', 'summary', 'language'),
]
