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
  print vid
  data = {"media":[{"id":vid,"name":"Media0","target":"hum-video","tracks":[{"name":"Layer 0","id":"0","trackEvents":[{"id":"TrackEvent0","type":"mutePlugin","popcornOptions":{"start":0,"end":2.53663,"target":"target-4","__humrequired":True,"id":"TrackEvent0"},"track":"0","name":"TrackEvent0"}]}],"clipData":{}}]}
  response = app.post('/annotation?client=popcorn',
                      data=json.dumps(data),
                      headers={'Content-Type': 'application/json'})
  print response.data
  assert response.status_code == 200
