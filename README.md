# Contact Management

A Django application for managing contacts, importing CSV files, displaying city
weather, and exposing a public REST API.

## Environment configuration

Both startup options require a `.env` file in the project directory.

1. If `.env` does not exist, copy `.env.example` to `.env`.
2. Set `DJANGO_SECRET_KEY` in `.env` to a private random value. With Python
   installed, generate one with:

   ```sh
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```

Both options use port 8000, so run only one at a time.

## Run instruction

You can run the application with Docker or directly in a local Python environment.
Choose one of the options below after configuring `.env` as described above.

### Run with Docker

Start Docker Desktop with Linux containers enabled. From the project directory,
build and start the application:

```sh
docker compose up --build
```

Open <http://localhost:8000/>. The contact API is available at
<http://localhost:8000/api/contacts/>; see [API documentation](contacts/api/README.md).
Migrations run automatically before the server starts, including the initial
contact statuses.

This configuration uses Django's development server and serves the application's
static files. It is intended for local development and project review.

### Run without Docker

Install Python 3.12, then run the following commands from the project directory.
On macOS and Linux, use `python3` to create the environment if `python` is unavailable.

1. Create a virtual environment:

   ```sh
   python -m venv .venv
   ```

2. Activate it using the command for your shell.

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   macOS / Linux:

   ```sh
   source .venv/bin/activate
   ```

3. Install the dependencies:

   ```sh
   python -m pip install -r requirements.txt
   ```

4. Configure `.env` as described above, then create the database tables and
   initial contact statuses:

   ```sh
   python manage.py migrate
   ```

5. Start Django's development server:

   ```sh
   python manage.py runserver
   ```

Open <http://localhost:8000/>. The API is available at
<http://localhost:8000/api/contacts/>. Stop the server with `Ctrl+C`.

With the virtual environment activated, you can also create an administrator or
run the unit tests:

```sh
python manage.py createsuperuser
python manage.py test contacts
```

The local database is stored in `db.sqlite3`, and weather cache files are stored
in `.cache/`, unless `DJANGO_DATA_DIR` points to a different directory.

## Sample CSV import

[examples/contacts.csv](examples/contacts.csv) contains six fictional sample
contacts, including all four statuses, several phone formats, and a Polish
emergency number. The file uses UTF-8 with BOM and a semicolon separator.

On the contact list page, click **Importuj CSV** and select this file. All six
records can be imported into an empty database. Existing contacts with matching
phone numbers or email addresses are reported as duplicates and skipped.

## Data and configuration

Compose passes `.env` values into the container. The file is excluded from the
image, along with the local virtual environment, database, and weather cache.

SQLite and weather cache files are stored in the `contact_data` volume, mounted
at `/app/data`. Docker starts with a separate, empty database; the existing local
`db.sqlite3` is not imported automatically. Data survives container recreation and
`docker compose down`. Adding `--volumes` to that command deletes the stored data.

`DJANGO_DATA_DIR` selects the storage directory. Compose sets it to `/app/data`;
without this setting, running Django locally keeps its existing storage paths.

After changing application code or dependencies, rebuild with
`docker compose up --build`.

## Useful Docker commands

Stop the application:

```sh
docker compose down
```

Create an administrator while the application is running:

```sh
docker compose exec web python manage.py createsuperuser
```

Run the three unit tests:

```sh
docker compose exec web python manage.py test contacts
```
