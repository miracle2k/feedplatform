"""Parsing functionality.

Contains routines that interact with the database, updating feeds and
other sorts of maintenance. Makes great use of the hook infrastructure
to let addins extend the process.

The management tools and parsing scripts exposed to the user depend
on this code.
"""

from hashlib import md5
import feedparser

from feedplatform import hooks
from feedplatform.log import log
from feedplatform.conf import config
from feedplatform import db
from feedplatform.db import Feed, Item


def simple_loop():
    #feed = db.store.get_next_feed()
    #while feed:
    #    update_feed(feed)
    #    feed = db.store.get_next_feed()
    while True:
        feeds = db.store.find(Feed)
        for feed in feeds:
            update_feed(feed, {})


def update_feed(feed, kwargs):
    """Parse and update a single feed, as specified by the instance
    of the ``Feed`` model in ``feed``.

    This is the one, main, most important core function, at the
    epicenter of the package, providing thousands of different hooks
    to the rest of the world.
    """

    log.info('Updating feed #%d: %s' % (feed.id, feed.url))
    feed_dict = feedparser.parse(feed.url, agent=config.USER_AGENT, **kwargs)

    # The bozo feature Universal Feed Parser allow it to parse feeds
    # that are not well-formed (http://feedparser.org/docs/bozo.html).
    # While very useful in many cases, it also means that just about
    # anything, from 404 to parking pages will be represented as a
    # feed object with the bozo flag set (about without any useful
    # feed data obviously - for example, the whole page content will
    # be inside the ``subtitle`` field).
    #
    # How do we differentiate between "valid" feed problems like a
    # missing closing tag, that could potentially be ignored while
    # still extracting useful content, and completely invalid data?
    # Simple, we don't. This will be the job of the error handling
    # addin, and should not be our care right now. Suffice to say
    # though that it is important for the addin to make sure that
    # those completely invalid feeds are skipped early so that e.g.
    # a previously valid feed title in the database is not overridden
    # with empty or clearly erroneous data.
    #
    # We will log the problem, though.
    if feed_dict.bozo:
        log.warn('Feed #%d bozo: %s' % (feed.id, feed_dict.bozo_exception))

    for entry_dict in feed_dict.entries:

        # Determine a unique id for the item; this is one of the
        # few fixed requirements that we have: we need a guid.
        # Addins can provide new ways to determine one, but if all
        # fails, we just can't handle the item.
        guid = _find_guid(entry_dict)
        if not guid:
            log.warn('Feed #%d: unable to determine item guid' % (feed.id))
            continue
        else:
            log.debug('Feed #%d: determined item guid "%s"' % (feed.id, guid))

        # does the item already exist?
        items = list(db.store.find(Item, Item.guid==guid))
        if len(items) >= 2:
            # TODO: log a warning/error
            return
        elif items:
            item = items[0]
        else:
            item = None

        if not item:
            # it doesn't, so create it
            item = Item()
            item.feed = feed
            item.guid = guid
            db.store.add(item)
            db.store.flush()
            log.info('Feed #%d: found new item (#%d)' % (feed.id, item.id))

    db.store.commit()


def _find_guid(entry_dict):
    """Helper function to determine the guid of an item.

    Preferably, use use the guid specified. If that fails (lots of
    feeds don't have them), try hard to come up with a plan B.

    # TODO: refactor this so that addins can easily add their own
      guid logic; the enclosure-guid should probably be a separate addin,
      but enabled automatically by the enclosure() addin?
    """
    guid = entry_dict.get('guid')
    if not guid:
        # for podcast feeds, the enclosure is usually a defining element
        if 'enclosures' in entry_dict:
            guid = 'enclosure:%s'% entry_dict.enclosures[0].href
    if not guid:
        # try a content hash
        content = u"%s%s" % (entry_dict.get('title'), entry_dict.get('summary'))
        if content:
            hash = md5(content.encode('ascii', 'ignore'))
            guid = u'content:%s' % hash.hexdigest()
    return guid