from flask import Flask, request, session, redirect
from helpers import crossdomain, endpoint_404, mongo_jsonify
from urllib2 import Request, urlopen, URLError
from resources import *

app = Flask(__name__)

resource_lookup={"annotation":Annotation,"collection":AssetGroup,"video":MediaAsset, "account":UserProfile}

@app.route('/language',methods=['GET'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def languages():
    from langs import langs
    return mongo_jsonify(langs)

@app.route('/account/login',methods=['GET'])
@app.route('/account/login/<provider>',methods=['GET'])
def apilogin(provider=None):
    access_token = session.get('access_token')
    if access_token is None:
    	if provider=="google":
  		from flask_oauth import OAuth
		from config import GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET
		google = oauth.remote_app('google',
                         base_url='https://www.google.com/accounts/',
                         authorize_url='https://accounts.google.com/o/oauth2/auth',
                         request_token_url=None,
                         request_token_params={'scope': 'https://www.googleapis.com/auth/userinfo.email',
                                               'response_type': 'code'},
                         access_token_url='https://accounts.google.com/o/oauth2/token',
                         access_token_method='POST',
                         access_token_params={'grant_type': 'authorization_code'},
                         consumer_key=GOOGLE_CLIENT_ID,
                         consumer_secret=GOOGLE_CLIENT_SECRET)
    	else:
    		import pycas
    		CAS_SERVER="https://cas.byu.edu"
    		SERVICE_URL="https://zelda.byu.edu/api/devel/account/login"
    		status,id,cookie = pycas.login(CAS_SERVER,SERVICE_URL)
    		session["authlogin"]=True
    		return jsonify({"status":status,"id":id,"cookie":cookie})
    else:
    	if provider=="google":
            access_token = access_token[0]
            headers = {'Authorization': 'OAuth '+access_token}
            req = Request('https://www.googleapis.com/oauth2/v1/userinfo',None, headers)
        try:
            res = urlopen(req)
        except URLError, e:
            if e.code == 401:
                # Unauthorized - bad token
                session.pop('access_token', None)
                return redirect(url_for('login'))
            return res.read()
        return res.read()



@app.route('/<collection>', methods=['GET','POST','OPTIONS'])
@app.route('/<collection>/<id>', methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def Collection(collection,id=None):
    if collection in resource_lookup:
        coll=resource_lookup[collection](request)
        return coll.dispatch(id)
    else:
    	return endpoint_404()

@app.route('/')
def index():
    return jsonify({"API":"Humvideo","Version":2})
