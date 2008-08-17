"""Parsing functionality.

Contains routines that interact with the database, updating feeds and
other sorts of maintenance. Makes great use of the hook infrastructure
to let addins extend the process.

The management tools and parsing scripts exposed to the user depend
on this code.
"""

from hashlib import md5

from feedplatform.deps import feedparser
from feedplatform import hooks
from feedplatform.log import log
from feedplatform.conf import config
from feedplatform import db


def simple_loop(callback=None):
    """Loop forever, and update feeds.

    Callback will be run every time a feed was updated, and is
    expected to take one argument, the number of iterations so far.
    If it returns True, the loop will stop.
    """
    #feed = db.store.get_next_feed()
    #while feed:
    #    update_feed(feed)
    #    feed = db.store.get_next_feed()
    do_return = lambda: callback and callback(counter)
    counter = 0
    while True:
        feeds = db.store.find(db.models.Feed)
        for feed in feeds:
            counter += 1
            update_feed(feed, {})
            if do_return():
                return
        if do_return():
            return


def update_feed(feed, kwargs={}):
    """Parse and update a single feed, as specified by the instance
    of the ``Feed`` model in ``feed``.

    This is the one, main, most important core function, at the
    epicenter of the package, providing thousands of different hooks
    to the rest of the world.
    """

    log.info('Updating feed #%d: %s' % (feed.id, feed.url))
    data_dict = feedparser.parse(feed.url, agent=config.USER_AGENT,
                                 handlers=list(config.URLLIB2_HANDLERS),
                                 **kwargs)

    keep_going = hooks.trigger('after_parse', args=[feed, data_dict])
    if keep_going == False:
        return

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
    if data_dict.bozo:
        log.warn('Feed #%d bozo: %s' % (feed.id, data_dict.bozo_exception))

    for entry_dict in data_dict.entries:

        # Determine a unique id for the item; this is one of the
        # few fixed requirements that we have: we need a guid.
        # Addins can provide new ways to determine one, but if all
        # fails, we just can't handle the item.
        guid = hooks.trigger('get_guid', args=[feed, entry_dict])
        if not guid:
            guid = entry_dict.get('guid')
        if not guid:
            guid = hooks.trigger('need_guid', args=[feed, entry_dict])

        if guid:
            log.debug('Feed #%d: determined item guid "%s"' % (feed.id, guid))
        else:
            hooks.trigger('no_guid', args=[feed, entry_dict])
            log.warn('Feed #%d: unable to determine item guid' % (feed.id))
            continue

        # does the item already exist *for this feed*?
        items = list(db.store.find(db.models.Item,
                                   db.models.Item.feed==feed,
                                   db.models.Item.guid==guid))
        if len(items) >= 2:
            # TODO: log a warning/error
            # TODO: test for this case
            return
        elif items:
            item = items[0]
        else:
            item = None

        if not item:
            # it doesn't, so create it
            item = db.models.Item()
            item.feed = feed
            item.guid = guid
            db.store.add(item)
            db.store.flush()
            log.info('Feed #%d: found new item (#%d)' % (feed.id, item.id))

    db.store.commit()