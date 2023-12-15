#!/bin/sh

cd $APP_PATH

python manage.py migrate

python manage.py qcluster &

PYTHONUNBUFFERED=TRUE \
    gunicorn --workers 4 --threads 1 --timeout 30 \
    --enable-stdio-inheritance --capture-output \
    --access-logfile '/home/LogFiles/gunicorn-access.log' \
    --error-logfile '/home/LogFiles/gunicorn-error.log' \
    --bind=0.0.0.0:8000 \
    --chdir=. \
    bamru_net.wsgi \
    -c deploy/gunicorn.config.py
