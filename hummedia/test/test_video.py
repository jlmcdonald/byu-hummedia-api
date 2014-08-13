import pytest
import json

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

def test_limit_search(app, ACCOUNTS, monkeypatch):
  from ..resources import MediaAsset

  monkeypatch.setattr(MediaAsset, 'max_search_results', 2)

  # TODO: use a mock database so we don't have to wipe it
  MediaAsset.collection.database.drop_collection('assets')
  MediaAsset.collection.database.create_collection('assets')

  title = "Wolfeschlegelstein"

  app.login(ACCOUNTS['SUPERUSER'])
  total_films = MediaAsset.max_search_results + 2;
  mock_data = {"ma:title":title,"dc:coverage":"private","ma:hasLanguage":["en"],"ma:description":"","ma:date":"2014","url":["http://youtu.be/h2tfjG4tzWY"],"type":"yt"}

  for i in range(0, total_films):
    response = app.post('/video', data=json.dumps(mock_data),
        content_type='application/json')
    assert response.status_code == 200
  
  response = app.get('/video')
  data = json.loads(response.data)
  assert len(data) == total_films
  
  response = app.get('/video?q=' + title)
  data = json.loads(response.data)
  assert len(data) == MediaAsset.max_search_results

def test_patch_video_without_good_date(app, ACCOUNTS):
  from ..resources import MediaAsset

  app.login(ACCOUNTS['SUPERUSER'])

  # TODO: use a mock database so we don't have to wipe it
  MediaAsset.collection.database.drop_collection('assets')
  MediaAsset.collection.database.create_collection('assets')

  title = "thing"
  mock_data = {"ma:title":title,"dc:coverage":"private","ma:hasLanguage":["en"],"ma:description":"","ma:date":"2014","url":["http://youtu.be/h2tfjG4tzWY"],"type":"yt"}
  posted = app.post('/video', data=json.dumps(mock_data), content_type='application/json')
  response = json.loads(posted.data)
  pid = response['pid']
  patch = {
    'ma:title': 'Ghostbusters',
    'ma:date': '',
    'pid': pid
  } 

  result = app.patch('/video/' + pid, data=json.dumps(patch), content_type='application/json')

  assert result.status_code is 200
  
  result_data = json.loads(result.data)
  assert result_data['ma:title'] == patch['ma:title']
