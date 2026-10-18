"""Fetch city weather while sharing cached results and API limits locally."""

import hashlib
import json
import logging
import math
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import caches
from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)

WEATHER_TTL = 30 * 60
COORDINATES_TTL = 30 * 24 * 60 * 60
STALE_TTL = 24 * 60 * 60
NOT_FOUND_TTL = 5 * 60
ERROR_TTL = 60
REQUEST_TIMEOUT = 5
MAX_ATTEMPTS = 3


class WeatherAPIError(Exception):
    def __init__(self, message, retry_after=ERROR_TTL):
        super().__init__(message)
        self.retry_after = retry_after


def _city_key(city):
    normalized = ' '.join(city.split()).casefold()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def _retry_after(value):
    """Retry-After can contain either seconds or an HTTP date."""
    if not value:
        return 0
    try:
        return max(0, int(value))
    except ValueError:
        try:
            return max(0, math.ceil(parsedate_to_datetime(value).timestamp() - time.time()))
        except (TypeError, ValueError, OverflowError):
            return 0


def _provider_error(provider, message, delay=ERROR_TTL):
    caches['weather'].set(
        f'provider:{provider}',
        {'message': message, 'retry_at': time.time() + delay},
        timeout=delay,
    )
    return WeatherAPIError(message, delay)


def _request_json(provider, url, parameters):
    cache = caches['weather']
    failure = cache.get(f'provider:{provider}')
    if failure and failure['retry_at'] > time.time():
        raise WeatherAPIError(
            failure['message'], math.ceil(failure['retry_at'] - time.time()),
        )

    request = Request(
        f'{url}?{urlencode(parameters)}',
        headers={'User-Agent': settings.WEATHER_USER_AGENT, 'Accept': 'application/json'},
    )
    for attempt in range(MAX_ATTEMPTS):
        started_at = time.monotonic()
        delay = 2 ** (attempt + 1)
        retryable = True
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                return json.load(response)
        except HTTPError as error:
            retryable = error.code in (429, 500, 502, 503, 504)
            delay = max(delay, _retry_after(error.headers.get('Retry-After')))
            logger.warning('%s returned HTTP %s (attempt %s)', provider, error.code, attempt + 1)
            error.close()
        except (URLError, OSError, HTTPException, ValueError) as error:
            logger.warning('%s request failed (%s, attempt %s)', provider, type(error).__name__, attempt + 1)
        finally:
            if provider == 'geocoding':
                # Keep Nominatim below one request per second, including after errors.
                # The shared lock stays held during the pause across local processes.
                time.sleep(max(0, 1.1 - (time.monotonic() - started_at)))

        # Long server delays become a cooldown instead of blocking a Django worker.
        if not retryable or attempt == MAX_ATTEMPTS - 1 or delay > 4:
            raise _provider_error(
                provider, 'Serwis pogodowy jest chwilowo niedostępny.', max(ERROR_TTL, delay),
            )
        time.sleep(delay)


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Expected a finite number.')
    return value


def _coordinates(city, key):
    cache = caches['weather']
    coordinates = cache.get(f'coordinates:{key}')
    if coordinates is not None:
        return coordinates
    missing_until = cache.get(f'missing:{key}')
    if missing_until:
        raise WeatherAPIError('Nie znaleziono miasta.', max(1, math.ceil(missing_until - time.time())))

    data = _request_json('geocoding', settings.WEATHER_GEOCODING_URL, {
        'q': ' '.join(city.split()), 'format': 'json', 'limit': 1,
    })
    if data == []:
        cache.set(f'missing:{key}', time.time() + NOT_FOUND_TTL, timeout=NOT_FOUND_TTL)
        raise WeatherAPIError('Nie znaleziono miasta.', NOT_FOUND_TTL)
    try:
        latitude = _number(float(data[0]['lat']))
        longitude = _number(float(data[0]['lon']))
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError('Coordinates outside valid range.')
    except (KeyError, IndexError, TypeError, ValueError):
        raise _provider_error('geocoding', 'Nie udało się odczytać położenia miasta.')
    coordinates = (latitude, longitude)
    cache.set(f'coordinates:{key}', coordinates, timeout=COORDINATES_TTL)
    return coordinates


def _forecasts(coordinates):
    data = _request_json('forecast', settings.WEATHER_FORECAST_URL, {
        'latitude': ','.join(str(point[0]) for point in coordinates),
        'longitude': ','.join(str(point[1]) for point in coordinates),
        'current': 'temperature_2m,relative_humidity_2m,wind_speed_10m',
        'temperature_unit': 'celsius', 'wind_speed_unit': 'kmh', 'timeformat': 'unixtime',
    })
    if isinstance(data, dict):
        data = [data]
    try:
        if len(data) != len(coordinates):
            raise ValueError('Unexpected forecast count.')
        forecasts = []
        for item in data:
            current = item['current']
            temperature = _number(current['temperature_2m'])
            humidity = _number(current['relative_humidity_2m'])
            wind_speed = _number(current['wind_speed_10m'])
            timestamp = _number(current['time'])
            if not (0 <= humidity <= 100 and wind_speed >= 0):
                raise ValueError('Invalid forecast values.')
            forecasts.append({
                'temperature': temperature, 'humidity': humidity, 'wind_speed': wind_speed,
                'time': datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
            })
        return forecasts
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        raise _provider_error('forecast', 'Nie udało się odczytać danych pogodowych.')


def _error_result(key, error):
    previous_weather = caches['weather'].get(f'last-weather:{key}')
    return {
        'status': 'error', 'message': str(error), 'retry_after': error.retry_after,
        'weather': previous_weather, 'stale': previous_weather is not None,
    }


def get_city_weather(cities):
    """Return cached weather first; serialize cache misses across local workers."""
    cache = caches['weather']
    results = {}
    pending = {}
    for city in cities:
        key = _city_key(city)
        weather = cache.get(f'weather:{key}')
        if weather is not None:
            results[city] = {'status': 'ok', 'weather': weather, 'stale': False}
        else:
            pending[city] = key
    if not pending:
        return results

    try:
        # One shared lock also prevents duplicate requests for the same city.
        with FileLock(settings.WEATHER_LOCK_PATH, timeout=0):
            locations = {}
            for city, key in pending.items():
                weather = cache.get(f'weather:{key}')
                if weather is not None:
                    results[city] = {'status': 'ok', 'weather': weather, 'stale': False}
                    continue
                try:
                    coordinates = _coordinates(city, key)
                except WeatherAPIError as error:
                    results[city] = _error_result(key, error)
                else:
                    locations.setdefault(coordinates, []).append((city, key))

            if locations:
                try:
                    forecasts = _forecasts(list(locations))
                except WeatherAPIError as error:
                    for city_entries in locations.values():
                        for city, key in city_entries:
                            results[city] = _error_result(key, error)
                else:
                    for city_entries, weather in zip(locations.values(), forecasts):
                        for city, key in city_entries:
                            cache.set(f'weather:{key}', weather, timeout=WEATHER_TTL)
                            cache.set(f'last-weather:{key}', weather, timeout=STALE_TTL)
                            results[city] = {'status': 'ok', 'weather': weather, 'stale': False}
    except Timeout:
        for city, key in pending.items():
            results[city] = _error_result(key, WeatherAPIError('Trwa pobieranie pogody. Spróbuj ponownie.', 3))

    return results
