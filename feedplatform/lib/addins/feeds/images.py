"""Addins that handle feed images/covers.

A large part of the functionality in this module requires PIL (but
not everything).
"""

from os import path
import datetime
import urllib2, urlparse
import cgi
import cStringIO

from storm.locals import DateTime

from feedplatform import addins
from feedplatform import db
from feedplatform import hooks
from feedplatform.util import urlopen
from collect_feed_data import _base_data_collector


__all__ = (
    'handle_feed_images',
    'collect_feed_image_data',
    'feed_image_to_filesystem',
    'feed_image_thumbnails',
)


# used internally
class _ImageTooLarge(Exception):
    pass


class Image(object):
    """Represents a feed's image as passed around internally to exchange
    data between the addins that need to deal with the image.

    Apart from holding image-related data (like mime type, file extension)
    and thus acting as a container for it (instead of that passed along
    through hooks separately), it's main purpose is to encapsulate access
    to the feed image, since the best way to do this may depend on the
    addins and options used.

    For example, in the simpliest case, the data may just be written
    directly from the socket to the disk. However, if we are supposed to
    identify the image type for validation purposes, then PIL needs to
    get involved early, and the image has to be hold in memory.

    This class takes care of all that, so that each addin doesn't have to
    do it itself.

    It also does a live validation of the images maximum size, if
    requested, since a Content-Length header may be fake or missing.
    Should the size exceed the limit, an exception will be raised during
    reading from it, which the user should capture.
    """

    # size of chunk size to use when reading image from source
    chunk_size = 1024

    def __init__(self, source, max_size=None):
        self.source = source
        self.max_size = max_size
        self._bytes_read = 0

    def _validate_size(self):
        # validate the actual size of the file
        if self.max_size and self._bytes_read > self.max_size:
            raise _ImageTooLarge()

    def read(self, n=-1):
        result = self.source.read(n)
        self._bytes_read += len(result)
        self._validate_size()
        return result

    def tell(self):
        return self.source.tell()

    def seek(self, pos):
        result = self.source.seek(pos)
        self._validate_size()
        return result

    @property
    def pil_image():
        if not hasattr(self, '_pil_image'):
            from PIL import Image as PILImage
            self._pil_image = PILImage(self)

        return self._pil_image


def _parse_http_contenttype(content_type):
    """Takes HTTP Content-Type header and returns
    ``(content type, charset)``.

    ``charset`` may be an empty string. If ``content type`` is None,
    ``('', '')`` is returned.

    Both return values are guaranteed to be lowercase strings.

    This is adapted from feedparser.py's ``_parseHTTPContentType``.
    """
    content_type = content_type or ''
    content_type, params = cgi.parse_header(content_type)
    return content_type, params.get('charset', '').replace("'", '')


