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
  from bson.objectid import ObjectId
  
  connection = Connection(host=config.MONGODB_HOST, port=config.MONGODB_PORT)
  
  video = connection[Video.__database__][Video.__collection__]
  
  pid = str(ObjectId())
  video.insert({ "_id" : pid, "@context" : { "dc:type" : "@type", "hummedia" : "http://humanities.byu.edu/hummedia/", "ma" : "http://www.w3.org/ns/ma-ont/", "dc" : "http://purl.org/dc/elements/1.1/", "dc:identifier" : "@id" }, "@graph" : { "dc:coverage" : "private", "dc:creator" : "testuser", "dc:date" : "2013-08-29", "dc:identifier" : "hummedia:id/video/"+pid, "dc:rights" : { "read" : [ ], "write" : [ ] }, "dc:type" : "hummedia:type/humvideo", "ma:averageBitRate" : 903903, "ma:date" : 1970, "ma:description" : "None", "ma:duration" : 0, "ma:features" : [ ], "ma:frameHeight" : 360, "ma:frameRate" : 25, "ma:frameSizeUnit" : "px", "ma:frameWidth" : 720, "ma:hasContributor" : [ ], "ma:hasGenre" : { "@id" : None, "name" : None }, "ma:hasKeyword" : [  "film",  "German" ], "ma:hasLanguage" : [  "en" ], "ma:hasPolicy" : [ ], "ma:hasRelatedResource" : [ ], "ma:height" : 400, "ma:isCopyrightedBy" : { "@id" : None, "name" : None }, "ma:isMemberOf" : [     {   "@id" : "anothertest",     "title" : "Test Videos" },    {   "@id" : "testid",     "title" : "testtitle" } ], "ma:isRelatedTo" : [ ], "ma:locator" : [  {   "@id" : "tommytutone",  "ma:hasFormat" : "video/mp4",   "ma:hasCompression" : {     "@id" : "http://www.freebase.com/view/en/h_264_mpeg_4_avc",     "name" : "avc.42E01E" } },  {   "@id" : "tommytutone",  "ma:hasFormat" : "video/webm",  "ma:hasCompression" : {     "@id" : "http://www.freebase.com/m/0c02yk5",    "name" : "vp8.0" } } ], "ma:title" : "Test Video", "pid" : pid } })
  
  app.login(ACCOUNTS['SUPERUSER'])
  patch = {"ma:title": "Castaway on the Moon", "ma:isMemberOf":[]}
  result = app.patch('/video/' + pid, data=json.dumps(patch), content_type='application/json')
  raw = result.data

  assert result.status_code is 200

  data = json.loads(result.data)
  assert data['ma:title'] == patch['ma:title']
  
def test_ingest(app, ACCOUNTS, ASSETS):
  from uuid import uuid4
  from shutil import copyfile
  from hummedia import config
  from os.path import isfile
  filename = 'fire.mp4'

  app.login(ACCOUNTS['SUPERUSER'])
  response = app.post('/video')
  data = json.loads(response.data)
  pid = data[u'pid']
  copyfile(ASSETS + filename, config.INGEST_DIRECTORY + filename)
  up = json.dumps([{"filepath": filename, "pid": pid, "id":  str(uuid4())}])
  ingest_response = app.post('/batch/video/ingest', data=up, content_type='application/json')

  assert ingest_response.status_code is 200

  vid_response = app.get('/video/' + pid)
  vid = json.loads(vid_response.data)

  assert len(vid['url']) is 2

  for v in vid['url']:
    filename = v.split('/')[-1]
    assert isfile(config.MEDIA_DIRECTORY + filename)

def test_ingest_duplicate_id(app, ACCOUNTS, ASSETS):
  from shutil import copyfile
  from hummedia import config
  from uuid import uuid4
  
  app.login(ACCOUNTS['SUPERUSER'])

  filename = 'fire.mp4'
  unique_id = str(uuid4())

  new_filename = str(uuid4()) + '.mp4'
  response = app.post('/video')
  data = json.loads(response.data)
  pid = data[u'pid']
  copyfile(ASSETS + filename, config.INGEST_DIRECTORY + new_filename)
  up = json.dumps([{"filepath": new_filename, "pid": pid, "id":  unique_id}])
  ingest_response = app.post('/batch/video/ingest', data=up, content_type='application/json')
  assert ingest_response.status_code is 200, "Error ingesting first video: \"%s\"" % ingest_response.data

  response = app.post('/video')
  new_filename = str(uuid4()) + '.mp4'
  data = json.loads(response.data)
  pid = data[u'pid']
  copyfile(ASSETS + filename, config.INGEST_DIRECTORY + new_filename)
  up = json.dumps([{"filepath": new_filename, "pid": pid, "id":  unique_id}])
  ingest_response = app.post('/batch/video/ingest', data=up, content_type='application/json')
  assert ingest_response.status_code is not 200, "Second video could overwrite first video."

