web: gunicorn --worker-class eventlet -w 1 runserver:app
worker: celery -A app.tasks worker -c 3 -B --loglevel=info
