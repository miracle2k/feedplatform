"""Addins that relate to HTTP functionality.
"""

from feedplatform import addins
from feedplatform import db
from feedplatform import log


__all__ = (
    'update_redirects',
)


class update_redirects(addins.base):
    """Handles HTTP 301 permanent redirects.

    If a server sends a permanent redirect, you should update your
    database so that the new URL will be used for future requests. For
    the most part, this is a straightforward job, however, with one
    unfortunate catch: The new URL, the redirection target, may already
    exist in your database. In which case there are a number of ways to
    go on:

        1) Delete the current feed
        2) Delete the other feed
        3) Ignore, don't change url
        4) Force, change url regardless (requires the url database column
           to allow duplicates)

    You must choose one of the above options, and then pass to
    ``__init__``:

        for 1) delete="self"
        for 2) delete="other"
        for 3) ignore=True
        for 4) force=True

    In any case, a log message will be emitted, which for 1-2 will be a
    notice, for 3 and 4 a warning.

    # TODO: add a mode for merging items
    """

    def __init__(self, delete=None, force=None, ignore=None):
        if delete:
            if not delete in ['self', 'other']:
                raise ValueError('"%s" is not a valid value for "delete". '
                    'Need "self" or "other".' % delete)

        if not any([delete, force, ignore]):
            raise ValueError('One of the parameters delete, force, '
                'ignore is required')

        if len([x for x in (delete, force, ignore) if x]) > 1:
            raise ValueError('Only one of the parameters delete, force, '
                'ignore is allowed')

        if delete == 'self':
            self._conflict_strategy = self._delete_self
        elif delete == 'other':
            self._conflict_strategy = self._delete_other
        elif force:
            self._conflict_strategy = self._force
        elif ignore:
            self._conflict_strategy = self._ignore

    def on_after_parse(self, feed, data_dict):
        if data_dict.status == 301:
            new_url = data_dict.href
            self.log.info('Feed #%d: permanent redirect to %s' % (feed.id, new_url))
            dup_feeds = db.store.find(db.models.Feed, db.models.Feed.url == new_url)

            if dup_feeds.any():
                return self._conflict_strategy(feed, new_url, dup_feeds)
            else:
                feed.url = new_url

    def _delete_self(self, feed, new_url, dup_feeds):
        self.log.info('Redirect target already exists: removing self')
        # XXX: delete related objects
        db.store.remove(feed)

        # don't process this feed further
        return False

    def _delete_other(self, feed, new_url, dup_feeds):
        self.log.info('Redirect target already exists: removing the other feeds')
        count = 0
        for f in dup_feeds:
            count += 1
            # XXX: we need a solution to delete related objects as well.
            # Storm doesn't seem to do it, and ON DELETE * is not
            # supported by every database backend.
            db.store.remove(f)
        self.log.debug('%d duplicate feeds removed' % count)
        feed.url = new_url

    def _ignore(self, feed, new_url, dup_feeds):
        # simple: don't do anything (except log), we keep the current url
        self.log.info('Redirect target already exists: ignore, keeping the old url')

    def _force(self, feed, new_url, dup_feeds):
        self.log.info('Redirect target already exists: changing to new url anyway')
        feed.url = new_url