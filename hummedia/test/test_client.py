import json

def test_download_ic_file(app, ACCOUNTS):
  from zipfile import ZipFile
  from StringIO import StringIO

  app.login(ACCOUNTS['SUPERUSER'])

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

  # now make a collection-based annotation
  collection_based = {"media":[{"id":vid_pid,"name":"Media0","url":["https://milo.byu.edu///movies/50aba99cbe3e2dadd67872da44b0da94/54131f93/0033467.mp4","https://milo.byu.edu///movies/b4861e89ca5c8adf5ae37281743206cd/54131f93/0033467.webm"],"target":"hum-video","duration":300.011,"popcornOptions":{"frameAnimation":True},"controls":False,"tracks":[{"name":"Layer 0","id":"0","trackEvents":[{"id":"TrackEvent0","type":"skip","popcornOptions":{"start":0,"end":5,"target":"target-0","__humrequired":False,"id":"TrackEvent0"},"track":"0","name":"TrackEvent0"}]}],"clipData":{}}]}
  col_result = app.post('/annotation?client=popcorn&collection=' + col_pid, data=json.dumps(collection_based), headers={'Content-Type':'application/json'})
  assert col_result.status_code is 200, "Superuser could not create collection-based annotation"

  # maketh a required annotation
  required = {"media":[{"id":vid_pid,"name":"Media0","url":["https://milo.byu.edu///movies/50aba99cbe3e2dadd67872da44b0da94/54131f93/0033467.mp4","https://milo.byu.edu///movies/b4861e89ca5c8adf5ae37281743206cd/54131f93/0033467.webm"],"target":"hum-video","duration":300.011,"popcornOptions":{"frameAnimation":True},"controls":False,"tracks":[{"name":"Layer 0","id":"0","trackEvents":[]}],"clipData":{}}]}
  req_result = app.post('/annotation?client=popcorn', data=json.dumps(required), headers={'Content-Type': 'application/json'})
  assert req_result.status_code is 200, "Superuser could not create required annotation"

  annotation_result = app.get('/annotation?client=ic&collection=' + col_pid + '&dc:relation=' + vid_pid)
  assert annotation_result.headers.get('Content-Type') == 'application/zip'

  z = ZipFile(StringIO(annotation_result.data))
  items = z.namelist()

  assert len(filter(lambda fname: fname.endswith('.json'), items)) is 1, 'No annotations in archive'
  assert len(filter(lambda fname: fname.endswith('.icf'), items)) is 1, 'No ICF file in archive'

  a_filename = filter(lambda fname: fname.endswith('.json'), items)[0]
  a = json.loads(z.read(a_filename))
  assert len(a) is 2, 'There are not two annotation sets in the annotation file.'
