import re

import phonenumbers
from django.core.exceptions import ValidationError

# Short codes are restricted to Polish emergency numbers listed by UKE.
# https://bip.uke.gov.pl/numeracja/tablice-numerow-kierowania-alarmowego-nka,4,32.html
POLISH_EMERGENCY_NUMBERS = (
    '112', '984', '985', '986', '987', '991', '992',
    '993', '994', '995', '996', '997', '998', '999',
)


def normalize_phone_number(value):
    number = re.sub(r'[\s()-]', '', value)
    error_message = 'Podaj prawidłowy numer telefonu lub polski numer alarmowy, np. 112.'
    if not re.fullmatch(r'(?:\+|00)?[0-9]+', number):
        raise ValidationError(error_message, code='invalid_phone_number')

    # Keep Polish emergency short codes unchanged instead of prepending +48.
    if number in POLISH_EMERGENCY_NUMBERS:
        return number

    if number.startswith('00'):
        number = '+' + number[2:]

    try:
        # PL supplies the country code only when no international prefix is given.
        parsed_number = phonenumbers.parse(number, 'PL')
    except phonenumbers.NumberParseException as error:
        raise ValidationError(error_message, code='invalid_phone_number') from error

    if not phonenumbers.is_valid_number(parsed_number):
        raise ValidationError(error_message, code='invalid_phone_number')

    # One storage format makes equivalent numbers share the same unique value.
    return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
