from feedplatform.management import BaseCommand
from feedplatform import db

class Command(BaseCommand):
    help = 'Show defined models and fields.'

    def handle(self, *args, **options):
        for model in db.models:

            header = model.__name__
            if model.__name__.lower() != model.__storm_table__.lower():
                header += " (-> %s)" %  model.__storm_table__
            print header

            # ``_storm_columns`` seems to be the only place we can get
            # access to to the originally defined ``Property`` objects
            # (instead of the wrapped ``PropertyColumn``), and thus to
            # the field type (= the class name).
            # Fortunately, it is also seems to be the best solution,
            # as opposed to say using ``dir(model)`` to get the fields.
            for column, property in model._storm_columns.iteritems():
                attr_name = column._detect_attr_name(model)
                line = "    %s" % attr_name
                line += ": %s" % column.__class__.__name__
                if property.name and attr_name != property.name:
                    line += ' -> %s' % property.name
                print line

            print ""