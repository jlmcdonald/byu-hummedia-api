import pytest
import json

def test_change_owner_of_collection(app, ACCOUNTS):
  app.login(ACCOUNTS['SUPERUSER'])
  
  c = app.post('/collection', data=json.dumps({}), headers={'Content-Type': 'application/json'})
  data = json.loads(c.data)
  new = {'dc:creator': ACCOUNTS['FACULTY']['username']}
  col_pid = data['pid']
  r = app.patch('/collection/' + col_pid, data=json.dumps(new), headers={'Content-Type': 'application/json'})
  assert r.status_code is 200
  
  c = app.get('/collection/' + data['pid'])
  data = json.loads(c.data)
  assert data['dc:creator'] == ACCOUNTS['FACULTY']['username'], "Faculty could not be set as owner of collection"

def test_owner_of_collection_can_add_videos(app, ACCOUNTS):
  app.login(ACCOUNTS['SUPERUSER'])
  c = app.post('/collection', data=json.dumps({}), headers={'Content-Type': 'application/json'})
  v = app.post('/video', data=json.dumps({}), headers={'Content-Type': 'application/json'})

  c_data = json.loads(c.data)
  new = {'dc:creator': ACCOUNTS['FACULTY']['username']}
  col_pid = c_data['pid']
  r = app.patch('/collection/' + col_pid, data=json.dumps(new), headers={'Content-Type': 'application/json'})

  app.login(ACCOUNTS['FACULTY'])
  vid_data =  json.loads(v.data)
  vid_pid = vid_data['pid']
  
  membership = [{"collection":{"id":col_pid,"title":"Something"},"videos":[vid_pid]}]
  membership_result = app.post('/batch/video/membership', data=json.dumps(membership), headers={'Content-Type': "application/json"})
  assert membership_result.status_code is 200

  new_c = app.get('/collection/' + col_pid + '?full=true')
  assert len(json.loads(new_c.data)['videos']) is 1

def test_write_access_of_collection_can_add_videos(app, ACCOUNTS):
  app.login(ACCOUNTS['SUPERUSER'])
  c = app.post('/collection', data=json.dumps({}), headers={'Content-Type': 'application/json'})
  v = app.post('/video', data=json.dumps({}), headers={'Content-Type': 'application/json'})

  c_data = json.loads(c.data)
  user = ACCOUNTS['STUDENT']['username']
  patch_data = {'dc:rights': {'read': [user], 'write': [user]}}
  col_pid = c_data['pid']
  r = app.patch('/collection/' + col_pid, data=json.dumps(patch_data), headers={'Content-Type': 'application/json'})
  
  app.login(ACCOUNTS['STUDENT'])
  vid_data =  json.loads(v.data)
  vid_pid = vid_data['pid']
  
  membership = [{"collection":{"id":col_pid,"title":"Something"},"videos":[vid_pid]}]
  membership_result = app.post('/batch/video/membership', data=json.dumps(membership), headers={'Content-Type': "application/json"})
  assert membership_result.status_code is 200

  new_c = app.get('/collection/' + col_pid + '?full=true')
  result = json.loads(new_c.data)
  assert len(result['videos']) is 1

def test_student_no_write_access_of_collection_cannot_add_videos(app, ACCOUNTS):
  app.login(ACCOUNTS['SUPERUSER'])
  c = app.post('/collection', data=json.dumps({}), headers={'Content-Type': 'application/json'})
  v = app.post('/video', data=json.dumps({}), headers={'Content-Type': 'application/json'})
  
  app.login(ACCOUNTS['STUDENT'])
  vid_data =  json.loads(v.data)
  vid_pid = vid_data['pid']
  c_data = json.loads(c.data)
  col_pid = c_data['pid']
  
  membership = [{"collection":{"id":col_pid,"title":"Something"},"videos":[vid_pid]}]
  membership_result = app.post('/batch/video/membership', data=json.dumps(membership), headers={'Content-Type': "application/json"})
  assert membership_result.status_code is 401

  app.login(ACCOUNTS['SUPERUSER'])
  new_c = app.get('/collection/' + col_pid + '?full=true')
  result = json.loads(new_c.data)
  assert len(result['videos']) is 0
