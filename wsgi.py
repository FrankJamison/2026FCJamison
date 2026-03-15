"""WSGI entrypoint for production servers (Gunicorn, mod_wsgi, etc)."""

# Import the Flask app and route registrations.
from __init__ import app as application
