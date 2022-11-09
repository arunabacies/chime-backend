#!/bin/sh
#flask db upgrade
gunicorn -b :5000 --access-logfile - --error-logfile ---timeout=300 runserver:app
