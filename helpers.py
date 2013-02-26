from flask import request, Response, jsonify, current_app
from datetime import datetime, timedelta, date
from functools import update_wrapper
from mongokit import ObjectId
from models import connection as conn
import json

class NoModelException(Exception):
    pass

class Resource():
    model=conn.hummeda.annotations.AnnotationList
    collection=conn.test.test
    namespace="hummedia:id/object"
    endpoint="test"
    bundle=None
    request=None
    
    def __init__(self,request):
        self.request=request
    
    if not model:
        raise NoModelException("You have to declare the model for the resource")

    def patch(self,pid):
        self.bundle=self.model.find_one({'_id': ObjectId(pid)})
        self.set_attrs()
        return self.save_bundle()

    def post(self,pid=None):
        self.bundle=self.model()
        self.bundle["_id"]=ObjectId(pid)
        self.preprocess_bundle()
        self.set_attrs()
        return self.save_bundle()

    def put(self,pid):
        return self.post(pid)
            
    def get(self,pid):
        q=self.set_query()
        if pid:
            q['_id']=ObjectId(pid)
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

    def delete(self,pid):
        self.bundle=self.model.find_one({'_id': ObjectId(pid)})
        return self.delete_obj()
        
    def get_bundle(self,q):
        return self.collection.find_one(q)

    def get_list(self):
        return mongo_jsonify(self.bundle)

    def serialize_bundle(self,payload):
        return mongo_jsonify(payload)
        
    def set_resource(self):
        pass

    def set_attrs(self):
        pass

    def preprocess_bundle(self):
        self.bundle["@graph"]["dc:identifier"] = "%s/%s" % (self.namespace,str(self.bundle["_id"]))
        self.bundle["@graph"]["pid"] = str(self.bundle["_id"])

    def save_bundle(self):
        try:
            self.bundle.save()
            return jsonify({"success":True,"id":self.bundle["@graph"]["pid"]})
        except Exception as e:
            return Response("The request was malformed: %s" % (e),status=400,mimetype="text/plain")
    
    def client_process(self):
        return self.bundle
    
    def set_query(self):
        return {}

    def delete_obj(self):
        try:
            self.bundle.delete()
            return jsonify({"success":"True"})
        except Exception as e:
            return Response("The request was malformed: %s" % (e),status=400,mimetype="text/plain")

    def dispatch(self,pid):
        methods={"GET":self.get,"POST":self.post,"PUT":self.put,"PATCH":self.patch,"DELETE":self.delete}
        return methods[self.request.method](pid)

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

def parse_npt(nptstr):
    times=nptstr.split(":")[1]
    (start,end)=times.split(",")
    return {"start":start,"end":end}

def resolve_type(t):
    return t.split("/")[-1]

def uri_pattern(pid,host=""):
    return "%s/%s" % (host,pid)
