import json

def test_required_annotation_audio(app, ACCOUNTS, ASSETS):
  app.login(ACCOUNTS['SUPERUSER'])

  # TODO: mock the database with certain entries
  with open(ASSETS + 'stapler.mp3') as f:
    data = {
        'audio[]': [(f, 'audio.mp3')]
    }
    response = app.post('/batch/audio/ingest', data=data)

  data = json.loads(response.data)
  vid = data[0]['pid']

  headers = [('Content-Type', 'application/json')]
  data = {"media":[{"id":vid,"name":"Media0","target":"hum-video","tracks":[{"name":"Layer 0","id":"0","trackEvents":[{"id":"TrackEvent0","type":"mutePlugin","popcornOptions":{"start":0,"end":2.53663,"target":"target-0","__humrequired":True,"id":"TrackEvent0"},"track":"0","name":"TrackEvent0"}]}],"clipData":{}}]}
  response = app.post('/annotation?client=popcorn',
                      data=json.dumps(data),
                      headers={'Content-Type': 'application/json'})
  assert response.status_code == 200

def test_collection_write_access_faculty_can_modify(app, ACCOUNTS):
  ''' If we create a collection as a superuser, annotate it, and then
      give someone write access to the collection it belongs to,
      then that person should have write access to the annotations as well. '''

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

  required = {"media":[{"id":vid_pid,"name":"Media0","url":["https://milo.byu.edu///movies/50aba99cbe3e2dadd67872da44b0da94/54131f93/0033467.mp4","https://milo.byu.edu///movies/b4861e89ca5c8adf5ae37281743206cd/54131f93/0033467.webm"],"target":"hum-video","duration":300.011,"popcornOptions":{"frameAnimation":True},"controls":False,"tracks":[{"name":"Layer 0","id":"0","trackEvents":[]}],"clipData":{}}]}
  req_result = app.post('/annotation?client=popcorn', data=json.dumps(required), headers={'Content-Type': 'application/json'})
  assert req_result.status_code is 200, "Superuser could not create required annotation"
  req_data = json.loads(req_result.data)
  req_id = req_data['media'][0]['tracks'][0]['id']

  collection_based = {"media":[{"id":vid_pid,"name":"Media0","url":["https://milo.byu.edu///movies/50aba99cbe3e2dadd67872da44b0da94/54131f93/0033467.mp4","https://milo.byu.edu///movies/b4861e89ca5c8adf5ae37281743206cd/54131f93/0033467.webm"],"target":"hum-video","duration":300.011,"popcornOptions":{"frameAnimation":True},"controls":False,"tracks":[{"name":"Layer 0","id":"0","trackEvents":[{"id":"TrackEvent0","type":"skip","popcornOptions":{"start":0,"end":5,"target":"target-0","__humrequired":False,"id":"TrackEvent0"},"track":"0","name":"TrackEvent0"}]}],"clipData":{}}]}
  col_result = app.post('/annotation?client=popcorn&collection=' + col_pid, data=json.dumps(collection_based), headers={'Content-Type':'application/json'})
  assert col_result.status_code is 200, "Superuser could not create collection-based annotation"
  col_data = json.loads(col_result.data)
  col_based_id = col_data['media'][0]['tracks'][0]['id']

  # now grant write access to the faculty
  patch = {"dc:rights": {"read": [ACCOUNTS['FACULTY']['username']], "write": [ACCOUNTS['FACULTY']['username']]}}
  result = app.patch('/collection/' + col_pid, data=json.dumps(patch), headers={'Content-Type': 'application/json'})
  assert result.status_code is 200

  app.login(ACCOUNTS['FACULTY'])
  req_patch = app.patch('/annotation/' + req_id + '?client=popcorn', data=json.dumps(required), headers={'Content-Type': 'application/json'})
  col_based_patch = app.patch('/annotation/' + col_based_id + '?client=popcorn', data=json.dumps(collection_based), headers={'Content-Type': 'application/json'})

  assert col_based_patch.status_code is 200, "Faculty with write access could not modify collection-based annotations. Status: %d" % col_based_patch.status_code
  assert req_patch.status_code is 200, "Faculty with write access could not modify required annotations. Status: %d" % req_patch.status_code

