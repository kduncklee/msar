# Database Fixtures

This directory contains Django fixture data for seeding default configuration tables.

## Available Fixtures

- **`callout_response_options.json`**: Default `CalloutResponseOption` records covering both `promised_time` (`10-8`, `10-19`, `10-7`) and `stated_time` (`Yes`, `No`, `Deploying`, `Returned`) workflows.

## Loading the Fixture

After pulling this branch and running migrations, load the fixture into your database with:

```bash
python manage.py migrate
python manage.py loaddata callout_response_options
```

*(If using the local virtual environment: `./venv/bin/python manage.py loaddata callout_response_options`)*

## Updating / Re-exporting the Fixture

If you modify the Callout Response Options in the Django Admin (`/admin/main/calloutresponseoption/`) and want to save your changes back to the fixture file:

```bash
python manage.py dumpdata main.CalloutResponseOption --indent 2 --output main/fixtures/callout_response_options.json
```
