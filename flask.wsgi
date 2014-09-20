import logging,sys
from logging.handlers import RotatingFileHandler
from logging import Formatter
from os.path import dirname
script_path = dirname(__file__)
sys.path.append(script_path)
from hummedia import app as application

# see http://flask.pocoo.org/docs/0.10/errorhandling/
file_handler=RotatingFileHandler(script_path+'/flask_err.log')
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
))

application.logger.addHandler(file_handler)
