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

  title = "thing"
  mock_data = {"ma:title":title,"dc:coverage":"private","ma:hasLanguage":["en"],"ma:description":"","ma:date":"2014","url":["http://youtu.be/h2tfjG4tzWY"],"type":"yt"}
  posted = app.post('/video', data=json.dumps(mock_data), content_type='application/json')
  response = json.loads(posted.data)
  pid = response['pid']

  patch = { 'ma:title': 'Ghostbusters', 'ma:date': '' } 

  result = app.patch('/video/' + pid, data=json.dumps(patch), content_type='application/json')

  assert result.status_code is 200
  
  result_data = json.loads(result.data)
  assert result_data['ma:title'] == patch['ma:title']

def test_patch_video_25_fps(app, ACCOUNTS):
  from mongokit import Document, Connection
  from hummedia import config
  from hummedia.models import Video, AssetGroup
  
  connection = Connection(host=config.MONGODB_HOST, port=config.MONGODB_PORT)
  
  video = connection[Video.__database__][Video.__collection__]
  
  pid = "8675309"
  video.insert({ "_id" : pid, "@context" : { "dc:type" : "@type", "hummedia" : "http://humanities.byu.edu/hummedia/", "ma" : "http://www.w3.org/ns/ma-ont/", "dc" : "http://purl.org/dc/elements/1.1/", "dc:identifier" : "@id" }, "@graph" : { "dc:coverage" : "private", "dc:creator" : "testuser", "dc:date" : "2013-08-29", "dc:identifier" : "hummedia:id/video/"+pid, "dc:rights" : { "read" : [ ], "write" : [ ] }, "dc:type" : "hummedia:type/humvideo", "ma:averageBitRate" : 903903, "ma:date" : 1970, "ma:description" : "None", "ma:duration" : 0, "ma:features" : [ ], "ma:frameHeight" : 360, "ma:frameRate" : 25, "ma:frameSizeUnit" : "px", "ma:frameWidth" : 720, "ma:hasContributor" : [ ], "ma:hasGenre" : { "@id" : None, "name" : None }, "ma:hasKeyword" : [  "film",  "German" ], "ma:hasLanguage" : [  "en" ], "ma:hasPolicy" : [ ], "ma:hasRelatedResource" : [ ], "ma:height" : 400, "ma:isCopyrightedBy" : { "@id" : None, "name" : None }, "ma:isMemberOf" : [     {   "@id" : "anothertest",     "title" : "Test Videos" },    {   "@id" : "testid",     "title" : "testtitle" } ], "ma:isRelatedTo" : [ ], "ma:locator" : [  {   "@id" : "tommytutone",  "ma:hasFormat" : "video/mp4",   "ma:hasCompression" : {     "@id" : "http://www.freebase.com/view/en/h_264_mpeg_4_avc",     "name" : "avc.42E01E" } },  {   "@id" : "tommytutone",  "ma:hasFormat" : "video/webm",  "ma:hasCompression" : {     "@id" : "http://www.freebase.com/m/0c02yk5",    "name" : "vp8.0" } } ], "ma:title" : "Test Video", "pid" : pid } })
  
  app.login(ACCOUNTS['SUPERUSER'])
  patch = {"ma:title": "Castaway on the Moon", "ma:isMemberOf":[]}
  result = app.patch('/video/' + pid, data=json.dumps(patch), content_type='application/json')
  raw = result.data

  assert result.status_code is 200

  data = json.loads(result.data)
  assert data['ma:title'] == patch['ma:title']
