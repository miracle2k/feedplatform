"""Addins that handle feed images/covers.

Some of them require PIL.

# TODO: Validate against PIL addin: The image is only processed if PIL finds
a valid image, by looking at the headers (or optionally by fully reading
the image?

# TODO: Support updating the image when the href changes.
"""

import os
import datetime
import urllib2, urlparse
import cgi
import cStringIO as StringIO

from storm.locals import DateTime

from feedplatform import addins
from feedplatform import db
from feedplatform import hooks
from feedplatform.util import urlopen
from collect_feed_data import _base_data_collector


__all__ = (
    'handle_feed_images',
    #'collect_feed_image_data',
    'feed_image_restrict_frequency',
    'feed_image_restrict_size',
    'feed_image_restrict_extensions',
    'feed_image_restrict_mediatypes',
    'feed_image_to_filesystem',
    'feed_image_thumbnails',
)


class ImageError(Exception):
    """Stop image processing.

    See ``handle_feed_images`` docstring for more information on how
    to use this exception in your addins.
    """
    pass


class RemoteImage(object):
    """Represents a remote feed image, by wrapping around an url, and
    encapsulating all access to it.

    This is passed around between the various addins dealing with feed
    images. It holds and provides access to related metadata, as well
    as ensuring that access is as efficient as possible.

    See, depending on the addins installed, and the data operated on,
    we might never need to even start an HTTP request for the image.
    Or, if validation fails early, we may not need to actually download
    the content. Or simply reading it, without storing the information
    may be enough, no need to hold it in memory.
    Addins do not need to care about any of that, and what other addins
    might have done already - rather, they just use the interface
    exposed here.

    During downloading, the ``feed_image_download_chunk`` is triggered
    for each chunk read. See the ``handle_feed_images`` addin for
    more information on that hook.
    """

    chunk_size = 64 * 10**2

    def __init__(self, url):
        self.url = url

    @property
    def request(self):
        """Access to the HTTP request object.

        The first time this is accessed, the actual request will be made.
        """
        if not hasattr(self, '_request'):
            self._request = urlopen(self.url)
        return self._request

    @property
    def content_type(self):
        """Return the images mime type, as indicated by the server in
        the response headers.

        May be None if the data is missing.

        Adapted from feedparser.py's ``_parseHTTPContentType``.
        """
        content_type = self.request.headers.get('Content-Type')
        if not content_type:
            return None
        content_type, params = cgi.parse_header(content_type)
        return content_type

    @property
    def content_length(self):
        """Return the length of the image in bytes, as sent by the server
        in the response headers.

        May be None if the data is missing.
        """
        length = self.request.headers.get('Content-Length')
        if length:
            return int(length)
        return None

    @property
    def filename(self):
        """The filename of the image, as extracted from the URL.
        """
        parsed_url = urlparse.urlparse(self.url)
        return os.path.basename(parsed_url.path)

        # Sometimes an extension is appended to the query, for example:
        #     /image.php?id=345&name=200x200.png
        # If that is the case, should the ``name`` completely replace
        # the filename? What if "name=.png", without a filename?
        ##        ext = parsed_url.query.rsplit('.', 1)
        ##        ext = len(ext) >= 2 and ext[1] or ''
        ##        if len(ext) > 4 or not ext.isalpha():
        ##            ext = None

    @property
    def filename_with_ext(self):
        """The filename, but with an extension from other sources if the
        url itself did not contain one.

        It is however possible that under certain circumstances, no
        extension can be found.
        """
        filename = self.filename
        if not os.path.splitext(filename)[1]:
            ext = self.extension
            if ext:
                filename = '%s.%s' % (filename, ext)
        return filename

    @property
    def extension_by_url(self):
        """Determine the file extension by looking at the URL.

        If the path does not include an extension, we look at the last
        part of the querystring for one.
        """
        ext = os.path.splitext(self.filename)[1]
        if ext:
            return ext[1:]

    @property
    def extension_by_contenttype(self):
        """Determine the file extension by the content type header.

        Compares against a dict of well-known content types.
        """
        return {
            'image/png': 'png',
            'image/gif': 'gif',
            'image/jpeg': 'jpg',
        }.get(self.content_type, None)

    @property
    def extension_by_pil(self):
        """Determine the file extension by looking at the actual
        image format as detected by PIL.

        # TODO: Could possibly be improved so that a full image load
        is not required using ``PIL.ImageFile.Parser``, see also
        ``django.core.files.images.get_image_dimensions``.
        """
        if self.pil:
            return self.pil.format.lower()

    @property
    def extension(self):
        """Return a file extension for the image, by trying different
        things (for example, the url may not contain one).

        In an unlikely, but possible scenario, None can be returned, if
        no extension can be determined.
        """
        return self.extension_by_url or \
               self.extension_by_contenttype or \
               self.extension_by_pil or \
               None

    def _load_data(self):
        """Download the image while yielding chunks as they are
        incoming.

        Called internally when access to the image data is needed. The
        fact that the data is yielded live means the caller may already
        start using it, before the download is completed.
        """
        # TODO: store bigger files on disk?
        self._data = StringIO.StringIO()
        while True:
            chunk = self.request.read(self.chunk_size)
            if not chunk:
                break
            self._data.write(chunk)
            # HOOK: FEED_IMAGE_DOWNLOAD_CHUNK
            hooks.trigger('feed_image_download_chunk',
                          args=[self, self.data.tell()])
            yield chunk
        # reset once we initially loaded the data
        self.data.seek(0)

    @property
    def data(self):
        """Access the image data as a file-object.

        Will cause the image to be downloaded, and stored in a
        temporary location, if not already the case.
        """
        if not self.data_loaded:
            for chunk in self._load_data():
                pass
        return self._data

    @property
    def data_loaded(self):
        """Return True if the image has already been downloaded.

        Check this before accessing ``data` if you want to avoid
        unnecessary network traffic.
        """
        return hasattr(self, '_data')

    def chunks(self):
        """Iterator that yields the image data in chunks.

        Accessing this will cause the image to be downloaded, if that
        hasn't already happend. Chunks will be yielded as they are
        read.

        Otherwise, it iterates over the already downloaded data.

        If the image is fully available in memory, it will be
        returned as a whole (a single chunk).

        TODO: The idea behind yielding chunks while they are downloaded
        and written to a temporary storage for future access is that the
        latter might not even be necessary. Unfortunately, we currently
        have no way of knowing which plugins want to access chunks(), and
        how often. We could solve this maybe by letting addins "announce"
        what capabilities they need (using another hook), and then we
        could decide that if chunks() is only needed once, temporary
        storage of the data is not even necessary.
        Until that is the case, however, the "live-yielding" of chunks we
        currently employ has little significance, and we could just as
        well download the image fully when first needed, and then
        immediately give chunks from the downloaded copy at all times.
        """

        # On first access, download the image, while immediately
        # yielding each chunk we read.
        if not self.data_loaded:
            for chunk in self._load_data():
                yield chunk

        # once we have the image locally, get the data from there
        else:
            self.data.seek(0)
            while True:
                # currently, _data is always a memory StringIO,
                # no reason to read that in chunks
                chunk = self.data.read()
                if not chunk:
                    break
                yield chunk

    @property
    def pil(self):
        """Return a PIL image.

        Created on first access.
        """
        from PIL import Image as PILImage
        if not self.pil_loaded:
            self.data.seek(0)  # PIL lies in docs, does not rewind
            try:
                self._pil = PILImage.open(self.data)
            except IOError, e:
                raise ImageError('Not a valid image: %s' % e)

        return self._pil

    @property
    def pil_loaded(self):
        """Return True if a PIL image is already available.

        Use this if want to avoid unnecessarily initializing a PIL
        image, since accessing PIL will do exactly that.
        """
        return hasattr(self, '_pil')

    def save(self, filename, format=None):
        """Save the image to the filesystem, at the given ``filename``.

        Specify ``format`` if you want to ensure a certain image format.
        Note that this will force saving via PIL.

        In other cases, PIL may be avoided completely.

        TODO: In the future, this might support writing to an arbitrary
        storage backend, rather than requiring non-filesystem addins to
        write their own save() code?
        """

        # If a PIL image is already available, or required due to
        # a requested format conversion, save the image through PIL.
        if format or (self.pil_loaded and self.pil):
            self.pil.save(filename, format)

        # Otherwise write the data manually
        else:
            f = open(filename, 'wb')
            try:
                for data in self.chunks():
                    f.write(data)
            finally:
                f.close()


