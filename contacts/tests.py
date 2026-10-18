from unittest.mock import patch
from urllib.error import HTTPError

from django.core.cache.backends.locmem import LocMemCache
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .phone_numbers import normalize_phone_number
from .weather import WeatherAPIError, _request_json


class PhoneNumberTests(SimpleTestCase):
    def test_normalizes_phone_number_formats(self):
        cases = {
            '501234567': '+48501234567',
            '501 234 567': '+48501234567',
            '+48501234567': '+48501234567',
            '0048501234567': '+48501234567',
            '+44 20 7946 0018': '+442079460018',
        }

        for number, expected in cases.items():
            with self.subTest(number=number):
                self.assertEqual(normalize_phone_number(number), expected)

    def test_accepts_only_polish_emergency_short_codes(self):
        for number in ('112', '997'):
            with self.subTest(number=number):
                self.assertEqual(normalize_phone_number(number), number)

        for number in ('911', '+48112'):
            with self.subTest(number=number):
                with self.assertRaises(ValidationError):
                    normalize_phone_number(number)


class WeatherRequestTests(SimpleTestCase):
    def test_retry_after_prevents_requests_during_cooldown(self):
        # Keep test state separate from the application's file-based weather cache.
        cache = LocMemCache(self.id(), {})
        cache.clear()
        self.addCleanup(cache.clear)
        url = 'https://weather.example/forecast'
        error = HTTPError(url, 429, 'Too Many Requests', {'Retry-After': '120'}, None)

        # Simulate both the HTTP response and elapsed time without network access or waits.
        with (
            patch('contacts.weather.caches', {'weather': cache}),
            patch('contacts.weather.urlopen', side_effect=error) as request,
            patch('contacts.weather.time.time', return_value=1000) as clock,
            patch('contacts.weather.time.sleep') as sleep,
            self.assertLogs('contacts.weather', level='WARNING'),
        ):
            with self.assertRaises(WeatherAPIError) as first_failure:
                _request_json('forecast', url, {})

            self.assertEqual(first_failure.exception.retry_after, 120)
            request.assert_called_once()

            clock.return_value = 1060
            with self.assertRaises(WeatherAPIError) as second_failure:
                _request_json('forecast', url, {})

            self.assertEqual(second_failure.exception.retry_after, 60)
            request.assert_called_once()
            sleep.assert_not_called()
