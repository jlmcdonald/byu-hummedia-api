import json

def test_can_find_user_with_objectid(app, ACCOUNTS):
  ''' There's a fun an exciting bug where a ton of our users have ended up
  with ObjectIds instead of straight string IDs. This checks for
  backwards compatibility. '''

  from mongokit import Document, Connection
  from hummedia import config
  from hummedia.models import User
  from bson.objectid import ObjectId
  
  connection = Connection(host=config.MONGODB_HOST, port=config.MONGODB_PORT)
  
  user = connection[User.__database__][User.__collection__]
  
  _id = ObjectId()
  pid = str(_id)

  a = {'_id': _id, 'pid': str(pid)}
  a.update(ACCOUNTS['STUDENT'])
  user.insert(a)

  app.login(ACCOUNTS['SUPERUSER'])

  patch = {"username": a['username'],"superuser": a['superuser'],"firstname":"George","preferredLanguage":"en","lastname":"Norris","userid":"555555560","role": a['role'],"oauth":{"twitter":{},"google":{"access_token":[],"id":None,"email":None},"facebook":{}},"fullname":"George Norris","_id":str(pid),"email":"","isSaving":True}

  r = app.patch('/account/' + pid, data=json.dumps(patch), headers={'Content-Type': 'application/json'})
  print r.data
  assert r.status_code is 200
