from flask import request, jsonify, session
from helpers import crossdomain, endpoint_404, mongo_jsonify
from resources import *
from config import CROSS_DOMAIN_HOSTS
from hummedia import app

resource_lookup={"annotation":Annotation,"collection":AssetGroup,"video":MediaAsset, "account":UserProfile}

@app.route('/cookietest',methods=['GET'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def cookietest():
	session['cookie_test']="we are here!"
	cookie_packet={"session_cookie_path":app.config['SESSION_COOKIE_PATH'],"session_cookie_domain":app.config['SESSION_COOKIE_DOMAIN'],"session_cookie_name":app.config['SESSION_COOKIE_NAME'],"session_cookie_secure":app.config['SESSION_COOKIE_SECURE'],"cookie_test":session.get('cookie_test')}
	return jsonify(cookie_packet)

@app.route('/language',methods=['GET'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def languages():
	from langs import langs
	return mongo_jsonify(langs)

@app.route('/courseDepartments',methods=['GET'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def getCourseDepartments():
	from programs import programs
	return mongo_jsonify(programs)

@app.route('/<collection>', methods=['GET','POST','OPTIONS'])
@app.route('/<collection>/<id>', methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'])
@crossdomain(origin=CROSS_DOMAIN_HOSTS,headers=['Origin','x-requested-with','accept','Content-Type'],credentials=True)
def Collection(collection,id=None):
	if collection in resource_lookup:
		coll=resource_lookup[collection](request)
		return coll.dispatch(id)
	else:
		return endpoint_404()

@app.route('/text/<filename>',methods=['DELETE','PUT'])
def modify_subtitle(filename):
    video = MediaAsset(request)

    if request.method == 'DELETE':
        return video.delete_subtitle(filename)
    elif request.method == 'PUT':
        replacement = request.files['subtitle']
        return video.update_subtitle(filename, replacement)

@app.route('/')
def index():
	return jsonify({"API":"Humvideo","Version":2})