class handle_feed_images(addins.base):
    """The core addin for feed image handling. All other related plugins
    build on this.

    It simply checks for the existance of an image, and when found,
    triggers a sequence of three hooks:

        * ``feed_image``:
            A feed image was found; This is the initial validation stage,
            and addins may return a True value to stop further processing.
            For example, the file extension may be validated.

        * ``update_feed_image``:
            At this point the image has been vetted, and addins may try
            to process it - for example, writing it to the disk, or
            submitting it to a remote storage service (i.e. S3).

        * ``feed_image_updated``:
            The image was successfully processed. Addins may use this
            opportunity to do clean-up work, e.g. delete temporary files,
            mark the success in the database, store the data necessary
            to later access the image etc.

    All of those hooks are passed the same arguments: The feed model
    instance, the image_dict from the feedparser, and a ``RemoteImage``
    instance. The latter is where the magic happens, since it encapsulates
    all access the image for addins. For example, depending on the addins
    installed, an HTTP request may or may not need sending, or the image
    may or may not need downloading.
    See ``RemoteImage`` for  more information.

    # TODO: about error handling, and how all three hooks are in the same
    # try-except, and therefore merely semantic differences.
    # TODO: feed_image_download_chunk
    """

    def get_hooks(self):
        return ('feed_image', 'update_feed_image',
                'feed_image_updated', 'feed_image_download_chunk',)

    def on_after_parse(self, feed, data_dict):

        # determine the image url, and bail out early if it is missing
        image_href = None
        image_dict = data_dict.feed.get('image')
        if image_dict:
            image_href = image_dict.get('href')
        if not image_href:
            return

        image = RemoteImage(image_href)

        try:
            # HOOK: FEED_IMAGE
            stop = hooks.trigger('feed_image', args=[feed, image_dict, image])
            if stop:
                return

            # HOOK: UPDATE_FEED_IMAGE
            hooks.trigger('update_feed_image',
                          args=[feed, image_dict, image],
                          all=True)

            # HOOK: FEED_IMAGE_UPDATED
            hooks.trigger('feed_image_updated',
                        args=[feed, image_dict, image],)

        except urllib2.URLError, e:
            self.log.debug('Feed #%d: failed to download image "%s" (%s)' %
                (feed.id, image_href, e))
            return
        except ImageError, e:
            self.log.warning('Feed #%d: error handling image "%s" (%s)' %
                (feed.id, image_href, e))
            return


