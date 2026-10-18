import csv
from io import StringIO

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import translation

from .forms import ContactForm
from .models import ContactStatus

CSV_HEADERS = ('first_name', 'last_name', 'phone_number', 'email', 'city', 'status')


def _read_csv(uploaded_file):
    try:
        text = uploaded_file.read().decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise ValidationError('Zapisz plik CSV w kodowaniu UTF-8.') from error

    lines = text.splitlines(keepends=True)
    header_start = next(
        (index for index, line in enumerate(lines)
         if line.strip() and not line.lstrip().startswith('#')),
        None,
    )
    if header_start is None:
        raise ValidationError('Plik CSV jest pusty lub zawiera tylko instrukcje.')

    # Only leading instructions are skipped; quoted multiline data stays intact.
    content = ''.join(lines[header_start:])
    delimiter = ';' if ';' in lines[header_start] else ','
    reader = csv.reader(StringIO(content, newline=''), delimiter=delimiter, strict=True)
    rows = []
    try:
        headers = [header.strip().lower() for header in next(reader)]
        if len(headers) != len(CSV_HEADERS) or set(headers) != set(CSV_HEADERS):
            raise ValidationError(
                'Plik musi zawierać dokładnie następujące nagłówki: '
                + ', '.join(CSV_HEADERS) + '.'
            )

        while True:
            row_number = header_start + reader.line_num + 1
            try:
                values = next(reader)
            except StopIteration:
                break
            if values and (len(values) > 1 or any(value.strip() for value in values)):
                rows.append((row_number, values))
    except csv.Error as error:
        raise ValidationError(
            f'Błędna struktura CSV w pobliżu wiersza {header_start + reader.line_num}. '
            'Sprawdź separator i cudzysłowy.'
        ) from error

    if not rows:
        raise ValidationError('Plik zawiera nagłówki, ale nie zawiera kontaktów.')
    return headers, rows


def import_contacts(uploaded_file):
    """Import valid contacts and report skipped rows with their source line numbers."""
    # Reject malformed CSV syntax before saving; validate contact data per row.
    headers, rows = _read_csv(uploaded_file)
    status_ids = {}
    for status in ContactStatus.objects.all():
        status_ids[status.name.casefold()] = status.pk
        status_ids[status.get_name_display().casefold()] = status.pk

    result = {'imported_count': 0, 'skipped_count': 0, 'errors': []}
    for row_number, values in rows:
        if len(values) != len(headers):
            result['errors'].append({
                'row_number': row_number,
                'messages': [f'Nieprawidłowa liczba kolumn: oczekiwano {len(headers)}, otrzymano {len(values)}.'],
            })
            continue

        data = dict(zip(headers, (value.strip() for value in values)))
        status_name = ' '.join(data['status'].split()).casefold()
        if status_name:
            data['status'] = status_ids.get(status_name, 'invalid_status')

        # Reuse form validation, including normalized phone and unique field checks.
        with translation.override('pl'):
            form = ContactForm(data)
            if not form.is_valid():
                errors = []
                for field_name, field_errors in form.errors.items():
                    label = form.fields[field_name].label if field_name in form.fields else 'Kontakt'
                    errors.extend(f'{label}: {message}' for message in field_errors)
                result['errors'].append({'row_number': row_number, 'messages': errors})
                continue

        try:
            # Isolate each save so a concurrent duplicate does not block later rows.
            with transaction.atomic():
                form.save()
        except IntegrityError:
            result['errors'].append({
                'row_number': row_number,
                'messages': ['Nie udało się zapisać kontaktu. Dane mogły się zmienić podczas importu.'],
            })
        else:
            result['imported_count'] += 1

    result['skipped_count'] = len(result['errors'])
    return result


def create_csv_template():
    content = StringIO(newline='')
    # A BOM lets Excel recognize UTF-8, including Polish characters.
    content.write('\ufeff')
    content.write('# Wypełnij wszystkie pola. Zachowaj nagłówki i zapisz jako CSV UTF-8.\r\n')
    content.write(
        '# Zastąp przykładowy wiersz. Kolumnę phone_number ustaw jako tekst. '
        'Bez prefiksu kraju przyjmujemy +48. '
        'Status: nowy / w trakcie / zagubiony / nieaktualny.\r\n'
    )
    content.write('# Polskie numery alarmowe, np. 112 i 997, podaj bez prefiksu kraju.\r\n')
    writer = csv.writer(content, delimiter=';', lineterminator='\r\n')
    writer.writerow(CSV_HEADERS)
    writer.writerow(('Jan', 'Kowalski', '+48500100200', 'jan.kowalski@example.com', 'Warszawa', 'nowy'))
    return content.getvalue()
