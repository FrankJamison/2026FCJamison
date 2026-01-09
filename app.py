import os

from __init__ import app
from homeViews import *

if __name__ == '__main__':
    debug = (os.getenv('FLASK_DEBUG') or '').strip().lower() in {
        '1', 'true', 'yes', 'on'}
    host = (os.getenv('HOST') or '127.0.0.1').strip()
    port = int((os.getenv('PORT') or '5000').strip() or '5000')
    app.run(host=host, port=port, debug=debug)
