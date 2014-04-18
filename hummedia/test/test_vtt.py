import pytest
import io
import json
from .. import config
from .. import vtt

def test_from_srt(ASSETS):
  f = io.BytesIO()
  vtt.from_srt(ASSETS + 'subs.srt', f)
  compare = open(ASSETS + 'subs.vtt', 'r')
  assert f.getvalue() == compare.read()

def test_from_srt_file(ASSETS):
  i = open(ASSETS + 'subs.srt')
  o = io.BytesIO()
  vtt.from_srt(i, o)
  compare = open(ASSETS + 'subs.vtt', 'r')
  assert o.getvalue() == compare.read()

def test_iso_8859_srt(ASSETS):
  i = open(ASSETS + 'ISO-8859.srt')
  o = io.BytesIO()
  vtt.from_srt(i, o)
  compare = open(ASSETS + 'utf8.vtt', 'r')
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

