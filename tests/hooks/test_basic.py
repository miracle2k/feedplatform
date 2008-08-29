"""General tests of the ``hooks`` module.

Each specific hook has it's own test(s).
"""

from nose.tools import assert_raises
from feedplatform import hooks


def test_validity():
    # invalid identifers result in exceptions
    assert_raises(KeyError, hooks.add_callback, 'worldpeace', lambda: None)
    assert_raises(KeyError, hooks.trigger, 'worldpeace')
    assert_raises(KeyError, hooks.any, 'worldpeace')

    # can't register the same function twice
    def foo(): pass
    hooks.add_callback('alien_invasion', foo)
    assert_raises(ValueError, hooks.add_callback, 'alien_invasion', foo)

    # valid identifers work
    hooks.reset()
    hooks.add_callback('alien_invasion', lambda x: x)
    assert hooks.trigger('alien_invasion', [5]) == 5


def test_any():
    """Test the any() function.
    """
    hooks.reset()
    assert hooks.any('alien_invasion') == False
    hooks.add_callback('alien_invasion', lambda: None)
    assert hooks.any('alien_invasion') == True

    # invalid hook names raise an error
    assert_raises(KeyError, hooks.any, 'worldpeace')


def test_multiple():
    """Test handling of multiple callbacks for a hook.
    """

    hooks.reset()
    # making this an attribute of a global avoids all kinds of scoping issues
    test_multiple.counter = 0
    def mkinc():   # can't use same callback twice
        def inc():
            test_multiple.counter += 1;
            return 42
        return inc

    hooks.add_callback('alien_invasion', mkinc())
    hooks.add_callback('alien_invasion', mkinc())
    hooks.add_callback('alien_invasion', mkinc())

    # by default, the first successfull callback returns
    test_multiple.counter = 0
    assert hooks.trigger('alien_invasion') == 42
    assert test_multiple.counter == 1

    # we can forcefully go through all callbacks (and get None back)
    test_multiple.counter = 0
    assert hooks.trigger('alien_invasion', all=True) == None
    assert test_multiple.counter == 3


def test_priority():
    # fifo: without a priority, the callback added first is called first
    hooks.reset()
    hooks.add_callback('alien_invasion', lambda: 1)
    hooks.add_callback('alien_invasion', lambda: 2)
    hooks.add_callback('alien_invasion', lambda: 3)
    assert hooks.trigger('alien_invasion') == 1

    # but callback priorization works as well
    hooks.reset()
    hooks.add_callback('alien_invasion', lambda: 'p10', priority=10)
    hooks.add_callback('alien_invasion', lambda: 'p20', priority=20)
    hooks.add_callback('alien_invasion', lambda: 'p5', priority=5)
    assert hooks.trigger('alien_invasion') == 'p20'


def test_custom():
    """Test custom, non-default hooks.
    """

    # this fails, hook doesn't yet exist
    assert_raises(Exception, hooks.add_callback, 'i_love_you', lambda: None)
    assert_raises(Exception, hooks.trigger, 'i_love_you')

    # after we register the hook, it works
    hooks.register('i_love_you')
    hooks.add_callback('i_love_you', lambda: None)
    hooks.trigger('i_love_you')

    # registering the same hook multiple times is a no-op
    hooks.register('i_love_you')
    hooks.register('i_love_you')


def test_reset():
    # reset() was already used throughout previous tests,
    # but for good measure, do it specifically.

    # callback is no longer registered after a reset
    hooks.add_callback('alien_invasion', lambda: 42)
    hooks.reset()
    assert hooks.trigger('alien_invasion') == None

    # custom hook is gone after a reset
    hooks.register('i_love_you')
    hooks.reset()
    assert_raises(Exception, hooks.add_callback, 'i_love_you', lambda: None)