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
        for i in xrange(0, feeds.count()):  # XXX: only do this in sqlite
            feed = feeds[i]
            counter += 1
            update_feed(feed, {})
            if do_return():
                return
        if do_return():
            return


def update_feed(feed):
    """Parse and update a single feed, as specified by the instance
    of the ``Feed`` model in ``feed``.

    This is the one, main, most important core function, at the
    epicenter of the package, providing different hooks to the rest
    of the world.
    """

    # HOOK: BEFORE_PARSE
    parser_args = {
        'agent': config.USER_AGENT,
        'handlers': list(config.URLLIB2_HANDLERS),
    }
    stop = hooks.trigger('before_parse', args=[feed, parser_args])
    if stop:
        log.info('Feed #%d skipped by addin' % (feed.id))
        return

    # ACTION: PARSE FEED
    log.info('Updating feed #%d: %s' % (feed.id, feed.url))
    data_dict = feedparser.parse(feed.url, **parser_args)

    # HOOK: AFTER_PARSE
    stop = hooks.trigger('after_parse', args=[feed, data_dict])
    if stop:
        log.info('Feed #%d: Futher processing skipped by addin' % (feed.id))
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
        # TODO: add a hook here
        log.warn('Feed #%d bozo: %s' % (feed.id, data_dict.bozo_exception))

    # ACTION: HANDLE ITEMS
    for entry_dict in data_dict.entries:

        # ACTION: DETERMINE GUID; HOOKS: GET_GUID, NEED_GUID
        #
        # Determine a unique id for the item; this is one of the
        # few fixed requirements that we have: we need a guid.
        # Addins can provide new ways to determine one, but if all
        # fails, we just can't handle the item.
        guid = hooks.trigger('get_guid', args=[feed, entry_dict])
        if not guid:
            guid = entry_dict.get('guid')
        if not guid:
            guid = hooks.trigger('need_guid', args=[feed, entry_dict])

        # HOOK: NO_GUID
        if not guid:
            hooks.trigger('no_guid', args=[feed, entry_dict])
            log.warn('Feed #%d: unable to determine item guid' % (feed.id))
            continue
        else:
            log.debug('Feed #%d: determined item guid "%s"' % (feed.id, guid))


        # ACTION: RESOLVE GUID TO ITEM; HOOKS: GET_ITEM, NEED_ITEM
        #
        # XXX: we need more extensive testing here, with all the variants
        # of returning items, return false etc. involved.
        #
        # Note how each hook result is passed through get_one, since a
        # possible issue when resolving a guid is that for whatever
        # reason the database may contain multiple matching rows. This
        # is a error, and we handle it here for both our default query
        # as well as results delievered via a hook (the latter means
        # that addins don't have to care about this situation
        # themselves).
        try:
            item = db.get_one(hooks.trigger('get_item',
                                            args=[feed, entry_dict, guid]))
            if item is None:
                # does the item already exist for *this feed*?
                item = db.get_one((db.store.find(db.models.Item,
                                                 db.models.Item.feed==feed,
                                                 db.models.Item.guid==guid)))
            if item is None:
                item = db.get_one(hooks.trigger('need_item',
                                                args=[feed, entry_dict, guid]))
        except db.MultipleObjectsReturned:
               # TODO: log a warning/error, provide a hook
               # TODO: test for this case
               return


        if not item:
            # HOOK: BEFORE_NEW_ITEM
            item = hooks.trigger('create_item', args=[feed, entry_dict, guid])
            if not item:
                item = db.models.Item()
                item.feed = feed
                item.guid = guid

            db.store.add(item)
            # HOOK: NEW_ITEM
            #
            # Note how this happens before flushing(), so that any
            # changes made by this hook will go into the initial
            # INSERT query. If you need an existing primary key, use
            # the process_item hook instead.
            hooks.trigger('new_item', args=[item, entry_dict])

            db.store.flush()
            log.info('Feed #%d: found new item (#%d)' % (feed.id, item.id))
            item_created = True
        else:
            # HOOK: FOUND_ITEM
            hooks.trigger('found_item', args=[item, entry_dict])
            item_created = False

        # HOOK: PROCESS_ITEM
        hooks.trigger('process_item', args=[item, entry_dict, item_created])

        # flush once for each item
        db.store.flush()

    # commit once for each feed
    db.store.commit()