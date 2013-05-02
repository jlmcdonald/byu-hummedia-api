from flask import request, jsonify
from helpers import crossdomain, endpoint_404, mongo_jsonify
from resources import *

from hummedia import app

resource_lookup={"annotation":Annotation,"collection":AssetGroup,"video":MediaAsset, "account":UserProfile}

@app.route('/language',methods=['GET'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def languages():
	from langs import langs
	return mongo_jsonify(langs)

@app.route('/<collection>', methods=['GET','POST','OPTIONS'])
@app.route('/<collection>/<id>', methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'])
@crossdomain(origin=['http://hlrdev.byu.edu','https://hlrdev.byu.edu','http://ian.byu.edu','https://ian.byu.edu'],headers=['Origin','x-requested-with','accept','Content-Type'],credentials=True)
def Collection(collection,id=None):
	if collection in resource_lookup:
		coll=resource_lookup[collection](request)
		return coll.dispatch(id)
	else:
		return endpoint_404()

@app.route('/')
def index():
	return jsonify({"API":"Humvideo","Version":2})