def test_no_dotfiles(app, ACCOUNTS):
  from uuid import uuid4
  import os
  from hummedia import config
  app.login(ACCOUNTS['SUPERUSER'])

  dotfile = config.INGEST_DIRECTORY + '.' + str(uuid4())
  mp4file = config.INGEST_DIRECTORY + str(uuid4()) + '.mp4'

  for filename in (dotfile, mp4file):
    with open(filename,'a'):
      os.utime(filename,None)

  ingest = app.get('/batch/video/ingest')
  data = json.loads(ingest.data)

  assert len(data) is 1
  assert data[0].find('.mp4') is not -1

def test_delete_video_file(app, ACCOUNTS, ASSETS):
  from uuid import uuid4
  from shutil import copyfile
  from hummedia import config
  from os.path import isfile
  filename = 'fire.mp4'

  app.login(ACCOUNTS['SUPERUSER'])
  response = app.post('/video')
  data = json.loads(response.data)
  pid = data[u'pid']
  copyfile(ASSETS + filename, config.INGEST_DIRECTORY + filename)
  up = json.dumps([{"filepath": filename, "pid": pid, "id":  str(uuid4())}])
  ingest_response = app.post('/batch/video/ingest', data=up, content_type='application/json')

  vid_response = app.get('/video/' + pid)
  vid = json.loads(vid_response.data)
  filepath = config.MEDIA_DIRECTORY + vid['url'][0].split('/')[-1]

  assert isfile(filepath)
  response = app.delete('/video/' + pid)
  assert response.status_code is 200, "Video document could not be deleted."
  assert not isfile(filepath), "Video was deleted, but file was not"

def test_delete_video_duplicate_documents_one_file(app, ACCOUNTS, ASSETS):
  from uuid import uuid4
  from shutil import copyfile
  from os.path import isfile
  from bson.objectid import ObjectId
  from mongokit import Document, Connection
  from hummedia import config
  from hummedia.models import Video, AssetGroup
  from bson.objectid import ObjectId
  
  connection = Connection(host=config.MONGODB_HOST, port=config.MONGODB_PORT)
  video = connection[Video.__database__][Video.__collection__]
  
  pid = str(ObjectId())
  filename = str(ObjectId())
  filepath = config.MEDIA_DIRECTORY + filename + '.mp4'
  copyfile(ASSETS + 'fire.mp4', filepath)
  video.insert({ "_id" : pid, "@context" : { "dc:type" : "@type", "hummedia" : "http://humanities.byu.edu/hummedia/", "ma" : "http://www.w3.org/ns/ma-ont/", "dc" : "http://purl.org/dc/elements/1.1/", "dc:identifier" : "@id" }, "@graph" : { "dc:coverage" : "private", "dc:creator" : "testuser", "dc:date" : "2013-08-29", "dc:identifier" : "hummedia:id/video/"+pid, "dc:rights" : { "read" : [ ], "write" : [ ] }, "dc:type" : "hummedia:type/humvideo", "ma:averageBitRate" : 903903, "ma:date" : 1970, "ma:description" : "None", "ma:duration" : 0, "ma:features" : [ ], "ma:frameHeight" : 360, "ma:frameRate" : 25, "ma:frameSizeUnit" : "px", "ma:frameWidth" : 720, "ma:hasContributor" : [ ], "ma:hasGenre" : { "@id" : None, "name" : None }, "ma:hasKeyword" : [  "film",  "German" ], "ma:hasLanguage" : [  "en" ], "ma:hasPolicy" : [ ], "ma:hasRelatedResource" : [ ], "ma:height" : 400, "ma:isCopyrightedBy" : { "@id" : None, "name" : None }, "ma:isMemberOf" : [     {   "@id" : "anothertest",     "title" : "Test Videos" },    {   "@id" : "testid",     "title" : "testtitle" } ], "ma:isRelatedTo" : [ ], "ma:locator" : [  {   "@id" : filename,  "ma:hasFormat" : "video/mp4",   "ma:hasCompression" : {     "@id" : "http://www.freebase.com/view/en/h_264_mpeg_4_avc",     "name" : "avc.42E01E" } } ], "ma:title" : "Test Video", "pid" : pid } })
  
  pid2 = str(ObjectId())
  video.insert({ "_id" : pid2, "@context" : { "dc:type" : "@type", "hummedia" : "http://humanities.byu.edu/hummedia/", "ma" : "http://www.w3.org/ns/ma-ont/", "dc" : "http://purl.org/dc/elements/1.1/", "dc:identifier" : "@id" }, "@graph" : { "dc:coverage" : "private", "dc:creator" : "testuser", "dc:date" : "2013-08-29", "dc:identifier" : "hummedia:id/video/"+pid2, "dc:rights" : { "read" : [ ], "write" : [ ] }, "dc:type" : "hummedia:type/humvideo", "ma:averageBitRate" : 903903, "ma:date" : 1970, "ma:description" : "None", "ma:duration" : 0, "ma:features" : [ ], "ma:frameHeight" : 360, "ma:frameRate" : 25, "ma:frameSizeUnit" : "px", "ma:frameWidth" : 720, "ma:hasContributor" : [ ], "ma:hasGenre" : { "@id" : None, "name" : None }, "ma:hasKeyword" : [  "film",  "German" ], "ma:hasLanguage" : [  "en" ], "ma:hasPolicy" : [ ], "ma:hasRelatedResource" : [ ], "ma:height" : 400, "ma:isCopyrightedBy" : { "@id" : None, "name" : None }, "ma:isMemberOf" : [     {   "@id" : "anothertest",     "title" : "Test Videos" },    {   "@id" : "testid",     "title" : "testtitle" } ], "ma:isRelatedTo" : [ ], "ma:locator" : [  {   "@id" : filename,  "ma:hasFormat" : "video/mp4",   "ma:hasCompression" : {     "@id" : "http://www.freebase.com/view/en/h_264_mpeg_4_avc",     "name" : "avc.42E01E" } } ], "ma:title" : "Test Video", "pid" : pid2 } })

  app.login(ACCOUNTS['SUPERUSER'])

  response = app.delete('/video/' + pid)
  assert isfile(filepath), "Video was deleted with two references."

  response = app.delete('/video/' + pid2)
  assert not isfile(filepath), "Video was not deleted after all references to the video were removed."