def test_collection_write_access_ta_can_annotate(app, ACCOUNTS):
  ''' If we create a collection as a superuser and then
      give a student write access to the collection it belongs to,
      then that person should have write access to the annotations as well. '''

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

  # now grant write access to the TA
  patch = {"dc:rights": {"read": [ACCOUNTS['STUDENT']['username']], "write": [ACCOUNTS['STUDENT']['username']]}}
  result = app.patch('/collection/' + col_pid, data=json.dumps(patch), headers={'Content-Type': 'application/json'})
  assert result.status_code is 200
  
  app.login(ACCOUNTS['STUDENT'])

  collection_based = {"media":[{"id":vid_pid,"name":"Media0","url":["https://milo.byu.edu///movies/50aba99cbe3e2dadd67872da44b0da94/54131f93/0033467.mp4","https://milo.byu.edu///movies/b4861e89ca5c8adf5ae37281743206cd/54131f93/0033467.webm"],"target":"hum-video","duration":300.011,"popcornOptions":{"frameAnimation":True},"controls":False,"tracks":[{"name":"Layer 0","id":"0","trackEvents":[{"id":"TrackEvent0","type":"skip","popcornOptions":{"start":0,"end":5,"target":"target-0","__humrequired":False,"id":"TrackEvent0"},"track":"0","name":"TrackEvent0"}]}],"clipData":{}}]}
  col_result = app.post('/annotation?client=popcorn&collection=' + col_pid, data=json.dumps(collection_based), headers={'Content-Type':'application/json'})
 
  assert col_result.status_code is 200, "TA could not create collection-based annotation"
  col_data = json.loads(col_result.data)
  col_based_id = col_data['media'][0]['tracks'][0]['id']
  col_based_patch = app.patch('/annotation/' + col_based_id + '?client=popcorn', data=json.dumps(collection_based), headers={'Content-Type': 'application/json'})

  assert col_based_patch.status_code is 200, "TA with write access could not modify collection-based annotations. Status: %d" % col_based_patch.status_code

def test_collection_write_access_ta_can_patch_superusers_edit(app, ACCOUNTS):
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

  # now grant write access to the TA
  patch = {"dc:rights": {"read": [ACCOUNTS['STUDENT']['username']], "write": [ACCOUNTS['STUDENT']['username']]}}
  result = app.patch('/collection/' + col_pid, data=json.dumps(patch), headers={'Content-Type': 'application/json'})
  assert result.status_code is 200
  
  collection_based = {"media":[{"id":vid_pid,"name":"Media0","url":["https://milo.byu.edu///movies/50aba99cbe3e2dadd67872da44b0da94/54131f93/0033467.mp4","https://milo.byu.edu///movies/b4861e89ca5c8adf5ae37281743206cd/54131f93/0033467.webm"],"target":"hum-video","duration":300.011,"popcornOptions":{"frameAnimation":True},"controls":False,"tracks":[{"name":"Layer 0","id":"0","trackEvents":[{"id":"TrackEvent0","type":"skip","popcornOptions":{"start":0,"end":5,"target":"target-0","__humrequired":False,"id":"TrackEvent0"},"track":"0","name":"TrackEvent0"}]}],"clipData":{}}]}
  col_result = app.post('/annotation?client=popcorn&collection=' + col_pid, data=json.dumps(collection_based), headers={'Content-Type':'application/json'})
  col_data = json.loads(col_result.data)
  col_based_id = col_data['media'][0]['tracks'][0]['id']
  
  app.login(ACCOUNTS['STUDENT'])
  col_based_patch = app.patch('/annotation/' + col_based_id + '?client=popcorn', data=json.dumps(collection_based), headers={'Content-Type': 'application/json'})

  assert col_based_patch.status_code is 200, "TA with write access could not modify collection-based annotations created by superuser. Status: %d" % col_based_patch.status_code

