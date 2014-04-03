import pytest
import os

@pytest.fixture
def ASSETS():
  return os.path.dirname(os.path.realpath(__file__)) + os.sep + 'assets' +\
         os.sep

'''
 Helpful when monkeypatching methods that should return specific exeptions
'''
def raise_(ex):
  raise ex
