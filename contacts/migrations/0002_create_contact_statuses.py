from django.db import migrations


def create_contact_statuses(apps, schema_editor):
    ContactStatus = apps.get_model('contacts', 'ContactStatus')
    database_alias = schema_editor.connection.alias

    for name in ('new', 'in_progress', 'lost', 'outdated'):
        ContactStatus.objects.using(database_alias).get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ('contacts', '0001_initial'),
    ]

    operations = [
        # Preserve statuses on rollback because existing contacts may use them.
        migrations.RunPython(create_contact_statuses, migrations.RunPython.noop),
    ]
