"""Default configuaration file.

Any value not specified in your own configuration will fallback to
this. Dict values are usually merged.
"""

# Database connection string - examples:
#   'sqlite:foo'
#   'mysql://user:pass@localhost/dbname'
DATABASE = None

# No addins are loaded.
ADDINS = []

# Allow only specific protocols; set to False to skip the check, in
# which case anything given as the feed url will be passed through to
# the parser library. That will potentiallly allow the filesystem, as
# well as parsing of the string directly.
ENFORCE_URI_SCHEMA = ['http', 'https']