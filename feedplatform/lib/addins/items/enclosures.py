"""Addins that deal with item enclosures.

TODO: A ``store_enclosure`` addin (singular) that handles only one
enclosure and doesn't rely on a separate table, but rather fields
in the item table might be nice.
"""

from storm.locals import Unicode, Int, Reference, ReferenceSet

from feedplatform import addins
from feedplatform import db
from feedplatform import hooks
from feedplatform.lib.addins.feeds.collect_feed_data \
    import _base_data_collector


__all__ = (
    'store_enclosures',
    'collect_enclosure_data'
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
    make it possible to customize the enclosure handling. Those work
    pretty much the same way as the hooks for item processing:

        * create_enclosure (item, enclosure_dict, href)
            Before an Enclosure model instance is created; May return
            one to override the default creation.

        * new_enclosure (enclosure, enclosure_dict)
            After a new enclosure has been created; can be used to
            initialize it.

        * found_enclosure (enclosure, enclosure_dict)
            When an enclosure was determined to be already existing.
            Can be used to update it.

        * process_enclosure (enclosure, enclosure_dict, created)
            Like ``process_item``, this combines both ``new_enclosure``
            and ``found_enclosure``. While the enclosure, unlike an item,
            will not have been flushed at this point, you should
            nevertheless decide whether to use this hook on the same
            merits: If you just want to modify the element, use
            ``new`` and ``found``, otherwise use ``process``. If every
            addin follows this principle, ideally, during ``process``,
            the enclosure object itself will not be changed, and when
            combined with an addin that implicitely flushes the
            enclosure, multiple writes to the enclosure are nevertheless
            avoided.
    """

    def get_hooks(self):
        return ('create_enclosure', 'new_enclosure',
                'found_enclosure', 'process_enclosure',)

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
        """
        Per the suggested protocol, we're using ``process_item``, since we
        don't want nor need to cause an update to the item, but instead
        require it to be flushed, so we can hook up enclosures to it.
        """

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
        for enclosure_dict in enclosures:
            href = enclosure_dict.get('href')
            # bug in feedparser can return those as bytestrings when bozo
            if href is not None and not isinstance(href, unicode):
                href = href.decode('utf8', 'ignore')
            if not href:
                self.log.debug('Item #%d: enclosure has no href '
                    '- skipping.' % item.id)
                continue

            try:
                enclosure = db.get_one(
                    db.store.find(db.models.Enclosure,
                        db.models.Enclosure.href == href,
                        db.models.Enclosure.item_id == item.id))
            except db.MultipleObjectsReturned:
                # TODO: log a warning/error, provide a hook
                # TODO: test for this case
                pass


            if enclosure is None:
                # HOOK: CREATE_ENCLOSURE
                enclosure = hooks.trigger('create_enclosure',
                    args=[item, enclosure_dict, href])
                if not enclosure:
                    enclosure = db.models.Enclosure()
                    enclosure.item = item
                    enclosure.href = href
                    db.store.add(enclosure)

                # HOOK: NEW_ENCLOSURE
                hooks.trigger('new_enclosure',
                    args=[enclosure, enclosure_dict])
                enclosure_created = True

                self.log.debug('Item #%d: new enclosure: %s' % (item.id, href))
            else:
                # HOOK: FOUND_ENCLOSURE
                hooks.trigger('found_enclosure',
                    args=[enclosure, enclosure_dict])
                enclosure_created = False

            # HOOK: PROCESS_ENCLOSURE
            hooks.trigger('process_enclosure',
                args=[enclosure, enclosure_dict, enclosure_created])


class collect_enclosure_data(_base_data_collector):
    """Collect enclosure-level meta data, and store it in the database.

    This works precisely like ``collect_feed_data``, except that
    the supported known fields are:

    length, type

    Although you may specify custom fields, their use is limited, since
    their rarely will be any.
    """

    depends = (store_enclosures,)

    model_name = 'enclosure'
    standard_fields = {
        'length': (Int, (), {}),
        'type': (Unicode, (), {}),
    }

    def _process_field(self, field, value):
        if field == 'length':
            try:
                return int(value)
            except ValueError:
                # TODO: potentially log an error here (in the
                # yet-to-be-designed error system, not just a log message)?
                self.log.debug('Enclosure has invalid length value: %s' % value)
                return None
        else:
            return super(collect_enclosure_data, self)._process_field(field, value)

    def on_found_enclosure(self, enclosure, enclosure_dict):
        return self._process(enclosure, enclosure_dict)

    def on_new_enclosure(self, enclosure, enclosure_dict):
        return self._process(enclosure, enclosure_dict)