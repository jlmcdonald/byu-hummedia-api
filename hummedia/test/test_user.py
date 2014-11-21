import json

def test_patch_user(app, ACCOUNTS):
  from mongokit import Document, Connection
  from hummedia import config
  from hummedia.models import User
  from bson.objectid import ObjectId
  
  connection = Connection(host=config.MONGODB_HOST, port=config.MONGODB_PORT)
  
  user = connection[User.__database__][User.__collection__]
  
  pid = str(ObjectId())
  a = {'pid': pid}
  a.update(ACCOUNTS['STUDENT'])
  user.insert(a)

  app.login(ACCOUNTS['SUPERUSER'])

  patch = {"username": a['username'],"superuser": a['superuser'],"firstname":"George","preferredLanguage":"en","lastname":"Norris","userid":"555555560","role": a['role'],"oauth":{"twitter":{},"google":{"access_token":[],"id":None,"email":None},"facebook":{}},"fullname":"George Norris","_id":str(pid),"email":"","isSaving":True}
  print patch

  r = app.patch('/account/' + pid, data=json.dumps(patch), headers={'Content-Type': 'application/json'})
  print r.data
