from feedplatform import test as feedev

def test():
    """At least a single pass is required.
    """
    try:
        feedev.testmod()
    except Exception, e:
        assert "has no passes" in str(e)
    else:
        raise AssertionError("testmod() did not fail on pass-less module")