import pytest
import io
import json
import sys
from .. import config
from .. import vtt

reload(sys)
sys.setdefaultencoding('utf-8')

def test_from_srt(ASSETS):
  f = io.BytesIO()
  vtt.from_srt(ASSETS + 'subs.srt', f)
  compare = open(ASSETS + 'subs.vtt', 'r')
  assert f.getvalue() == compare.read()

def test_from_srt_bom(ASSETS):
  f = io.BytesIO()
  vtt.from_srt(ASSETS + 'subs-bom.srt', f)
  compare = open(ASSETS + 'subs.vtt', 'r')
  assert f.getvalue() == compare.read()

def test_from_srt_file(ASSETS):
  i = open(ASSETS + 'subs.srt')
  o = io.BytesIO()
  vtt.from_srt(i, o)
  compare = open(ASSETS + 'subs.vtt', 'r')
  v = o.getvalue().decode('utf8')
  w = compare.read().decode('utf8')
  assert v == w

def test_from_srt_file_tricky_decoding(ASSETS):
  i = open(ASSETS + 'tricky-decoding.srt')
  o = io.BytesIO()
  try:
    vtt.from_srt(i, o)
  except UnicodeDecodeError:
    assert False, "Could not accurately decode srt file."

def test_from_bad_srt(ASSETS):
  i = open(ASSETS + 'fake.srt')
  o = io.BytesIO()
  with pytest.raises(Exception):
    vtt.from_srt(i, o)

def test_iso_8859_srt(ASSETS):
  i = open(ASSETS + 'ISO-8859.srt')
  o = io.BytesIO()
  vtt.from_srt(i, o)
  compare = open(ASSETS + 'utf8.vtt', 'r')
  assert o.getvalue() == compare.read()

def test_special_chars(ASSETS):
  i = open(ASSETS + 'special-chars.srt')
  o = io.BytesIO()
  vtt.from_srt(i, o)
  compare = open(ASSETS + 'special-chars.vtt', 'r')
  assert o.getvalue() == compare.read()

def test_shift_time(ASSETS):
  f = io.BytesIO()
  vtt.shift_time(ASSETS + 'subs.vtt', f, 10)
  compare = open(ASSETS + 'subs+10.vtt', 'r')
  assert f.getvalue() == compare.read()

def test_shift_time_file(ASSETS):
  i = open(ASSETS + 'subs.vtt', 'r')
  o = io.BytesIO()
  vtt.shift_time(i, o, 10)
  i.close()
  compare = open(ASSETS + 'subs+10.vtt', 'r')
  assert o.getvalue() == compare.read()

def test_validate_vtt(ASSETS):
  assert vtt.is_valid(ASSETS + 'subs.vtt') is True

def test_invalid_vtt(ASSETS):
  assert vtt.is_valid(ASSETS + 'invalid.vtt') is False

def test_upload_srt(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["SUPERUSER"])
  response = None

  with open(ASSETS + 'subs.srt') as f:
    data = {"subtitle": (f, 'subs.srt')}
    response = app.post('/video', data=data)
  
  assert response.status_code == 200
  data = json.loads(response.data)
  file = data['ma:hasRelatedResource'][0]['@id']
  assert file.split('.')[-1] == 'vtt'
  filename = file.split('/')[-1]
  
  file = open(config.SUBTITLE_DIRECTORY + filename, 'r')
  orig = open(ASSETS + 'subs.vtt', 'r')
  assert orig.read() == file.read()

def test_upload_vtt(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["SUPERUSER"])
  response = None

  with open(ASSETS + 'subs.vtt') as f:
    data = {
        'subtitle': (f, 'subs.vtt'),
        'name': "The One True Subtitle",
        'lang': 'en'
    }
    response = app.post('/video', data=data)
  
  assert response.status_code == 200
  data = json.loads(response.data)
  file = data['ma:hasRelatedResource'][0]['@id']
  assert data['ma:hasRelatedResource'][0]['name'] == 'The One True Subtitle'
  assert data['ma:hasRelatedResource'][0]['language'] == 'en'
  assert file.split('.')[-1] == 'vtt'
  filename = file.split('/')[-1]
  
  file = open(config.SUBTITLE_DIRECTORY + filename, 'r')
  orig = open(ASSETS + 'subs.vtt', 'r')
  assert orig.read() == file.read()

def test_upload_vtt_as_student_with_write_access(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["SUPERUSER"])
  
  v = app.post('/video')
  data = json.loads(v.data)
  vid_pid = data['pid']

  c = app.post('/collection', data=json.dumps({}), headers={'Content-Type': 'application/json'})
  data = json.loads(c.data)
  col_pid = data['pid']

  # attach video to collection
  membership = [{"collection":{"id":col_pid,"title":"Something"},"videos":[vid_pid]}]
  membership_result = app.post('/batch/video/membership', data=json.dumps(membership), headers={'Content-Type': "application/json"})
  assert membership_result.status_code is 200

  # now grant write access to the TA
  patch = {"dc:rights": {"read": [ACCOUNTS['STUDENT']['username']], "write": [ACCOUNTS['STUDENT']['username']]}}
  result = app.patch('/collection/' + col_pid, data=json.dumps(patch), headers={'Content-Type': 'application/json'})
  assert result.status_code is 200
  
  app.login(ACCOUNTS['STUDENT'])

  response = None

  with open(ASSETS + 'subs.vtt') as f:
    data = {
        'subtitle': (f, 'subs.vtt'),
        'name': "The One True Subtitle",
        'lang': 'en'
    }
    response = app.patch('/video/' + vid_pid, data=data)
  
  assert response.status_code == 200
  data = json.loads(response.data)
  file = data['ma:hasRelatedResource'][0]['@id']
  assert data['ma:hasRelatedResource'][0]['name'] == 'The One True Subtitle'
  assert data['ma:hasRelatedResource'][0]['language'] == 'en'
  assert file.split('.')[-1] == 'vtt'
  filename = file.split('/')[-1]
  
  file = open(config.SUBTITLE_DIRECTORY + filename, 'r')
  orig = open(ASSETS + 'subs.vtt', 'r')
  assert orig.read() == file.read()

