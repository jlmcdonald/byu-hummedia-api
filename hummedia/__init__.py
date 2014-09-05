from flask import Flask
app = Flask(__name__)

import sys
import re

# Are we running py.test?
x = re.compile('.*py\.test$', re.MULTILINE)
if x.match(sys.argv[0]) is not None:
  # if py.test is running this, overwrite configuration values
  import config
  from tempfile import mkdtemp
  from os import sep

  patch = {
    'MONGODB_DB': 'hummedia_test',
    'SUBTITLE_DIRECTORY': mkdtemp('hummedia-subs') + sep,
    'MEDIA_DIRECTORY': mkdtemp('hummedia-media') + sep,
    'AUTH_TOKEN_IP': False,
    'INGEST_DIRECTORY': mkdtemp('hummedia-ingest') + sep,
    'POSTERS_DIRECTORY': mkdtemp('hummedia-posters') + sep,
    'APIHOST': '',
    'HOST': '',
  }

  for name in patch:
    setattr(config, name, patch[name])
  

import hummedia.api, hummedia.auth
