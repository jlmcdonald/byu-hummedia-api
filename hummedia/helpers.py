from flask import request, Response, jsonify, current_app
from flask_oauth import OAuth
from datetime import datetime, timedelta, date
from functools import update_wrapper
from mongokit import ObjectId, cursor 
from models import connection
from config import APIHOST
import json

class NoModelException(Exception):
    pass

class OAuthProvider():
    client_id=None
    client_secret=None
    base_url=None
    authorize_url=None
    request_token_url=None
    request_token_params={'scope': None,'response_type': 'code'}
    access_token_url=None
    token_verify_url=None
    access_token_method='POST'
    access_token_params={'grant_type': 'authorization_code'}
    oauth=OAuth()
    remote_app=None

    def __init__(self,providerService):
        self.remote_app=self.oauth.remote_app(providerService,
                        base_url=self.base_url,
                        authorize_url=self.authorize_url,
                        request_token_url=self.request_token_url,
                        request_token_params=self.request_token_params,
                        access_token_url=self.access_token_url,
                        access_token_method=self.access_token_method,
                        access_token_params=self.access_token_params,
                        consumer_key=self.client_id,
                        consumer_secret=self.client_secret)

    def get_remote_app(self):
        return self.remote_app

class Resource():
    collection=connection.test.test
    model=collection.TestObject
    namespace="hummedia:id/object"
    endpoint="test"
    bundle=None
    request=None
    part=None
    manual_request={}
    
    def __init__(self,request=None,bundle=None, client=None,**kwargs):
        if bundle:
            self.bundle=bundle
            self.set_resource()
            if client:
                self.part=self.client_process()
            else:
                self.part=self.serialize_bundle(self.bundle)
        elif request:
            self.request=request
        else:
            self.manual_request=kwargs
    
    if not model:
        raise NoModelException("You have to declare the model for the resource")

    def patch(self,id):
        self.bundle=self.model.find_one({'_id': ObjectId(id)})
        if self.acl_write_check(self.bundle):
            self.set_attrs()
            return self.save_bundle()
        else:
            return action_401()

    def post(self,id=None):
        if self.acl_write_check():
            self.bundle=self.model()
            self.bundle["_id"]=ObjectId(id)
            self.preprocess_bundle()
            self.set_attrs()
            return self.save_bundle()
        else:
            return action_401()

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
                self.bundle=self.auth_filter(self.bundle)
                if not self.bundle:
                    return action_401()
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
        if self.acl_write_check():
            self.bundle=self.model.find_one({'_id': ObjectId(id)})
            return self.delete_obj()
        else:
            return action_401()

    def acl_read_check(self,obj,username,allowed,is_nested_obj=False):
        if is_nested_obj and (obj["@graph"]["dc:coverage"] in allowed or username in obj["@graph"]["dc:rights"]["read"]):
            return True
        if obj["@graph"]["dc:coverage"] in allowed or username in obj["@graph"]["dc:rights"]["read"] or obj["@graph"]["dc:creator"]==username:
            return True
        return False

    def acl_write_check(self,bundle=None):
        from auth import get_profile
        atts=get_profile()
        return atts['superuser'] or (atts['role']=="faculty" and not bundle) or bundle["@graph"]["dc:creator"]==atts['username'] or atts['username'] in bundle['@graph']["dc:rights"]["write"]   
   
    def auth_filter(self,bundle=None,atts=None):
        from auth import get_profile
        atts=get_profile()
        if not atts['username']:
            filtered_bundle=self.acl_filter(bundle=bundle)
        elif not atts['superuser']:
            filtered_bundle=self.acl_filter(["public","BYU"],atts['username'],atts['role'],bundle)
        else:
            filtered_bundle=bundle if bundle else self.bundle
        return filtered_bundle
    
    def acl_filter(self,allowed=["public"],username="unauth",role=None,bundle=None):
        if not bundle:
            bundle=self.bundle
        if type(bundle)==cursor.Cursor:
            bundle=list(bundle)
            for obj in bundle[:]:
                if not self.acl_read_check(obj,username,allowed):
                    bundle.remove(obj)
        elif not self.acl_read_check(bundle,username,allowed):
            bundle={}
        # need student filtering by course -- they can see course collections, and their videos, if enrolled. also need to allow faculty to see private videos
        return bundle               
        
    def get_bundle(self,q):
        return self.collection.find_one(q)

    def get_list(self):
        self.bundle=self.auth_filter()
        return mongo_jsonify(list(self.bundle))

    def serialize_bundle(self,payload):
        return mongo_jsonify(payload)

    def set_resource(self):
        self.bundle["resource"]=uri_pattern(str(self.bundle["_id"]),APIHOST+"/"+self.endpoint)

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
            return self.get(self.bundle["_id"])
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
        elif obj==ObjectId(str(obj)): 
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)
        
def get_auth():
    return [get_user(),get_role(),is_superuser()]

def crossdomain(origin=None, methods=None, headers=None, credentials=False,
                max_age=21600, attach_to_all=True,
                automatic_options=True,nocache=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    #if not isinstance(origin, basestring):
    #    origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_origin():
        return request.headers.get('Origin')

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
            if origin=="*":
                h['Access-Control-Allow-Origin'] = origin
            else:
                h['Access-Control-Allow-Origin'] = get_origin()   
                if credentials:
                    h['Access-Control-Allow-Credentials'] = "true"
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

def action_401():
    return Response("You do not have permission to perform that action.",status=401,mimetype="text/plain")

def plain_resp(obj):
    return Response(obj,status=200,mimetype="text/plain")

def parse_npt(nptstr):
    times=nptstr.split(":")[1]
    (start,end)=times.split(",")
    return {"start":start,"end":end}

def resolve_type(t):
    return t.split("/")[-1]

def uri_pattern(id,host=""):
    return "%s/%s" % (host,id)
