import re

import phonenumbers
from django.db import migrations


def normalize_phone_numbers(apps, schema_editor):
    Contact = apps.get_model('contacts', 'Contact')
    contacts = Contact.objects.using(schema_editor.connection.alias)
    seen_numbers = {}
    updates = []

    for contact_id, value in contacts.values_list('pk', 'phone_number'):
        number = re.sub(r'[\s()-]', '', value)
        if not re.fullmatch(r'(?:\+|00)?[0-9]+', number):
            continue
        try:
            parsed_number = phonenumbers.parse(number, 'PL')
        except phonenumbers.NumberParseException:
            continue
        if not phonenumbers.is_valid_number(parsed_number):
            continue

        normalized = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        if normalized in seen_numbers:
            raise RuntimeError(
                f'Contacts {seen_numbers[normalized]} and {contact_id} have the same '
                'phone number after normalization. Resolve the duplicate before migrating.'
            )
        seen_numbers[normalized] = contact_id
        if normalized != value:
            updates.append((contact_id, normalized))

    for contact_id, normalized in updates:
        contacts.filter(pk=contact_id).update(phone_number=normalized)


class Migration(migrations.Migration):
    dependencies = [
        ('contacts', '0003_alter_contact_email_alter_contact_phone_number'),
    ]

    operations = [
        migrations.RunPython(normalize_phone_numbers, migrations.RunPython.noop),
    ]
