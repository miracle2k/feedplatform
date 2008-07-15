from feedplatform.management import BaseCommand
from feedplatform import db

class Command(BaseCommand):
    def handle(self, *args, **options):
        for model in db.models.values():

            print model.__name__

            # ``_storm_columns`` seems to be the only place we can get
            # access to to the originally defined ``Property`` objects
            # (instead of the wrapped ``PropertyColumn``), and thus to
            # the field type (= the class name).
            # Fortunately, it is also seems to be the best solution,
            # as opposed to say using ``dir(model)`` to get the fields.
            for column, property in model._storm_columns.iteritems():
                print "    %(name)s: %(type)s" % {
                    'name': property.name,
                    'type': column.__class__.__name__
                }
