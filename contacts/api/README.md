# Contact API

The API is public: reading and writing contacts requires no login or CSRF token.
Send request bodies with `Content-Type: application/json`. Responses use JSON,
except for successful deletion, which returns an empty body.

| Method | URL | Success response |
| --- | --- | --- |
| GET | `/api/contacts/` | `200`: all contacts as an array, without pagination |
| POST | `/api/contacts/` | `201`: the created contact |
| PUT | `/api/contacts/{id}/` | `200`: the updated contact |
| DELETE | `/api/contacts/{id}/` | `204`: no response body |

POST and PUT require all six editable fields:

```json
{
  "first_name": "Anna",
  "last_name": "Kowalska",
  "phone_number": "501 234 567",
  "email": "anna@example.com",
  "city": "Warszawa",
  "status": "new"
}
```

Status accepts an existing status code: `new`, `in_progress`, `lost`, or `outdated`.
It refers to a `ContactStatus` record; requests do not create new statuses.

Each returned contact contains these six fields plus read-only `id` and
`created_at`. Dates use `YYYY-MM-DD`. Phone numbers use the same normalization
as the contact form and CSV import, including Polish emergency short codes.
Phone numbers and email addresses must be unique.

Invalid data returns `400` with errors grouped by field. Malformed JSON also
returns `400`. Updating or deleting a missing contact returns `404`.
Unsupported operations, including GET and PATCH on an individual contact,
return `405`. PUT requires the full set of editable fields.
