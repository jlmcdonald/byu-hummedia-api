from datetime import datetime
from flask import Flask, request, Response, jsonify
from mongokit import ObjectId
from models import connection as client
from config import *
from helpers import *

app = Flask(__name__)
db=client.hummedia
ags=db.assetgroups
assets=db.assets

@app.route('/collection', methods=['GET','POST','OPTIONS'])
@app.route('/collection/<pid>', methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def AssetGroup(pid=None):
    ags=db.assetgroups
    if request.method in ["POST","PUT","PATCH"]:
	if request.method =="PATCH":
	    d=ags.AssetGroup.find_one({'_id': ObjectId(pid)})
	else:
	    d=ags.AssetGroup()	    
	    d["_id"]=ObjectId() if request.method=="POST" else ObjectId(pid)
	    d["@graph"]["dc:identifier"] = "hummedia:id/collection/%s" % (str(d["_id"]))
	    d["@graph"]["pid"] = str(d["_id"])
	if "type" in request.json:
	    d["@graph"]["dc:type"]="hummedia:type/"+request.json["type"]
	for (k,v) in request.json.items():
	    if k in ags.AssetGroup.structure['@graph'] and k not in ["dc:identifier","pid","dc:type"]:
		d["@graph"][k]=unicode(v) if k in ["dc:title","dc:description"] else v
	try:
	    d.save()
	    resp=jsonify({"success":True,"id":d["@graph"]["pid"]})
	except Exception as e:
	    resp=Response("The request was malformed: %s" % (e),status=400,mimetype="text/plain")		
    elif request.method=="GET":
	q={"@graph.dc:creator":request.args.get("dc:creator")} if request.args.get("dc:creator",False) else {}
	if pid:
	    q['_id']=ObjectId(pid)
	    d=ags.find_one(q)
	    if d:
		v=assets.find({"@graph.ma:isMemberOf":d["_id"]})
		d["@graph"]["videos"]=[]
		for vid in v:
			if request.args.get("full",False):
				resource=assets.Video.uri_pattern(vid["@graph"]["pid"],apihost)	
				vid["@graph"]["type"]=resolve_type(vid["@graph"]["dc:type"])
				vid["@graph"]["resource"]=resource
				d["@graph"]['videos'].append(vid["@graph"])
			else:
				d["@graph"]["videos"].append(assets.Video.make_part(vid["@graph"],apihost,request.args.get("part","details")))
		d["@graph"]["resource"]=ags.AssetGroup.uri_pattern(d["@graph"]["pid"],apihost)
		d["@graph"]["type"]=resolve_type(d["@graph"]["dc:type"])
		resp=mongo_jsonify(d["@graph"])
	    else:
		resp=mongo_jsonify([])
	else:
	    a=ags.find(q)
	    aglist=[]
	    for d in a:
		d["@graph"]["resource"]=ags.AssetGroup.uri_pattern(d["@graph"]["pid"],apihost)
		d["@graph"]["type"]=resolve_type(d["@graph"]["dc:type"])
		aglist.append(d["@graph"])
	    resp=mongo_jsonify(aglist)
    elif request.method=="DELETE" and pid:
	    d=ags.AssetGroup.find_one({'_id': ObjectId(pid)})
	    try:
		d.delete()
		resp=jsonify({"success":"True"})
	    except Exception as e:
		resp=Response("The request was malformed: %s" % (e),status=400,mimetype="text/plain")			
    resp.headers['Last-Modified'] = datetime.now()
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
    return resp 

@app.route('/video',methods=['GET','POST','OPTIONS'])
@app.route('/video/<pid>',methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def Video(pid=None):
    if request.method in ["POST","PUT","PATCH"]:
	if request.method == "PATCH":
	    d=assets.Video.find_one({'_id': ObjectId(pid)})
	else:
	    d=assets.Video()
	    d["_id"]=ObjectId() if request.method=="POST" else ObjectId(pid)
	    d["@graph"]["dc:identifier"] = "hummedia:id/video/%s" % (str(d["_id"]))
	    d["@graph"]["pid"] = str(d["_id"])	    
	if "type" in request.json:
	    d["@graph"]["dc:type"]="hummedia:type/"+request.json["type"]
	for (k,v) in request.json.items():
	    if k in assets.Video.structure['@graph'] and k not in ["dc:identifier","pid","dc:type"]:
		if k in ["ma:features","ma:contributor"]:
		    for i in v:
			d["@graph"][k].append({"@id":i["@id"],"name":unicode(i["name"])})
		elif k in ["ma:isCopyrightedBy","ma:hasGenre"]:
		    d["@graph"][k]={"@id":v["@id"],"name":unicode(["name"]) }
		    d["@graph"][k]=ObjectId(v)
		elif assets.Video.structure['@graph'][k]==type(u""):
		    d["@graph"][k]=unicode(v)
		elif type(assets.Video.structure['@graph'][k])==type([]):
		    d["@graph"][k]=[]
		    for i in v:
			data=ObjectId(i) if k in ["ma:isMemberOf"] else i
			d["@graph"][k].append(data)		
		else: 
		    d["@graph"][k]=v
	try:
	    d.save()
	    resp=jsonify({"success":True,"id":d["@graph"]["pid"]})
	except Exception as e:
	    resp=Response("The request was malformed: %s" % (e),status=400,mimetype="text/plain")	
    elif request.method=="GET":
	q={}
	if pid:
	    q['_id']=ObjectId(pid)
	    d=assets.find_one(q)
	    if d:
		d["@graph"]["resource"]=assets.Video.uri_pattern(d["@graph"]["pid"],apihost)	
		d["@graph"]["type"]=resolve_type(d["@graph"]["dc:type"])
		d["@graph"]["path"]=assets.Video.uri_pattern(d["@graph"]["ma:locator"],host)
		resp=mongo_jsonify(d["@graph"])
	    else:
		resp=mongo_jsonify([])
	else:
	    v=request.args.get("q",False)
	    if v:
		q["$or"]=[{"@graph.ma:title":{'$regex':'.*'+v+'.*'}},
			{"@graph.ma:description":{'$regex':'.*'+v+'.*'}},
			{"@graph.ma:hasKeyword":{'$regex':'.*'+v+'.*'}}
			]
	    else:
		if any(x in request.args for x in ['yearfrom', 'yearto']):
		    q["@graph.ma:date"]={}
		    if "yearfrom" in request.args: 
			q["@graph.ma:date"]["$gte"]=int(request.args.get("yearfrom"))
		    if "yearto" in request.args: 
			q["@graph.ma:date"]["$lte"]=int(request.args.get("yearto"))
		elif "ma:date" in request.args:
		    q["@graph.ma:date"]=int(request.args.get("ma:date"))
		for (k,v) in request.args.items():
			if k not in ["yearfrom","yearto","ma:date","part"]:
			    q["@graph."+k]={'$regex':'.*'+v+'.*'}
	    a=assets.find(q)
	    alist=[]
	    for d in a:
		alist.append(assets.Video.make_part(d["@graph"],apihost,request.args.get("part","details")))
	    resp=mongo_jsonify(alist)
    elif request.method=="DELETE" and pid:
	    d=assets.Video.find_one({'_id': ObjectId(pid)})
	    try:
		d.delete()
		resp=jsonify({"success":"True"})
	    except Exception as e:
		resp=Response("The request was malformed: %s" % (e),status=400,mimetype="text/plain")
    resp.headers['Last-Modified'] = datetime.now()
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
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

@app.route('/language',methods=['GET'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def languages():
    from langs import langs
    return list_jsonify(langs)

@app.route('/')
def index():
    return jsonify({"API":"Humvideo","Version":2})