def test_collection_annotations_not_with_required(app, ACCOUNTS):
  ''' There's a bug where collection-based annotations are coming back with
      required annotations included in the same list. '''
  
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
 
  # maketh a required annotation
  required = {"media":[{"id":vid_pid,"name":"Media0","url":["https://milo.byu.edu///movies/50aba99cbe3e2dadd67872da44b0da94/54131f93/0033467.mp4","https://milo.byu.edu///movies/b4861e89ca5c8adf5ae37281743206cd/54131f93/0033467.webm"],"target":"hum-video","duration":300.011,"popcornOptions":{"frameAnimation":True},"controls":False,"tracks":[{"name":"Layer 0","id":"0","trackEvents":[]}],"clipData":{}}]}
  req_result = app.post('/annotation?client=popcorn', data=json.dumps(required), headers={'Content-Type': 'application/json'})
  assert req_result.status_code is 200, "Superuser could not create required annotation"

  # now make a collection-based annotation
  collection_based = {"media":[{"id":vid_pid,"name":"Media0","url":["https://milo.byu.edu///movies/50aba99cbe3e2dadd67872da44b0da94/54131f93/0033467.mp4","https://milo.byu.edu///movies/b4861e89ca5c8adf5ae37281743206cd/54131f93/0033467.webm"],"target":"hum-video","duration":300.011,"popcornOptions":{"frameAnimation":True},"controls":False,"tracks":[{"name":"Layer 0","id":"0","trackEvents":[{"id":"TrackEvent0","type":"skip","popcornOptions":{"start":0,"end":5,"target":"target-0","__humrequired":False,"id":"TrackEvent0"},"track":"0","name":"TrackEvent0"}]}],"clipData":{}}]}
  col_result = app.post('/annotation?client=popcorn&collection=' + col_pid, data=json.dumps(collection_based), headers={'Content-Type':'application/json'})
  assert col_result.status_code is 200, "Superuser could not create collection-based annotation"

  annotation_result = app.get('/annotation?client=popcorn&collection=' + col_pid + '&dc:relation=' + vid_pid)
  data = json.loads(annotation_result.data)

  assert len(data) is 1

def test_unauthorized_student_cannot_annotate(app, ACCOUNTS):
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
  
  app.login(ACCOUNTS['STUDENT'])
  collection_based = {"media":[{"id":vid_pid,"name":"Media0","url":["https://milo.byu.edu///movies/50aba99cbe3e2dadd67872da44b0da94/54131f93/0033467.mp4","https://milo.byu.edu///movies/b4861e89ca5c8adf5ae37281743206cd/54131f93/0033467.webm"],"target":"hum-video","duration":300.011,"popcornOptions":{"frameAnimation":True},"controls":False,"tracks":[{"name":"Layer 0","id":"0","trackEvents":[{"id":"TrackEvent0","type":"skip","popcornOptions":{"start":0,"end":5,"target":"target-0","__humrequired":False,"id":"TrackEvent0"},"track":"0","name":"TrackEvent0"}]}],"clipData":{}}]}
  col_result = app.post('/annotation?client=popcorn&collection=' + col_pid, data=json.dumps(collection_based), headers={'Content-Type':'application/json'})
  assert col_result.status_code == 401

def test_patch_with_transcript(app, ACCOUNTS):
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

  # try to add a transcript
  ann_pid = json.loads(col_result.data)['media'][0]['tracks'][0]['id']
  data ={"pid":ann_pid,"vcp:playSettings":{"vcp:showTranscript":True}}
  app.patch('/annotation/' + ann_pid, data=json.dumps(data), headers={'Content-Type':'application/json'})

  # make sure the transcript is included in the data that comes back from the server
  full_coll = app.get('/collection/' + col_pid + '?full=true')
  full_coll_data = json.loads(full_coll.data)

  assert full_coll_data['videos'][0]['transcript'], "Transcript not enabled."