class feed_image_restrict_size(addins.base):
    """Make sure the feed image does not exceed a specific size.

    ``max_size`` is specified in bytes. It is checked against both
    the Content-Length header (if sent), and the actual number of
    bytes downloaded.

    Note that the latter only happens if another plugin addin the
    image to be downloaded fully, whereas the former will happen
    in any case, and the inclusion of this addin will cause an
    HTTP request to be made.
    """

    depends = (handle_feed_images,)

    def __init__(self, max_size):
        self.max_size = max_size

    def _validate(self, size):
        if size > self.max_size:
            raise ImageError('image exceeds maximum size of %d' % self.max_size)

    def on_feed_image(self, feed, image_dict, image):
        self._validate(image.content_length)

    def on_feed_image_download_chunk(self, image, bytes_read):
        self._validate(bytes_read)


class feed_image_restrict_frequency(addins.base):
    """Ensures that an image is only updated every so-often.

    This primarily makes sense if you download the image, and want to
    avoid doing that everytime the feed is parsed, even though the image
    most likely has not changed. Especially when you are doing a lot
    of further processing (e.g. thumbnails), this is an addin you
    probably want to use.

    ``delta`` is the number of seconds that must pass since the last
    update of the image, before it is updated again. You may also pass
    a ``timedelta`` instance.
    """

    depends = (handle_feed_images,)

    def __init__(self, delta):
        self.delta = delta

    def get_columns(self):
        return {'feed': {'image_updated': (DateTime, [], {})}}

    def on_feed_image(self, feed, image_dict, image):
        delta = self.delta
        if not isinstance(self.delta, datetime.timedelta):
            delta = datetime.timedelta(seconds=self.delta)

        if feed.image_updated:
            if datetime.datetime.utcnow() - feed.image_updated < delta:
                # stop further processing
                self.log.warning('Feed #%d: image was last updated'
                        'recently enough' % (feed.id))
                return True

    def on_feed_image_updated(self, feed, image_dict, image):
        feed.image_updated = datetime.datetime.utcnow()


class feed_image_restrict_extensions(addins.base):
    """Restrict feed images to specific file extension.

    ``allowed`` should be an iterable of extension strings, without a
    dot prefix, e.g. ('png', 'gif'). If it is not specified, a default
    list of extension will be used.

    The extension does not necessarily need to be part of the url's
    filename. The addin also tries to defer it from the content type
    header, and if everything fails, the image content themselves.
    The latter means tha the image might need to be fully downloaded
    in some cases.

    If an extension cannot be determined, i.e. if the image content is
    invalid or in an unsupported format, it will be skipped.
    """

    depends = (handle_feed_images,)

    def __init__(self, allowed=None):
        self.allowed = allowed

    def on_feed_image(self, feed, image_dict, image):
        ext = image.extension
        allowed = self.allowed or ('png', 'gif', 'jpg', 'jpeg',)
        if ext and (not ext in allowed):
            # skip further processing
            self.log.debug('Feed #%d: image ignored, %s is not '
                'an allowed file extension' % (feed.id, ext))
            return True


