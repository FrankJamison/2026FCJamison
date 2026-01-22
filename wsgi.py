"""WSGI entrypoint for production servers (Gunicorn, mod_wsgi, etc)."""

from app import app as application
