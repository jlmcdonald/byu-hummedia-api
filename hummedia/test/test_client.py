# -*- coding: utf-8 -*-
from zipfile import ZipFile
from StringIO import StringIO
import json

def create_video_in_collection(app, title='Hummedia Video'):
  v = app.post('/video', data=json.dumps({'ma:title': title}), headers={'Content-Type': 'application/json'})
  data = json.loads(v.data)
  vid_pid = data['pid']

  c = app.post('/collection', data=json.dumps({}), headers={'Content-Type': 'application/json'})
  data = json.loads(c.data)
  col_pid = data['pid']

  # attach video to collection
  membership = [{"collection":{"id":col_pid,"title":"Something"},"videos":[vid_pid]}]
  membership_result = app.post('/batch/video/membership', data=json.dumps(membership), headers={'Content-Type': "application/json"})
  assert membership_result.status_code is 200

  return vid_pid, col_pid

def test_ic_file_correct_icf_format(app, ACCOUNTS, ASSETS):
  app.login(ACCOUNTS['SUPERUSER'])
  vid_pid, col_pid = create_video_in_collection(app)

  annotation_result = app.get('/annotation?client=ic&collection=' + col_pid + '&dc:relation=' + vid_pid)
  assert annotation_result.headers.get('Content-Type') == 'application/zip'

  z = ZipFile(StringIO(annotation_result.data))
  items = z.namelist()

  contents = z.read(filter(lambda fname: fname.endswith('.icf'), items)[0])
  contents = json.loads(contents);
  assert {'video', 'annotation', 'subtitle'} <= set(contents)

def test_download_ic_file(app, ACCOUNTS):
  app.login(ACCOUNTS['SUPERUSER'])
  vid_pid, col_pid = create_video_in_collection(app)

  # now make a collection-based annotation
  collection_based = {"media":[{"id":vid_pid,"name":"Media0","url":["https://milo.byu.edu///movies/50aba99cbe3e2dadd67872da44b0da94/54131f93/0033467.mp4","https://milo.byu.edu///movies/b4861e89ca5c8adf5ae37281743206cd/54131f93/0033467.webm"],"target":"hum-video","duration":300.011,"popcornOptions":{"frameAnimation":True},"controls":False,"tracks":[{"name":"Layer 0","id":"0","trackEvents":[{"id":"TrackEvent0","type":"skip","popcornOptions":{"start":0,"end":5,"target":"target-0","__humrequired":False,"id":"TrackEvent0"},"track":"0","name":"TrackEvent0"}]}],"clipData":{}}]}
  col_result = app.post('/annotation?client=popcorn&collection=' + col_pid, data=json.dumps(collection_based), headers={'Content-Type':'application/json'})
  assert col_result.status_code is 200, "Superuser could not create collection-based annotation"

  # maketh a required annotation
  required = {"media":[{"id":vid_pid,"name":"Media0","url":["https://milo.byu.edu///movies/50aba99cbe3e2dadd67872da44b0da94/54131f93/0033467.mp4","https://milo.byu.edu///movies/b4861e89ca5c8adf5ae37281743206cd/54131f93/0033467.webm"],"target":"hum-video","duration":300.011,"popcornOptions":{"frameAnimation":True},"controls":False,"tracks":[{"name":"Layer 0","id":"0","trackEvents":[{"id":"TrackEvent0","type":"skip","popcornOptions":{"start":10,"end":25,"target":"target-0","__humrequired":False,"id":"TrackEvent0"},"track":"0","name":"TrackEvent0"}]}],"clipData":{}}]}
  req_result = app.post('/annotation?client=popcorn', data=json.dumps(required), headers={'Content-Type': 'application/json'})
  assert req_result.status_code is 200, "Superuser could not create required annotation"

  annotation_result = app.get('/annotation?client=ic&collection=' + col_pid + '&dc:relation=' + vid_pid)
  assert annotation_result.headers.get('Content-Type') == 'application/zip'

  z = ZipFile(StringIO(annotation_result.data))
  items = z.namelist()

  assert len(filter(lambda fname: fname.endswith('.json'), items)) is 1, 'No annotations in archive'
  assert len(filter(lambda fname: fname.endswith('.icf'), items)) is 1, 'No ICF file in archive'

  a_filename = filter(lambda fname: fname.endswith('.json'), items)[0]

  filedata = z.read(a_filename)
  a = json.loads(filedata)

  assert len(a) is 2, 'There are not two annotation sets in the annotation file.'
  assert a[0]['media'][0]['tracks'][0]['trackEvents'][0]['popcornOptions']['start'] == '10'
  assert a[1]['media'][0]['tracks'][0]['trackEvents'][0]['popcornOptions']['start'] == '0'

def test_download_ic_file_subs_only(app, ACCOUNTS, ASSETS):
  from zipfile import ZipFile
  from StringIO import StringIO

  app.login(ACCOUNTS['SUPERUSER'])
  vid_pid, col_pid = create_video_in_collection(app)

  with open(ASSETS + 'subs.vtt') as f:
    data = {
        'subtitle': (f, 'subs.vtt'),
        'name': "The One True Subtitle",
        'lang': 'en'
    }
    response = app.patch('/video/' + vid_pid, data=data)

  annotation_result = app.get('/annotation?client=ic&collection=' + col_pid + '&dc:relation=' + vid_pid)
  assert annotation_result.headers.get('Content-Type') == 'application/zip'

  z = ZipFile(StringIO(annotation_result.data))
  items = z.namelist()

  assert len(filter(lambda fname: fname.endswith('.vtt'), items)) is 1, 'No subtitle in archive'
  assert len(filter(lambda fname: fname.endswith('.icf'), items)) is 1, 'No ICF file in archive'

def test_download_ic_file_non_ascii_characters(app, ACCOUNTS):
  app.login(ACCOUNTS['SUPERUSER'])
  vid_pid, col_pid = create_video_in_collection(app, u'ümläüẗs ärë ſüpër ﬀun')
  annotation_result = app.get('/annotation?client=ic&collection=' + col_pid + '&dc:relation=' + vid_pid)
  assert annotation_result.status_code is 200
