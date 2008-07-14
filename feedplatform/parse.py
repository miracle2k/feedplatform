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
from feedplatform import conf

def main_loop():
    # connect to database
    store = connect()

    feed = store.get_next_feed()
    while feed:
        parse_feed(feed)
        feed = store.get_next_feed()

def parse_feed(feed, kwargs):
    ########## ====> HOOK: before_feed (feedobj, url, skip)


    ########## ====> HOOK: before__parse (feedobj, url, skip, args)   (right now basically like before_feed, but seperation of concerns)
    feed = feedparser.parse(self.url, agent=settings.USER_AGENT, **kwargs)
    # TODO: disallow local files for security reasons?

    # If there is no status attribute and bozo is set, it is sane to
    # assume that there was a problem downloading the feed. We skip the
    # actual parsing, but still update the last_update etc. timestamps
    # at the end.
    # TODO: Is there a better way to determine this?
    if feed.bozo and not hasattr(feed, 'status'):
        ########## ====> HOOK: on_parse_error (feedobj, error)
        pass # TODO log/handle the error

    ########## ====> HOOK: after_parse (feedobj, feeddict)           (good to collect data addins, redirect handling)

    for entry in feed.entries:
        ########## ====> HOOK: before_item (feedobj, itemdict, skip)
        # determine a unique id for the item. if a guid doesn't exist,
        # try various alternatives.
        ########## ====> HOOK: before_guid_search
        guid = entry.guid or \
               'enclosure:%s'%entry.enclosures[0].href
        if not guid:
            _guidbase = "%s %s"%(entry.get('title'), entry.get('summary'))
            if _guidbase: guid = md5(_guidbase)
            else: continue;
        ########## ====> HOOK: after_guid_search
        ########## ====> HOOK: no_guid_found

        ########## ====> HOOK: guid_found (return custom item obj)
        # find an item with that guid
        try:
            item_obj = self.items.get(guid=guid)
            ########## ====> HOOK: after_item_loaded
        except Item.DoesNotExist:
            ########## ====> HOOK: before_item_create
            # not found: create it
            item_obj = Item()
            item_obj.feed = self
            item_obj.guid = guid
            ########## ====> HOOK: before_item_save
            item_obj.save()
            ########## ====> HOOK: after_item_save
        else:
            # found: check if we should update it
            if full:  # TODO: better check we we should update it
                item_obj.save()

    ########## ====> HOOK: before_feed_save
    # TODO: depending on addins, it might not be necessary to save the feed?
    self.save()
    ########## ====> HOOK: after_feed_save