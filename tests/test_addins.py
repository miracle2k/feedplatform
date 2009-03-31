from feedplatform import addins
from feedplatform import management
from nose.tools import assert_raises


def test_log():
    """Make sure we can access and use self.log from
    ``addins.base`` subclasses.
    """

    class addin(addins.base):
        def foo(self):
            self.log.debug('foo called')

    addin().foo()


def test_giving_classes():
    """Test handling of class references in addin list.
    """

    class simple_addin1(addins.base):
        pass

    class simple_addin2(addins.base):
        def __init__(self, x=1, y=2, *args, **kwargs):
            pass

    class complex_addin(addins.base):
        def __init__(self, argument):
            pass

    # parameterless addins can be given as classes
    addins.reinstall((simple_addin1,))
    # parameters that have defaults don't bother us either
    addins.reinstall((simple_addin2,))

    # ones that do require options raise a clear error
    assert_raises(ValueError, addins.reinstall, (complex_addin,))

    # [bug] since it's a method, the self argument doesn't stand
    # in the way of automatic construction.
    class self_addin(addins.base):
        def __init__(self): pass
    addins.reinstall((self_addin,))


def test_dependencies():
    """Test addin dependency handling.
    """

    # the simple case
    class a(addins.base): pass
    class b(addins.base):
        depends = (a,)
    assert len(addins.reinstall((b,))) == 2

    # if the dependency was explicitely specified, that's fine too
    assert len(addins.reinstall((b,a))) == 2

    # test a couple recursive dependency scenarios
    class c(addins.base):
        depends = (b,)
    assert len(addins.reinstall((c,))) == 3
    assert len(addins.reinstall((c,b))) == 3
    assert len(addins.reinstall((a,c))) == 3
    class d(addins.base):
        depends = (b,)
    assert len(addins.reinstall((c,d))) == 4

    # a dependecy can't be a class that can't be constructed
    class x(addins.base):
        def __init__(self, x): pass
    class y(addins.base):
        depends = (x,)
    assert_raises(ValueError, addins.reinstall, (y(),))

    # dependencies can be given as instances, though
    class z(addins.base):
        depends = (x("foobar"),)
    addins.reinstall((z(),))


def test_dynamic_dependencies():
    """Dependency can be dynamic, e.g. chosen by an  addin instance.
    """

    class a(addins.base): pass
    class b(addins.base):
        depends = ()
        def __init__(self, depend=False):
            if depend:
                self.depends = (a,)

    assert len(addins.reinstall((b,))) == 1
    # once we pass True, the addin requires a dependency
    assert len(addins.reinstall((b(True),))) == 2


def test_dependency_order():
    """Make sure depending addins are installed in the right order.
    """

    def clslist_for(*list):
        return [type(a) for a in addins.reinstall(list)]

    # dependencies are inserted at the right position
    class a(addins.base): pass
    class b(addins.base): depends = (a,)
    assert clslist_for(b) == [a,b]
    # even if they are recursive
    class c(addins.base): depends = (a,b)
    assert clslist_for(c) == [a,b,c]
    # even if non-dependency addins are mixed in
    class e(addins.base): pass
    assert clslist_for(e,b) == [e,a,b]

    # However, if the user manually specifies addins that
    # are depended on by others, and does so in the "wrong"
    # order, this is accepted, and no attempt is made to fix
    # it or fail. This is done because an addin may in fact
    # be specified multiple times, and this raises some
    # questions with regard to how dependencies are handled,
    # anyway, and we wanted to keep things simple.
    assert clslist_for(b,a) == [b,a]
    assert clslist_for(c,a) == [b,c,a]


def test_commands():
    """Addins may provide commands."""

    class FooCommand(management.NoArgsCommand):
        def handle_noargs(self, **options):
            return 1

    class foo(addins.base):
        def get_commands(self):
            return {
                'foo': FooCommand,
            }

    addins.reinstall((foo,))

    management.call_command('foo')