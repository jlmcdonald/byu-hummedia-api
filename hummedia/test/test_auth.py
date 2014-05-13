def test_redirect_url(app, ACCOUNTS):
  url = 'http://localhost?q=dog'
  
  app.login(ACCOUNTS['SUPERUSER'])

  with app.session_transaction() as sess:
    sess['redirect'] = url

  result = app.get('/account/login?r=' + url)
  assert url == result.headers['location']