class feed_image_restrict_mediatypes(addins.base):
    """Restrict feed images to specific content type headers.

    ``allowed`` should be an iterable of content type strings. If it
    is not specified, a default list of types will be used.

    If a contenet type is not available, the image is always allowed.
    """

    depends = (handle_feed_images,)

    def __init__(self, allowed=None):
        self.allowed = allowed

    def on_feed_image(self, feed, image_dict, image):
        ctype = image.content_type
        allowed = self.allowed or ('image/jpeg', 'image/png', 'image/gif',)
        if ctype and (not ctype in allowed):
            # skip further processing
            self.log.debug('Feed #%d: image ignored, %s is not '
                'an allowed content type' % (feed.id, ctype))
            return True


# TODO: rename to something storage/backend neutral
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

    You may also pass ``path`` as a ``os.path.join``-able iterable.

    Note that depending on how you store the image, you will later need
    the appropriate information to access it. For example, in the example
    above, the file extension is an unknown factor, and needs to be known
    for access. See ``collect_feed_image_data``, which can help you with
    this.
    """

    depends = (handle_feed_images,)

    def __init__(self, path, format=None):
        self.format = format
        if not isinstance(path, basestring):
            self.path = os.path.join(*path)
        else:
            self.path = path

    def _resolve_path(self, feed, image, extra=None):
        vars = {
            'model': feed.__class__.__name__.lower(),
            'model_id': feed.id,
            'filename': image.filename,
            'extension': image.extension,
        }
        if extra:
            vars.update(extra)
        return self.path % vars

    def on_update_feed_image(self, feed, image_dict, image):
        path = self._resolve_path(feed, image)
        image.save(path, format=self.format)


class feed_image_thumbnails(feed_image_to_filesystem):
    """Save thumbnail versions of feed images.

    May be used instead or in combination with ``feed_image_to_filesystem``.

    The required argument ``sizes`` is an iterable of 2-tuples,
    specifying the requested width/height values of the thumbnails.

    ``path`` and ``format`` work exactly like in
    ``feed_image_to_filesystem``, but you may use these additional
    format variables to specify the path:

        d width
        d height
        s size (e.g. "200x200")

    Requires PIL.
    """

    def __init__(self, sizes, path, format=None):
        self.sizes = sizes
        super(feed_image_thumbnails, self).__init__(path, format)

    def on_update_feed_image(self, feed, image_dict, image):
        for size in self.sizes:
            path = self._resolve_path(feed, image, {
                'width': size[0],
                'height': size[1],
                'size': ("%dx%d" % size),
            })
            thumb = make_thumbnail(image.pil, size[0], size[1], 'extend')
            thumb.save(path, format=self.format)

"""

class collect_feed_image_data(_base_data_collector):

    url title link
    extension
    filename

    # TODO: add a ``store_in_model`` option to use a separate model for this.
    pass

"""


def make_thumbnail(image, new_width, new_height, mode="crop"):
    """Create a thumbnail of a PIL image.

    Parameters:
        * ``new_width``, ``new_height``:
            Obviously, the wanted size of the image. Usually smaller
            than the orginal, although both directions work.

        * ``mode``:
            Supports "crop", "extend" and "fit".
                crop:       Keep propertions by cropping the image.
                extend:     Keep propertions by extending the canvas.
                fit:        Do not make an effort to keep proportions.

    # TODO: mode "extend" does not support enlarging of images.

    Partially based on code from this article:
        http://batiste.dosimple.ch/blog/2007-05-13-1/
    """

    from PIL import Image

    org_img = image

    if mode == "crop":
        org_width, org_height = org_img.size
        crop_ratio = new_width / float(new_height)
        image_ratio = org_width / float(org_height)
        if crop_ratio < image_ratio:
            # width needs to shrink
            top = 0
            bottom = org_width
            crop_width = int(org_width * crop_ratio)
            left = (org_width - crop_width) // 2
            right = left + crop_width
        else:
            # height needs to shrink
            left = 0
            right = org_width
            crop_height = int(org_width * crop_ratio)
            top = (org_height - crop_height) // 2
            bottom = top + crop_height
        # actually resize the image
        new_img = org_img.crop((left, top, right, bottom)).resize(
            (new_width,new_height), Image.ANTIALIAS)

    elif mode == "fit":
        new_img = org_img.resize((new_width,new_height), Image.ANTIALIAS)

    elif mode == 'extend':
        # we can use the builtin function for parts of the job
        thumb_img = org_img.copy()
        thumb_img.thumbnail((new_width, new_height), Image.ANTIALIAS)
        thumb_width, thumb_height = thumb_img.size
        # extend canvas whith whitespace
        new_img = Image.new("RGB", (new_width, new_height), "white")
        new_img.paste(thumb_img, ((new_width-thumb_width)//2, (new_height-thumb_height)//2))

    else:
        raise Exception("'%s' is not a supported mode" % mode)

    return new_img