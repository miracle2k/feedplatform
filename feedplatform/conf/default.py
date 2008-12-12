"""Default configuaration file.

Any value not specified in your own configuration will fallback to
this. Dict values are usually merged.
"""

# Database connection string - examples:
#   'sqlite:foo'
#   'mysql://user:pass@localhost/dbname'
DATABASE = None

# No addins are loaded.
ADDINS = ()

# Allows remapping of model and field names on the table/column level
# to match the desired database scheme.
TABLES = {}

# User agent string when needed, e.g. HTTP interactions.
USER_AGENT = 'FeedPlatform Python Library'

# Allow only specific protocols; set to False to skip the check, in
# which case anything given as the feed url will be passed through to
# the parser library. That will potentiallly allow the filesystem, as
# well as parsing of the string directly.
ENFORCE_URI_SCHEME = ('http', 'https',)

# Handlers that will be passed to urllib2 when fetching feeds. This,
# among other things, allows you to add support for new protocols.
# Note that you then may have to update ENFORCE_URI_SCHEME as well.
URLLIB2_HANDLERS = ()

# The timeout to use for connections in floating seconds.
SOCKET_TIMEOUT = 10