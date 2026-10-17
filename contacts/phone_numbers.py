import re

import phonenumbers
from django.core.exceptions import ValidationError


def normalize_phone_number(value):
    number = re.sub(r'[\s()-]', '', value)
    error_message = 'Podaj prawidłowy numer telefonu, np. +48500100200.'
    if not re.fullmatch(r'(?:\+|00)?[0-9]+', number):
        raise ValidationError(error_message, code='invalid_phone_number')

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
