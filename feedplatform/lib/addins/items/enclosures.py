"""Addins that deal with item enclosures.

TODO: A ``store_enclosure`` addin (singular) that handles only one
enclosure and doesn't rely on a separate table, but rather fields
in the item table might be nice.
"""

from feedplatform import addins
from feedplatform import db
from storm.locals import Unicode, Int, Reference, ReferenceSet


__all__ = (
    'store_enclosures',
)


class store_enclosures(addins.base):
    """Stores enclosures attached to items.

    Uses a separate table/model for this, which you are free to use
    and extend like the existing ones.

    Multiple enclosures are supported. While the RSS spec is not clear
    on whether multiple enclosures are allowed, the consensus seems
    to be that an entry can only have one enclosure. However, some
    feeds break this rule. Atom generally allows multiple enclosures.
    For all those reasons, we support multiple enclosures.
    See also:
        http://www.reallysimplesyndication.com/2004/12/21#a221
        http://www.feedparser.org/docs/uncommon-rss.html

    By default, only the ``href`` value is stored, which works
    similarily to an item's ``guid``. Enclosures without a ``href``
    attribute are ignored. If you need other enclosure data, see
    the ``collect_enclosure_data`` addin.

    To make ``collect_enclosure_data`` and possibly other addin
    functionality work, this addin registers additional hooks that
    make it possible to customize the enclosure handling.
    """

    def __init__(self):
        pass

    def get_columns(self):
        return {
            'enclosure': {
                'id': (Int, (), {'primary': True}),
                'item_id': (Int, (), {}),
                'href': (Unicode, (), {}),
                'item': (Reference, ('item_id', 'Item.id',), {}),
            },
            'item': {
                'enclosures': (ReferenceSet, ('Item.id', 'Enclosure.item_id',), {}),
            }
        }

    def on_process_item(self, item, entry_dict, item_created):

        enclosures = entry_dict.get('enclosures', ())

        # check for deleted enclosures (don't bother with new items)
        if not item_created:
            available_hrefs = [e.get('href') for e in enclosures]
            for enclosure in item.enclosures:
                if not enclosure.href in available_hrefs:
                    self.log.debug('Item #%d: enclosure #%d ("%s") no '
                        'longer exists - deleting.' % (
                            item.id, enclosure.id, enclosure.href))
                    db.store.remove(enclosure)

        # add new enclosures
        for enclosure_dict in entry_dict.enclosures:
            href = enclosure_dict.get('href')
            if not href:
                self.log.debug('Item #%d: enclosure has no href '
                    '- skipping.' % item.id)
                continue

            try:
                enclosure = db.get_one(
                    db.store.find(db.models.Enclosure,
                        db.models.Enclosure.href == href))
            except db.MultipleObjectsReturned:
                # TODO: log a warning/error, provide a hook
                # TODO: test for this case
                pass

            if enclosure is None:
                enclosure = db.models.Enclosure()
                enclosure.item = item
                enclosure.href = href
                db.store.add(enclosure)

                self.log.debug('Item #%d: new enclosure: %s' % (item.id, href))