class handle_feed_images(addins.base):
    """The core addin for feed image handling. All other related plugins
    build on this.

    It will check feeds for feed images and download them, provided they
    match the requirements:

        * ``max_size``:
            The maximum filesize in bytes. If the image is larger than
            this number, it will be ignored. ``None`` means no limit
            (the default).

        * ``restrict_extensions``:
            A tuple or list of allowed file extensions. If an image has
            an extension not in this list, it will be ignored. The
            extensions in the tuple should not include dots, e.g.:
                restrict_extensions=('png','gif')
            ``None`` means no restriction (the default).
            # TODO: support a default list of extensions, by passing True.

        * ``restrict_mediatypes``:
            A tuple or list of allowed media types. If an image is sent
            with a media type not in this list, it will be ignored.
            ``None`` means no restriction (the default).
            # TODO: support a default list of types, by passing True.

        * ``update_every``:
            The number of seconds (or a ``timedelta`` instance) that must
            pass since the last update of a cover, before it is updated
            again. This is very useful to avoid having to download every
            cover every time the feed is parsed. If you are using
            thumbnails or other complex processing, make sure you are
            using a restriction like this.

    The image is stored in memory or a temporary location. Via new hooks
    provided by this addin, other addins may then proceed to do something
    with the image, like saving it in a given filesystem structure, see
    ``feed_image_to_filesystem`` for example.

    # TODO: write in more details about the two hooks that we add, any that
    the reason for the separation is that update_feed_image may fail.
    implementers will also have to look out for imagetoolarge errors.

    # TODO: support updating the image when the href changes. This
    requires us to store the href, possibly by using functionality of
    the ``store_feed_image_data`` addin?

    # TODO: support overriding the actual extension with one deducted
    from the mediatype, if available.
    # TODO: support getting the image extension based on the file contents
    as detected by PIL, overriding the actual extension.
    """

    def __init__(self, max_size=None, restrict_extensions=None,
                 restrict_mediatypes=None, update_every=None):
        self.max_size = max_size
        self.restrict_extensions = restrict_extensions
        self.restrict_mediatypes = restrict_mediatypes
        self.update_every = update_every

    def get_hooks(self):
        return ('update_feed_image', 'feed_image_updated')

    def get_columns(self):
        if self.update_every:
            return {'feed': {
                        'image_updated': (DateTime, [], {})}
                   }
        else:
            return {}

    def on_after_parse(self, feed, data_dict):
        # if no image is available at all, skip right over this feed
        image_dict = data_dict.feed.get('image')
        if not image_dict:
            return
        image_href = image_dict.get('href')
        if not image_href:
            return

        # enforce timed update restriction
        if self.update_every:
            if isinstance(self.update_every, datetime.timedelta):
                delta = self.update_every
            else:
                delta = datetime.timedelta(seconds=self.update_every)
            if feed.image_updated and (
                    datetime.datetime.utcnow() - feed.image_updated < delta):
                self.log.warning('Feed #%d: image was last updated'
                        'recently enough' % (feed.id))
                return

        # TODO: possibly an early feed_image_found event here? depends
        # on our needs when we actually solve writing needed data to
        # the db.

        # only bother downloading the image if there are actually
        # hooks that would like to deal with it.
        if hooks.any('update_feed_image'):
            request = self._download(image_href, feed)
            if request:
                image = Image(request, self.max_size)
                try:
                    hooks.trigger('update_feed_image',
                                  args=[feed, image_dict, image],
                                  all=True)
                except _ImageTooLarge:
                    self.log.warning('Feed #%d: image exceeds maximum '
                        'size of %d' % (feed.id, self.max_size))
                else:
                    # sine there was no error, we apparently just
                    # sucessfully updated the image.
                    hooks.trigger('feed_image_updated',
                                args=[feed, image_dict, image],)
                    if self.update_every:
                        feed.image_updated = datetime.datetime.utcnow()

    def _download(self, url, feed):

        # check extension
        if self.restrict_extensions:
            parsed_url = urlparse.urlparse(url)
            ext = path.splitext(parsed_url.path)[1][1:]
            if not ext:
                # sometimes an extension is appended to the querystring
                # TODO: use last query string value as filename
                ext = parsed_url.query.rsplit('.', 1)
                ext = len(ext) >= 2 and ext[1] or ''
                if len(ext) > 4 or not ext.isalpha():
                    ext = None

            if ext and not ext in self.restrict_extensions:
                self.log.debug('Feed #%d: image ignored, %s is not '
                        'an allowed file extension' % (feed.id, ext))
                return

        try:
            request = urlopen(url)
        except urllib2.URLError, e:
            self.log.debug('Feed #%d: failed to download image "%s" (%s)' %
                (feed.id, url, e))
            return

        # check mediatype
        if self.restrict_mediatypes:
            ctype = request.headers.get('Content-Type')
            ctype = _parse_http_contenttype(ctype)[0]
            if ctype and not ctype in self.restrict_mediatypes:
                self.log.debug('Feed #%d: image ignored, %s is not '
                    'an allowed content type' % (feed.id, ctype))
                return None

        # check content-length
        if self.max_size:
            contentlength = request.headers.get('Content-Length')
            if contentlength is not None and int(contentlength) > self.max_size:
                self.log.warning('Feed #%d: image exceeds maximum '
                    'size of %d' % (feed.id, self.max_size))
                return None

        return request


class collect_feed_image_data(_base_data_collector):
    """
    # TODO: add a ``store_in_model`` option to use a separate model for this.
    """
    pass


class feed_image_to_filesystem(addins.base):
    """Will save feed images, as reported by ``handle_feed_cover`` to
    the filesystem.

    The required parameter ``path`` is used to specify the target
    location. It should be a format string that can use the following
    variables:

        s model           currently always "feed"
        d model_id        the database id of the feed
        s filename        the filename (``basename``) from the image url
        s extension       the file extension only, from the image url

    For example, ``path`` might look like this:

        path='/var/aggr/img/%(model)s/%(model_id)d/original.%(extension)s'

    Depending on how you store the image, you later will need some #
    information to access it. For example, in the example above, the
    file extension is an unknown factor. If you store images with their
    full original filename, that is what you will need to know to access
    them. You may use the ``collect_feed_image_data`` to do this.

    Similar to this, one may create an addin that uploads the images to
    Amazon S3, for example.

    # TODO: force filetype (convert image)
    """

    depends = (handle_feed_images,)

    def __init__(self, path):
        self.path = path

    def on_update_feed_image(self, feed, image_dict, image):
        path = self.path % {
            'model': feed.__class__.__name__.lower(),
            'model_id': feed.id,
            'filename': filename,
            'extension': extension,
        }
        image.save(path)
        # TODO: how do we handle too large errors?


class feed_image_thumbnails(addins.base):
    """Automatically create thumbnails for feed images.

    Hooks into ``handle_feed_image`` and uses the same mechanism to
    "announce" the thumbnail images, i.e. they are saved using addins
    like ``feed_image_to_filesystem``.

    The required argument ``sizes`` is an iterable of 2-tuples,
    specifying the requested width/height values of the thumbnails.

    Requires PIL.
    """

    depends = (handle_feed_images,)

    def __init__(self, sizes, typestr="thumb"):
        pass

    def on_update_cover(self, cover, secondary):
        if secondary != "thumb":
            for thumbnail in self._create_thumbnails():
                trigger.update_cover(thumbnail, self.typestr)

    def _create_thumbnails(self):
        pass