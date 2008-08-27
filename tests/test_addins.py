from feedplatform import addins
from nose.tools import assert_raises

def test_giving_classes():
    """Test handling of class references in addin list.
    """

    class simple_addin(addins.base):
        pass

    class complex_addin(addins.base):
        def __init__(self, argument):
            pass

    # parameterless addins can be given as classes
    addins.reinstall((simple_addin,))

    # ones that do require options raise a clear error
    assert_raises(ValueError, addins.reinstall, (complex_addin,))

def test_log():
    """Make sure we can access and use self.log from subclasses.
    """

    class addin(addins.base):
        def foo(self):
            self.log.debug('foo called')

    addin().foo()