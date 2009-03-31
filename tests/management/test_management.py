from feedplatform import management


def test_command_return_value():
    """"[bug] Check the return value is passed through ok."""

    class FooCommand(management.NoArgsCommand):
        def handle_noargs(self, **options):
            pass

    print  management.call_command(FooCommand())
    assert management.call_command(FooCommand()) == 0

# TODO: test the command return value is printed