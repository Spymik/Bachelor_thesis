"""WSGI entrypoint for production servers (gunicorn, waitress, uWSGI).

    gunicorn --config gunicorn.conf.py wsgi:app
"""

from app import create_app

app = create_app()
