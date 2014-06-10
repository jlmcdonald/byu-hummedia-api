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
  return {
   'SUPERUSER': {'superuser': True, 'username': 'arbitraryname'},
   'STUDENT': {'superuser': False, 'username': 'miss_havisham', 'role': 'student'},
   'FACULTY': {'superuser': False, 'username': 'john_psota', 'role': 'faculty'}
  }

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

@pytest.fixture(autouse=True)
def configure():
  hummedia.app.config.update(
      SESSION_COOKIE_DOMAIN = None,
      MONGODB_DB = 'AUTOMATED_TESTS',
      TESTING = True
  )
  config.SUBTITLE_DIRECTORY = tempfile.mkdtemp('hummedia-subs') + os.sep
  config.MEDIA_DIRECTORY = tempfile.mkdtemp('hummedia-audio') + os.sep
