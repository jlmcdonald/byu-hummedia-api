from flask import Flask, request
from helpers import crossdomain
from resources import *

app = Flask(__name__)

resource_lookup={"annotation":Annotation,"collection":AssetGroup,"video":MediaAsset}

@app.route('/language',methods=['GET'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def languages():
    from langs import langs
    return list_jsonify(langs)

@app.route('/<collection>', methods=['GET','POST','OPTIONS'])
@app.route('/<collection>/<pid>', methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def Collection(collection,pid=None):
    if collection in resource_lookup:
        coll=resource_lookup[collection](request)
        return coll.dispatch(pid)

@app.route('/')
def index():
    return jsonify({"API":"Humvideo","Version":2})
