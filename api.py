import json,os,queries,re
from lxml import etree
from fedora.fedoraclient import FedoraClient
from fedora.foxml import Foxml
from fedora.creds import creds
from fedora.config import *
from services.namespaces import *
from datetime import datetime, timedelta
from flask import Flask, request, Response, jsonify, current_app
from functools import update_wrapper
app = Flask(__name__)

script_path = os.path.dirname(__file__)
style_path = script_path+"/styles/"
type_descs={"HumVideoMovingImage": "Video","EditedHumVideoMovingImage":"Video","HumTVMovingImage":"TV Recording","YTMovingImage":"Youtube Video","VimeoMovingImage":"Vimeo Video","MovingImage":"Other Video"}
UNSUPPORTED_FORMAT=Response("That format is not currently supported.",status=400,mimetype="text/plain")
NOT_FOUND=Response("That object could not be found.",status=404,mimetype="text/plain")
BAD_REQUEST=Response("The request was malformed in some way.",status=400,mimetype="text/plain")

def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
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
            return resp

        f.provide_automatic_options = False
        f.required_methods=['OPTIONS']
        return update_wrapper(wrapped_function, f)
    return decorator    

def xmlify(xmlstring):
    return Response(xmlstring,status=200,mimetype="text/xml")

def list_jsonify(listobj):
    return Response(json.dumps(listobj),status=200,mimetype="application/json")

def xslTransform(obj,style,nojson=False,params=[]):
    style=open(style_path+style)
    transform=etree.XSLT(etree.XML(style.read()))
    transformed_string=str(transform(obj))
    for param in params:
	transformed_string=transformed_string.replace(param['old'],param['new'])
    if nojson:
    	return transformed_string
    else:
    	return json.loads(''.join(c for c in transformed_string if ord(c) >= 32))

@app.route('/test/<pid>',methods=["GET","OPTIONS","POST"])
@crossdomain(origin='*')
def test(pid=None):
	return Response(request.json["title"])