def test_upload_invalid_vtt(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS['SUPERUSER'])
  response = None

  with open(ASSETS + 'invalid.vtt') as f:
    data = {
        'subtitle': (f, 'subs.vtt'),
        'name': "The One True Subtitle",
        'lang': 'en'
    }
    response = app.post('/video', data=data)

  assert response.status_code == 400
    

def test_upload_multi_period_vtt(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["SUPERUSER"])
  response = None

  with open(ASSETS + 'subs.vtt') as f:
    data = {
        'subtitle': (f, 'has.lots.of.periods.vtt')
    }
    response = app.post('/video', data=data)
  
  assert response.status_code == 200

def test_upload_bad_extension_subtitles(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["SUPERUSER"])
  response = None

  with pytest.raises(Exception) as e:
    with open(ASSETS + 'subs.vtt') as f:
      data = {
          'subtitle': (f, 'bad.extension')
      }
      app.post('/video', data=data)

    assert 'Extension' in str(e)

def test_upload_duplicate_named_subtitles(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["SUPERUSER"])
  response = None

  with open(ASSETS + 'subs+10.vtt') as f:
    data = {"subtitle": (f, 'subs.vtt')}
    response = app.post('/video', data=data)
  
  with open(ASSETS + 'subs.vtt') as f:
    rjson = json.loads(response.data)
    data = {"subtitle": (f, 'subs.vtt')}
    response = app.patch('/video/' + rjson['pid'], data=data)
  
  assert response.status_code == 200
  data = json.loads(response.data)
  assert len(data['ma:hasRelatedResource']) == 2
  file1 = data['ma:hasRelatedResource'][0]['@id']
  file2 = data['ma:hasRelatedResource'][1]['@id']
  assert file1 != file2

def test_delete_subtitles(ASSETS, ACCOUNTS, app):
  import os

  app.login(ACCOUNTS["SUPERUSER"])
  response = None

  with open(ASSETS + 'subs.vtt') as f:
    data = {
        'subtitle': (f, 'subs.vtt')
    }
    response = app.post('/video', data=data)
  
  data = json.loads(response.data)
  pid  = data['pid']
  file = data['ma:hasRelatedResource'][0]['@id']
  filename = file.split('/')[-1]
  
  response = app.delete('/text/' + filename)
  assert response.status_code == 200, "Could not delete file"
  
  response = app.delete('/text/' + filename)
  assert response.status_code == 404, "Deleted file not returning 404"

  response = app.get('/video/' + pid)
  data = json.loads(response.data)
  assert len(data['ma:hasRelatedResource']) == 0, "RelatedResource not deletd"

  filepath = config.SUBTITLE_DIRECTORY + filename
  assert os.path.isfile(filepath) == False, "File still exists on server."

def test_delete_subtitles(ASSETS, ACCOUNTS, app):
  import os

  app.login(ACCOUNTS["SUPERUSER"])
  response = None

  with open(ASSETS + 'subs.vtt') as f:
    data = {
        'subtitle': (f, 'subs.vtt')
    }
    response = app.post('/video', data=data)
  
  data = json.loads(response.data)
  pid  = data['pid']
  file = data['ma:hasRelatedResource'][0]['@id']
  filename = file.split('/')[-1]
  
  response = app.delete('/text/' + filename)
  assert response.status_code == 200, "Invalid status code " + str(response.status_code)
  
  response = app.delete('/text/' + filename)
  assert response.status_code == 404, "Deleted file not returning 404"

  response = app.get('/video/' + pid)
  data = json.loads(response.data)
  assert len(data['ma:hasRelatedResource']) == 0, "RelatedResource not deleted"

  filepath = config.SUBTITLE_DIRECTORY + filename
  assert os.path.isfile(filepath) == False, "File still exists on server."

def test_replace_subtitle(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["SUPERUSER"])
  response = None

  with open(ASSETS + 'subs.vtt') as f:
    data = {
        'subtitle': (f, 'subs.vtt')
    }
    response = app.post('/video', data=data)
  
  data = json.loads(response.data)
  pid  = data['pid']
  filename = data['ma:hasRelatedResource'][0]['@id'].split('/')[-1]

  with open(ASSETS + 'subs-different.vtt') as f:
    data = {'subtitle': (f, 'subs.vtt')}
    response = app.put('/text/' + filename, data = data)

  assert response.status_code == 200, "Unexpected status code " + str(response.status_code)

  response = app.get('/video/' + pid)
  data = json.loads(response.data)

  assert len(data['ma:hasRelatedResource']) == 1, "Incorrect # of resources"

  filename = data['ma:hasRelatedResource'][0]['@id'].split('/')[-1]
  file = open(config.SUBTITLE_DIRECTORY + filename, 'r')
  orig = open(ASSETS + 'subs.vtt', 'r')

  assert orig.read() != file.read(), "File not replaced"
