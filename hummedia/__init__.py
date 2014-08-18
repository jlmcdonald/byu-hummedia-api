from flask import Flask
app = Flask(__name__)

import sys
import re

x = re.compile('.*py\.test$', re.MULTILINE)
if x.match(sys.argv[0]) is not None:
  import config
  from tempfile import mkdtemp
  from os import sep

  patch = {
    'MONGODB_DB': 'hummedia_test',
    'SUBTITLE_DIRECTORY': mkdtemp('hummedia-subs') + sep,
    'MEDIA_DIRECTORY': mkdtemp('hummedia-audio') + sep,
    'AUTH_TOKEN_IP': False,
  }

  for name in patch:
    setattr(config, name, patch[name])
  

import hummedia.api, hummedia.auth
