'use strict';

const weatherTable = document.querySelector('[data-weather-url]');

if (weatherTable) {
    const cities = new Map();
    const numberFormat = new Intl.NumberFormat('pl-PL', {maximumFractionDigits: 1});

    // Rows for the same city share both the initial request and manual retries.
    for (const cell of weatherTable.querySelectorAll('[data-weather-city]')) {
        const city = cell.dataset.weatherCity;
        const key = city.trim().replace(/\s+/g, ' ').toLocaleLowerCase('pl-PL');
        if (!cities.has(key)) {
            cities.set(key, {city, cells: [], loading: false, failed: false, retryAt: 0});
        }
        cities.get(key).cells.push(cell);
    }

    function updateButtons(group) {
        const seconds = Math.max(0, Math.ceil((group.retryAt - Date.now()) / 1000));
        for (const cell of group.cells) {
            const button = cell.querySelector('[data-weather-retry]');
            button.hidden = !group.failed;
            button.disabled = group.loading || seconds > 0;
            button.textContent = group.loading ? 'Pobieranie…'
                : seconds > 0 ? `Ponów za ${seconds} s` : 'Ponów pobieranie';
        }
    }

    function render(group, result) {
        group.failed = result.status !== 'ok';
        group.retryAt = Date.now() + (result.retry_after || 0) * 1000;
        for (const cell of group.cells) {
            const values = cell.querySelector('[data-weather-values]');
            const status = cell.querySelector('[data-weather-status]');
            values.replaceChildren();
            if (result.weather) {
                const weather = result.weather;
                const metrics = [
                    ['🌡', 'Temperatura', weather.temperature, '°C'],
                    ['💧', 'Wilgotność', weather.humidity, '%'],
                    ['💨', 'Prędkość wiatru', weather.wind_speed, 'km/h'],
                ];
                for (const [icon, label, value, unit] of metrics) {
                    const metric = document.createElement('span');
                    metric.className = 'd-inline-block me-2';
                    metric.textContent = `${icon} ${numberFormat.format(value)} ${unit}`;
                    metric.title = label;
                    metric.setAttribute('aria-label', `${label}: ${numberFormat.format(value)} ${unit}`);
                    values.append(metric);
                }
                const timestamp = new Date(weather.time).toLocaleString('pl-PL');
                status.textContent = result.stale
                    ? `Ostatnie dostępne dane z ${timestamp}. ${result.message}`
                    : `Dane z ${timestamp}`;
            } else {
                status.textContent = result.message || 'Pogoda jest niedostępna.';
            }
        }
        updateButtons(group);
    }

    async function loadWeather(groups) {
        const url = new URL(weatherTable.dataset.weatherUrl, window.location.origin);
        for (const group of groups) {
            group.loading = true;
            url.searchParams.append('city', group.city);
            for (const cell of group.cells) {
                cell.querySelector('[data-weather-status]').textContent = 'Pobieranie pogody…';
            }
            updateButtons(group);
        }

        const controller = new AbortController();
        // Allow time for sequential geocoding and API retries within the whole batch.
        const timeout = setTimeout(() => controller.abort(), 90000);
        try {
            const response = await fetch(url, {signal: controller.signal, headers: {Accept: 'application/json'}});
            if (!response.ok) {
                throw new Error('Weather request failed.');
            }
            const data = await response.json();
            for (const group of groups) {
                render(group, data.cities[group.city]);
            }
        } catch {
            for (const group of groups) {
                group.failed = true;
                group.retryAt = Date.now() + 5000;
                for (const cell of group.cells) {
                    const hasWeather = cell.querySelector('[data-weather-values]').childElementCount > 0;
                    cell.querySelector('[data-weather-status]').textContent = hasWeather
                        ? 'Nie udało się odświeżyć pogody. Widoczne dane mogą być nieaktualne.'
                        : 'Nie udało się pobrać pogody. Spróbuj ponownie.';
                }
            }
        } finally {
            clearTimeout(timeout);
            for (const group of groups) {
                group.loading = false;
                updateButtons(group);
            }
        }
    }

    for (const group of cities.values()) {
        for (const cell of group.cells) {
            cell.querySelector('[data-weather-retry]').addEventListener('click', () => {
                if (!group.loading && Date.now() >= group.retryAt) {
                    loadWeather([group]);
                }
            });
        }
    }

    setInterval(() => {
        for (const group of cities.values()) {
            if (group.failed) updateButtons(group);
        }
    }, 1000);

    // Fetch at most three cities per request to limit sequential geocoding time.
    async function loadInitialWeather() {
        const groups = [...cities.values()];
        for (let index = 0; index < groups.length; index += 3) {
            await loadWeather(groups.slice(index, index + 3));
        }
    }

    loadInitialWeather();
}