def test_should_ignore_bad_duration_data(app, ACCOUNTS, ASSETS):
  app.login(ACCOUNTS['SUPERUSER'])
  response = app.post('/video')
  data = json.loads(response.data)
  pid = data[u'pid']

  vid_response = app.get('/video/' + pid)
  vid = json.loads(vid_response.data)
  vid['ma:duration'] = None
  
  result = app.patch('/video/' + pid, data=json.dumps(vid), headers={'Content-Type': 'application/json'})
  new_vid = json.loads(result.data)
  assert new_vid['ma:duration'] is not None

def test_ingest_should_set_duration(app, ACCOUNTS, ASSETS):
  from uuid import uuid4
  from shutil import copyfile
  from hummedia import config
  from os.path import isfile
  filename = 'fire-long.mp4'

  app.login(ACCOUNTS['SUPERUSER'])
  response = app.post('/video')
  data = json.loads(response.data)
  pid = data[u'pid']
  copyfile(ASSETS + filename, config.INGEST_DIRECTORY + filename)
  up = json.dumps([{"filepath": filename, "pid": pid, "id":  str(uuid4())}])
  ingest_response = app.post('/batch/video/ingest', data=up, content_type='application/json')

  vid_response = app.get('/video/' + pid)
  vid = json.loads(vid_response.data)

  assert vid['ma:duration'] > 0

def test_replace_video(app, ACCOUNTS, ASSETS):
  ''' For when incorrect videos are uploaded. '''

  from uuid import uuid4
  from shutil import copyfile
  from hummedia import config
  from os.path import isfile
  import filecmp

  filename = 'fire-long.mp4'
  replacement = 'fire-flip.mp4'
  uid = str(uuid4())

  app.login(ACCOUNTS['SUPERUSER'])
  response = app.post('/video')
  data = json.loads(response.data)
  pid = data[u'pid']
  copyfile(ASSETS + filename, config.INGEST_DIRECTORY + filename)
  copyfile(ASSETS + replacement, config.INGEST_DIRECTORY + replacement)
  up = json.dumps([{"filepath": filename, "pid": pid, "id":  uid}])
  ingest_response = app.post('/batch/video/ingest', data=up, content_type='application/json')

  vid_response = app.get('/video/' + pid)
  vid = json.loads(vid_response.data)

  data = json.dumps({'replacement_file': replacement})
  replace_response = app.patch('/video/' + vid['pid'], data=data, content_type='application/json')

  assert replace_response.status_code is 200, "Error: " + replace_response.data
  updated = json.loads(replace_response.data)

  assert isfile(config.MEDIA_DIRECTORY + uid + '.mp4')
  assert filecmp.cmp(config.MEDIA_DIRECTORY + uid + '.mp4', ASSETS + replacement), "Video was not replaced."

def test_concise_video_list(app, ACCOUNTS, ASSETS):
  ''' Media is starting to load slowly; we just need minimal information for our admin interface. '''
  app.login(ACCOUNTS['SUPERUSER'])
  r = app.post('/video')
  response = app.get('/video?concise')
  data = json.loads(response.data)
  assert data[0].keys() == ['pid', 'ma:title']
