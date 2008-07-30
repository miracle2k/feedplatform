"""General tests of the ``hooks`` module.

Each specific hook has it's own test(s).
"""

from nose.tools import assert_raises
from feedplatform import hooks


def test_invalid():
    # invalid identifers result in exceptions
    assert_raises(Exception, hooks.add_callback, 'worldpeace', lambda: None)
    assert_raises(Exception, hooks.trigger, 'worldpeace')

    # can't register the same function twice
    def foo(): pass
    hooks.add_callback('alien_invasion', foo)
    assert_raises(Exception, hooks.add_callback, 'worldpeace', foo)

def test_valid():
    # valid identifers work
    hooks.reset()
    hooks.add_callback('alien_invasion', lambda x: x)
    assert hooks.trigger('alien_invasion', [5]) == 5

def test_multiple():
    # test handling of multiple callbacks for a hook

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

def test_reset():
    # reset() was already used throughout previous tests,
    # but for good measure, do it specifically.
    hooks.add_callback('alien_invasion', lambda: 42)
    hooks.reset()
    assert hooks.trigger('alien_invasion') == None