@app.route('/collection', methods=['GET','POST','OPTIONS'])
@app.route('/collection/<pid>', methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def Collection(pid=None):
    client=FedoraClient(True,creds)
    if request.method in ["POST","PUT","PATCH"]:
	if request.method=="POST":
            if not pid:
	    	pid=client.getNextPid("collection")
	    (namespace,id) = pid.split(":")
	    foxml = Foxml(id,namespace,owner=request.json["creator"])
	    foxml.buildDublinCore(request.json)
	    foxml.buildRdf("VideoCollectionModel","collection")
	    if client.ingest(foxml.buildFoxml(),pid,request.json["title"]) == pid:
		resp=jsonify({"success":True,"identifier":pid})
	    else:
		resp=jsonify({"success":False})
	elif pid and request.method in ["PUT","PATCH"]:
	    dc=client.getDataStream(pid,"DC")
	    for att in ["title","description","coverage","creator"]:
		if (att in request.json and request.method=="PATCH") or request.method=="PUT":
		    dc.find(".//"+DC+att).text=request.json.get(att)
	    if client.modifyDatastream(pid,"DC",etree.tostring(dc,pretty_print=True)):
		resp=jsonify({"success":True,"identifier":pid})
	    else:
		resp=jsonify({"success":False})		
	else:
	    resp=BAD_REQUEST		
    elif request.method=="GET":
	format = request.args.get("format","json")
	filter = request.args.get("filter",None)
	full=True if request.args.get("full")=="true" else request.args.get("full")
	count=False if request.args.get("count")!="true" else request.args.get("count")	
	kwargs={}
	if filter=="creator":
	    kwargs['netid']=request.args.get('netid')
	if pid:
		if client.pidExists(pid):
			obj=client.getDataStream(pid,"DC")
			if format=="xml":
				resp=xmlify(etree.tostring(obj,pretty_print=True))
			elif format=="json":
				collection=xslTransform(obj,"dc2json.xsl")
				collection["videos"]=[]
				collection["uri"]="%s/collection/%s" % (apihost,pid)
				kwargs['pid']=pid
				videos=etree.fromstring(client.risearch(queries.mediaInCollection(**kwargs),'itql','text'))
				for result in videos[1]:
				    pid=result.findtext(".//"+SPARQL+"pid")
				    video={"pid":pid,"uri":"%s/video/%s" % (apihost,pid)}
				    if full==True:
					details=client.getDataStream(pid,"DC")					
					video=dict(video.items()+xslTransform(details,"dc2json.xsl").items())
					video["type"]=type_descs[video["type"]]					
				    collection["videos"].append(video)
				resp=jsonify(collection)
			else:
				resp=UNSUPPORTED_FORMAT
		else:
			resp=NOT_FOUND			
	else:		
	    collections=etree.fromstring(client.risearch(queries.collectionList(filter,**kwargs),'sparql','text'))
	    if format=="xml":
		    resp=xmlify(etree.tostring(collections,pretty_print=True))
	    elif format=="json":
		    packet={"count":0,"collections":[]}
		    for result in collections[1]:
			    pid=result.findtext(".//"+SPARQL+"pid")
			    packet["collections"].append({"title":result.findtext(".//"+SPARQL+"title"),"identifier":pid,"uri":"%s/collection/%s" % (apihost,pid)})
		    packet["count"]=len(packet["collections"])
		    if not count:
			resp=list_jsonify(packet['collections'])
		    else:
			resp=jsonify(packet)
	    else:
		    resp=UNSUPPORTED_FORMAT
    elif request.method=="DELETE":
	if client.pidExists(pid):
	    client.purge(pid)
	    if client.pidExists(pid):
	        resp=jsonify({"success":False})
	    else:
	        resp=jsonify({"success":True,"identifier":pid})
	else:
	    resp=NOT_FOUND
    resp.headers['Last-Modified'] = datetime.now()
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
    return resp 

@app.route('/video',methods=['GET','POST','OPTIONS'])
@app.route('/video/<pid>',methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def Video(pid=None):
    if request.method=="GET":
	client=FedoraClient(True,creds)
	format = request.args.get("format","json")
	filter = request.args.get("filter",None)
	q = request.args.get("q",None)
	kwargs={}
	if q:
	    kwargs["query"]=[]
	    searchtype=request.args.get("searchtype","keyword")
	    if searchtype=="keyword":
		rq=[t.strip('"') for t in re.findall(r'[^\s"]+|"[^"]*"', q)]
		for phrase in rq:
		    kwargs["query"].append("(dc.title:%s OR dc.description:%s OR dc.subject:%s)" % (phrase,phrase,phrase))
	    else:
		params=q.split("&")
		for p in params:
		    if p.strip():
			kwargs["query"].append(p)
	    r=client.gSearch(" AND ".join(kwargs["query"]))
	    if format=="xml":
		resp=xmlify(etree.tostring(r,pretty_print=True))
	    elif format=="json":	
		resp=list_jsonify(xslTransform(r,"gsearch2json.xsl",params=[{'old':'%APIHOST%','new':apihost}]))
	    else:
		resp=UNSUPPORTED_FORMAT		
	elif pid:
	    if client.pidExists(pid):
		    obj=client.getDataStream(pid,"DC")
		    if format=="xml":
			resp=xmlify(etree.tostring(obj,pretty_print=True))
		    elif format=="json":
			video=xslTransform(obj,"dc2json.xsl")
			video["uri"]="%s/video/%s" % (apihost,pid)
			video["type"]=type_descs[video["type"]]
			resp=jsonify(video)
		    else:
			resp=UNSUPPORTED_FORMAT
	    else:
			resp=NOT_FOUND
	else:
	    videos=etree.fromstring(client.risearch(queries.videoList(filter,**kwargs),'sparql','text'))
	    if format=="xml":
		    resp=xmlify(etree.tostring(collections,pretty_print=True))
	    elif format=="json":
		    packet={"count":0,"videos":[]}
		    for result in videos[1]:
			    pid=result.findtext(".//"+SPARQL+"pid")
			    packet['videos'].append({"title":result.findtext(".//"+SPARQL+"title"),"identifier":pid,"uri":"%s/video/%s" % (apihost,pid)})
		    packet["count"]=len(packet["videos"])
		    resp=jsonify(packet)
	    else:
		    resp=UNSUPPORTED_FORMAT
	return resp 

#class Playlist(webapp2.RequestHandler):
    #def get(self,pid=None):
	#client=FedoraClient(True,creds)
	#format = self.request.get("format")
	#filter = self.request.get("filter")
	#kwargs={}
	#if filter=="video":
		#kwargs["pid"]=self.request.get("pid")
	#self.response.headers={ "Access-Control-Allow-Origin":"*",
				#"Access-Control-Allow-Methods":"GET",
				#"Access-Control-Max-Age":"3600"}
	#if pid:
		#if pid[-1]=="/":
			#pid=pid[:-1]
		#if client.pidExists(pid):
			#v=client.getDataStream(pid,"VCP")
			#if format=="xml":
				#self.response.content_type="text/xml"
				#self.response.write(etree.tostring(v,pretty_print=True))
			#elif format=="json" or format is None:
				#style=open(style_path+"vcp2json.xsl")
				#transform=etree.XSLT(etree.XML(style.read()))
				#self.response.content_type="application/json"
				#self.response.write(str(transform(v)))
			#else:
				#self.response.content_type="text/plain"
				#self.response.write("That format is not currently supported.")
		#else:
			#self.response.write("That playlist could not be found")
			
	#else:		
		#playlists=etree.fromstring(client.risearch(queries.vcpList(filter,**kwargs),'sparql','text'))
		#if format=="xml":
			#self.response.content_type="text/xml"
			#self.response.write(etree.tostring(playlists,pretty_print=True))
		#elif format=="json" or format is None:
			#collections=[]
			#for result in playlists[1]:
				#collections.append({"title":result.findtext(".//"+SPARQL+"title"),"pid":result.findtext(".//"+SPARQL+"pid")})
			#self.response.content_type="application/json"
			#self.response.write(json.dumps(collections))
		#else:
			#self.response.content_type="text/plain"
			#self.response.write("That format is not currently supported.")

			##(r'/collection/(.*)/?',Collection),
			##(r'/video/(.*)/?',Video),
			##(r'/playlist/(.*)/?',Playlist),

@app.route('/')
def index():
    return 'Humvideo Repo API'
