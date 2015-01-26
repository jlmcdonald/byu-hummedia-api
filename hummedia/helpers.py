from flask import request, Response, jsonify, current_app, session
from flask_oauth import OAuth
from datetime import datetime, timedelta, date
from functools import update_wrapper
from mongokit import cursor
from bson import ObjectId
from models import connection
from config import APIHOST, YT_SERVICE, BYU_WS_ID, BYU_SHARED_SECRET
from urllib2 import Request, urlopen, URLError
import json, byu_ws_sdk, requests, re, os, mimetypes
import time


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

class Resource(object):
    collection=connection.test.test
    model=collection.TestObject
    namespace="hummedia:id/object"
    endpoint="test"
    bundle=None
    request=None
    part=None
    manual_request={}
    disallowed_atts=[]
    override_only_triggers=[]
    override_only=False
    
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
        self.set_disallowed_atts()
        if request.args.get('inhibitor') in self.override_only_triggers:
                self.override_only=True
    
    if not model:
        raise NoModelException("You have to declare the model for the resource")

    def set_disallowed_atts(self):
        pass

    def patch(self,id):
        from bson.objectid import ObjectId
        self.bundle=self.model.find_one({'$or': [{'_id': str(id)}, {'_id': ObjectId(id)}]})
        if self.acl_write_check(self.bundle):
            setattrs=self.set_attrs()
	    if setattrs.get("resp")==200:
		return self.save_bundle()
	    else:
		return bundle_400(setattrs.get("msg"))    
        else:
            return action_401()

    def post(self,id=None):
        if self.acl_write_check():
            self.bundle=self.model()
            self.bundle["_id"]=str(ObjectId(id))
            self.preprocess_bundle()
            setattrs=self.set_attrs()
	    if setattrs.get("resp")==200:
		return self.save_bundle()
	    else:
		return bundle_400(setattrs.get("msg"))    
        else:
            return action_401()

    def put(self,id):
        return self.post(id)
            
    def get(self,id,limit=0,projection=None):
        q=self.set_query()
        if id:
            try:
                q['_id']=str(ObjectId(id))
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
            proj_dict = None

            if projection is not None:
              proj_dict = {x:1 for x in projection}

            self.bundle=self.collection.find(q, proj_dict).limit(limit)
            return self.get_list()

    def delete(self,id):
        if self.acl_write_check():
            self.bundle=self.model.find_one({'_id': str(id)})
            self.delete_associated(id)
            return self.delete_obj()
        else:
            return action_401()

    def acl_read_check(self,obj,username,allowed,is_nested_obj=False,role="student"):
        if self.read_override(obj,username,role):
            return True
        if not self.override_only:
            return any([role=="faculty",obj["@graph"].get("dc:coverage") in allowed,username in obj["@graph"].get("dc:rights",{}).get("read",[]),not is_nested_obj and obj["@graph"].get("dc:creator")==username])
        return False
        
    def read_override(self,obj,username,role):
        return False

    def acl_write_check(self,bundle=None):
        from auth import get_profile
        atts=get_profile()
        if atts['superuser'] or (atts['role']=='faculty' and not bundle):
            return True
        if bundle:
            if bundle["@graph"].get("dc:creator")==atts['username'] or atts['username'] in bundle['@graph']["dc:rights"]["write"]:
                return True
	return False
   
    def auth_filter(self,bundle=None):
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
                if not self.acl_read_check(obj,username,allowed,role=role):
                    bundle.remove(obj)
        elif not self.acl_read_check(bundle,username,allowed,role=role):
            bundle={}
        return bundle
    
    def retain(self,obj,username):
        return False
        
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
            if k in self.model.structure and k not in self.disallowed_atts:
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
	return ({"resp":200})

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

    def delete_associated(self,id):
        pass

    def dispatch(self,id):
        methods={"GET":self.get,"POST":self.post,"PUT":self.put,"PATCH":self.patch,"DELETE":self.delete}
        return methods[self.request.method](id)

