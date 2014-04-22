import pytest
import os
import types
import tempfile
import hummedia
from hummedia import config
from werkzeug.datastructures import Headers

@pytest.fixture
def ACCOUNTS():
  '''
  Account data that can be passed into app.login().
  Contains session information.
  '''
  return {'SUPERUSER': {'superuser': True}}

@pytest.fixture
def ASSETS():
  '''
  Returns a path to the test assets directory
  '''
  return os.path.dirname(os.path.realpath(__file__)) + os.sep + 'assets' +\
         os.sep

@pytest.fixture
def app():
  '''
  returns a test client for hummedia
  '''
  hummedia.app.config.update(
      SESSION_COOKIE_DOMAIN = None,
      TESTING = True
  )
  config.SUBTITLE_DIRECTORY = tempfile.mkdtemp('hummedia') + os.sep

  client = hummedia.app.test_client()

  def login(self, account):
    with self.session_transaction() as sess:
      sess.update(account)

  client.login = types.MethodType(login, client)
  return client

def raise_(ex):
  '''
  Helpful when monkeypatching methods that should return specific exeptions
  '''
  raise ex
