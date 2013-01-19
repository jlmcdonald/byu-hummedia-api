import logging,sys
from logging.handlers import RotatingFileHandler
from os.path import dirname
script_path = dirname(__file__)
sys.path.append(script_path)
from api import app as application
file_handler=RotatingFileHandler(script_path+'/flask_err.log')
file_handler.setLevel(logging.WARNING)
application.logger.addHandler(file_handler)
