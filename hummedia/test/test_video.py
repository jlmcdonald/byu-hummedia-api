import pytest


def test_youtube_with_bad_key(monkeypatch):
  import urllib2 
  monkeypatch.setattr(urllib2, 'urlopen', lambda x: raise_(Exception()))
  from ..helpers import getYtThumbs
  vid = 'IsdCGQbbd8k'
  thumbs = getYtThumbs([vid])
  assert thumbs.has_key(vid)
  assert thumbs[vid].has_key('poster') 
  assert thumbs[vid].has_key('thumb') 
  assert thumbs[vid]['thumb'] is None
  assert thumbs[vid]['poster'] is None
