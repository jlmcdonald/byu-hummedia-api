import sys
import pytest
import os
import types
import tempfile
import hummedia
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
def empty_directories(request):
  import shutil
  from hummedia import config

  def remove():
    dirs = ('SUBTITLE_DIRECTORY','MEDIA_DIRECTORY','INGEST_DIRECTORY','POSTERS_DIRECTORY')
    for path in [getattr(config,d) for d in dirs]:
      for f in os.listdir(path):
        os.unlink(path + f)

  request.addfinalizer(remove)

@pytest.fixture(autouse=True)
def configure():
  '''
  NOTE: SEE hummedia/__init__.py for other test-specific configuration values
  '''

  from hummedia import config

  if config.MONGODB_DB == 'hummedia':
    import sys
    print "WARNING: It looks like these tests are being run on a live database.\
        The test database name cannot be 'hummedia'."
    sys.exit(1)

  os.system('mongo ' + config.MONGODB_DB + ' --eval "JSON.stringify(db.dropDatabase())"')

  hummedia.app.config.update(
    SESSION_COOKIE_DOMAIN=None,
    TESTING=True,
  )