class mongokitJSON(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)): 
            return int(time.mktime(obj.timetuple())) 
        else:
            try:
                return json.JSONEncoder.default(self, obj)
            except TypeError:
                return str(obj)

def get_enrollments():
    from auth import get_user, get_userid
    if not get_user():
        return []
    if get_user()=="B3yGtjkIFz":
        return["ENGL 999 001 20135","SPAN 999 001 20135"]
    if "enrollments" in session:
        return session.get('enrollments')
    url="https://ws.byu.edu/rest/v1.0/academic/registration/studentschedule/"+get_userid()+"/"+getCurrentSem()
    headerVal = byu_ws_sdk.get_http_authorization_header(BYU_WS_ID, BYU_SHARED_SECRET, byu_ws_sdk.KEY_TYPE_API,byu_ws_sdk.ENCODING_NONCE,actor=get_user(),url=url,httpMethod=byu_ws_sdk.HTTP_METHOD_GET,actorInHash=True)
    res=requests.get(url, headers={'Authorization': headerVal})
    courses=[]
    try:
	content=json.loads(res.content)['WeeklySchedService']['response']
    except ValueError:
        content={"schedule_table":[]}
    for course in content["schedule_table"]:
        courses.append(" ".join((course['course'],course['section'],content['year_term'])))
    session['enrollments']=courses
    return courses

def is_enrolled(obj):
    try:
        return not set(get_enrollments()).isdisjoint(obj["@graph"]["dc:relation"])
    except (TypeError,KeyError):
        return False

def crossdomain(origin=None, methods=None, headers=None, credentials=False,
                max_age=21600, attach_to_all=True,
                automatic_options=True,nocache=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
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
    end=end if end.strip() else "0"
    return {"start":start,"end":end}

def resolve_type(t):
    return t.split("/")[-1]

def uri_pattern(id,host=""):
    return "%s/%s" % (host,id)

def getYtThumbs(ids=[]):
    ytThumbs={}
    if len(ids):
        req=Request(YT_SERVICE+"&id=%s" % (",".join(ids)))

        try:
          res=urlopen(req)
          j=json.loads(res.read())
          res.close()
        except:
          return dict.fromkeys(ids, {'poster': None, 'thumb': None})

        for vid in j["items"]:
            ytThumbs[vid["id"]]={"poster":vid["snippet"]["thumbnails"]["high"]["url"],"thumb":vid["snippet"]["thumbnails"]["default"]["url"]}
    return ytThumbs

def getCurrentSem():
    today=datetime.now()
    sem="1"
    if today.month in [5,6]:
        sem="3"
    elif today.month in [7,8]:
        sem="4"
    elif today.month in [9,10,11,12]:
        sem="5"
    return str(today.year)+sem

def getVideoInfo(filename):
    from subprocess import check_output

    cmd = ['avprobe', filename, '-show_streams', '-show_format', '-loglevel', 'quiet']

    if check_output('avprobe -version'.split()).find('avprobe 0.8') == -1:
        cmd += ['-of','old']

    output  =  check_output(cmd)
    
    # ensure that the data we have is that for the video. doesn't include audio data
    stream_match = re.search(
        r'\[STREAM\]\s*(.*?codec_type=video.*?)\s*\[/STREAM\]',
        output,
        re.DOTALL)

    format_match = re.search(r'\[FORMAT\]\s*(.*)\[/FORMAT\]', output, re.DOTALL)
    
    lines = stream_match.group(1).splitlines() + format_match.group(1).splitlines()
    data = {line.split('=')[0].strip(): line.split('=')[1].strip() for line in lines}
    
    framerate = data['avg_frame_rate'].split('/')
    data['framerate'] = round( float(framerate[0]) / float(framerate[1]), 3)
    data['bitrate']=data['bit_rate']
    return data
