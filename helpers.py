from flask import request, Response, jsonify, current_app
from datetime import datetime, timedelta, date
from functools import update_wrapper
from mongokit import ObjectId 
from models import connection as conn
from config import apihost
import json

class NoModelException(Exception):
    pass

class Resource():
    collection=conn.test.test
    model=conn.test.test.TestObject
    namespace="hummedia:id/object"
    endpoint="test"
    bundle=None
    request=None
    part=None
    
    def __init__(self,request=None,bundle=None, client=None):
        if bundle:
            self.bundle=bundle
            self.set_resource()
            if client:
                self.part=self.client_process()
            else:
                self.part=self.serialize_bundle(self.bundle)
        else:
            self.request=request
    
    if not model:
        raise NoModelException("You have to declare the model for the resource")

    def patch(self,id):
        self.bundle=self.model.find_one({'_id': ObjectId(id)})
        self.set_attrs()
        return self.save_bundle()

    def post(self,id=None):
        self.bundle=self.model()
        self.bundle["_id"]=ObjectId(id)
        self.preprocess_bundle()
        self.set_attrs()
        return self.save_bundle()

    def put(self,id):
        return self.post(id)
            
    def get(self,id):
        q=self.set_query()
        if id:
            try:
                q['_id']=ObjectId(id)
            except Exception as e:
                return bundle_400("The ID you submitted is malformed.")
            self.bundle=self.get_bundle(q)
            if self.bundle:
                self.set_resource()
                if self.request.args.get("client",None):
                    return self.client_process()
                else:
                    return self.serialize_bundle(self.bundle)
            else:
                return bundle_404()
        else:
            self.bundle=self.collection.find(q)
            return self.get_list()

    def delete(self,id):
        self.bundle=self.model.find_one({'_id': ObjectId(id)})
        return self.delete_obj()
        
    def get_bundle(self,q):
        return self.collection.find_one(q)

    def get_list(self):
        return mongo_jsonify(list(self.bundle))

    def serialize_bundle(self,payload):
        return mongo_jsonify(payload)
        
    def set_resource(self):
        self.bundle["resource"]=uri_pattern(str(self.bundle["_id"]),apihost+"/"+self.endpoint)

    def set_attrs(self):
        for (k,v) in self.request.json.items():
            if k in self.model.structure:
                if self.model.structure[k]==type(2):
                    self.bundle[k]=int(v)
                elif self.model.structure[k]==type(2.0):
                    self.bundle[k]=float(v)
                elif self.model.structure[k]==type(u""):
                    self.bundle[k]=unicode(v)
                elif type(self.model.structure[k])==type([]):
                    self.bundle[k]=[]
                    for i in v:
                        self.bundle[k].append(i)  
                else: 
                    self.bundle[k]=v

    def preprocess_bundle(self):
        pass

    def save_bundle(self):
        try:
            self.bundle.save()
            return jsonify({"success":True,"id":str(self.bundle["_id"])})
        except Exception as e:
            return bundle_400("The request was malformed: %s" % (e))
    
    def client_process(self):
        return self.bundle
    
    def set_query(self):
        return {}

    def delete_obj(self):
        try:
            self.bundle.delete()
            return jsonify({"success":"True"})
        except Exception as e:
            return bundle_400("The request was malformed: %s" % (e))

    def dispatch(self,id):
        methods={"GET":self.get,"POST":self.post,"PUT":self.put,"PATCH":self.patch,"DELETE":self.delete}
        return methods[self.request.method](id)

class mongokitJSON(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)): 
            return int(time.mktime(obj.timetuple())) 
        elif isinstance(obj, ObjectId): 
            return str(obj)
        return json.JSONEncoder.default(self, obj)

def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True,nocache=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = f(*args, **kwargs)
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            if nocache:
                h['Last-Modified'] = datetime.now()
                h['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
            return resp
            
        f.provide_automatic_options = False
        f.required_methods=['OPTIONS']
        return update_wrapper(wrapped_function, f)
    return decorator   

def mongo_jsonify(obj):
    return Response(json.dumps(obj, cls=mongokitJSON),status=200,mimetype="application/json")

def bundle_404():
    return Response("The object was not found",status=404,mimetype="text/plain") 

def endpoint_404():
    return Response("That service does not exist",status=404,mimetype="text/plain")

def bundle_400(e):
    return Response(e,status=400,mimetype="text/plain")  

def parse_npt(nptstr):
    times=nptstr.split(":")[1]
    (start,end)=times.split(",")
    return {"start":start,"end":end}

def resolve_type(t):
    return t.split("/")[-1]

def uri_pattern(id,host=""):
    return "%s/%s" % (host,id)
