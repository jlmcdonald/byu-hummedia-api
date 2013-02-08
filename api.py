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
annotations=db.annotations

@app.route('/annotation', methods=['GET','POST','OPTIONS'])
@app.route('/annotation/<pid>', methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def Annotation(pid=None):
	if request.method in ["POST","PUT","PATCH"]:
		if request.method =="PATCH":
			d=annotations.AnnotationList.find_one({'_id': ObjectId(pid)})
		else:
			d=annotations.AnnotationList()
			d["_id"]=ObjectId() if request.method=="POST" else ObjectId(pid)
			d["@graph"]["dc:identifier"] = "hummedia:id/annotation/%s" % (str(d["_id"]))
			d["@graph"]["pid"] = str(d["_id"])
		for (k,v) in request.json.items():
			if k=="dc:relation":
				d["@graph"][k]=ObjectId(v)
			elif k=="dc:title":
				d["@graph"]["dc:title"]=unicode(v)
			elif k=="vcp:playSettings":
				for (i,j) in v.items():
					if i=="vcp:frameRate":
						d["@graph"]["vcp:playSettings"][i]=float(j)
					elif i=="vcp:videoCrop":
						d["@graph"]["vcp:playSettings"][i]=j
					else:
						d["@graph"]["vcp:playSettings"][i]=int(j)
			elif k=="vcp:commands":
				d["@graph"]["vcp:commands"]=[] 
				for i in v:
					d["@graph"]["vcp:commands"].append(i)
			else:
				d["@graph"][k]=v
		try:
			d.save()
			resp=jsonify({"success":True,"id":d["@graph"]["pid"]})
		except Exception as e:
			resp=Response("The request was malformed: %s" % (e),status=400,mimetype="text/plain")
	elif request.method=="GET":
		if request.args.get("dc:relation",False):
			q={"@graph.dc:relation":request.args.get("dc:relation")}
		elif request.args.get("dc:creator",False):
			q={"@graph.dc:creator":request.args.get("dc:creator")}
		else:
			q={}
		if pid:
			q['_id']=ObjectId(pid)
			d=annotations.find_one(q)
			if d:
				d["@graph"]["resource"]=uri_pattern(d["@graph"]["pid"],apihost+"/annotation")
				resp=mongo_jsonify(d["@graph"])
			else:
				resp=mongo_jsonify([])
		else:
			a=annotations.find(q)
			alist=[]
			for d in a:
				d["@graph"]["resource"]=uri_pattern(d["@graph"]["pid"],apihost+"/annotation")
				alist.append(d["@graph"])
			resp=mongo_jsonify(alist)
	elif request.method=="DELETE" and pid:
		d=annotations.AnnotationList.find_one({'_id': ObjectId(pid)})
		try:
			d.delete()
			resp=jsonify({"success":"True"})
		except Exception as e:
			resp=Response("The request was malformed: %s" % (e),status=400,mimetype="text/plain")			
	resp.headers['Last-Modified'] = datetime.now()
	resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
	return resp 

@app.route('/collection', methods=['GET','POST','OPTIONS'])
@app.route('/collection/<pid>', methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def AssetGroup(pid=None):
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
				v=assets.find({"@graph.ma:isMemberOf.@id":d["_id"]})
				d["@graph"]["videos"]=[]
				for vid in v:
					if request.args.get("full",False):
						resource=uri_pattern(vid["@graph"]["pid"],apihost+"/video")	
						vid["@graph"]["type"]=resolve_type(vid["@graph"]["dc:type"])
						vid["@graph"]["resource"]=resource
						d["@graph"]['videos'].append(vid["@graph"])
					else:
						d["@graph"]["videos"].append(assets.Video.make_part(vid["@graph"],apihost,request.args.get("part","details")))
				d["@graph"]["resource"]=uri_pattern(d["@graph"]["pid"],apihost+"/collection")
				d["@graph"]["type"]=resolve_type(d["@graph"]["dc:type"])
				resp=mongo_jsonify(d["@graph"])
			else:
				resp=mongo_jsonify([])
		else:
			a=ags.find(q)
			aglist=[]
			for d in a:
				d["@graph"]["resource"]=uri_pattern(d["@graph"]["pid"],apihost+"/collection")
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
				    if k=="ma:title":
						d["ititle"]=unicode(v).lower()
				elif assets.Video.structure['@graph'][k]==type(2):
					d["@graph"][k]=int(v)
				elif assets.Video.structure['@graph'][k]==type(2.0):
					d["@graph"][k]=float(v)
				elif type(assets.Video.structure['@graph'][k])==type([]):
				    d["@graph"][k]=[]
				    for i in v:
						if k=="ma:isMemberOf":
							membership={}
							for (g,h) in i.items():
								membership[g]=ObjectId(h) if g=="@id" else h
							d["@graph"]["ma:isMemberOf"].append(membership)
						else:
							d["@graph"][k].append(i)	
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
				d["@graph"]["resource"]=uri_pattern(d["@graph"]["pid"],apihost+"/video")	
				d["@graph"]["type"]=resolve_type(d["@graph"]["dc:type"])
				if d["@graph"]["type"]=="humvideo":
					d["@graph"]["url"]=uri_pattern(d["@graph"]["ma:locator"],host+"/video")
				elif d["@graph"]["type"]=="yt":
					d["@graph"]["url"]=uri_pattern(d["@graph"]["ma:locator"],"http://youtu.be")
				resp=mongo_jsonify(d["@graph"])
			else:
				resp=mongo_jsonify([])
		else:
			v=request.args.get("q",False)
			if v:
				q["$or"]=[{"ititle":{'$regex':'.*'+v.lower()+'.*'}},
					{"@graph.ma:description":{'$regex':'.*'+v+'.*', '$options':'i'}},
					{"@graph.ma:hasKeyword":{'$regex':'.*'+v+'.*', '$options': 'i'}}
					]
			else:
				if any(x in request.args for x in ['yearfrom', 'yearto']):
					q["@graph.ma:date"]={}
					if "yearfrom" in request.args: 
						q["@graph.ma:date"]["$gte"]=int(request.args.get("yearfrom"))
					if "yearto" in request.args and request.args.get("yearto").strip()!="": 
						q["@graph.ma:date"]["$lte"]=int(request.args.get("yearto"))
				elif "ma:date" in request.args:
					q["@graph.ma:date"]=int(request.args.get("ma:date"))
				for (k,v) in request.args.items():
					if k == "ma:title":
						q["ititle"]=v.lower()
					elif k in ["ma:description","ma:hasKeyword"]:
						q["@graph."+k]={'$regex':'.*'+v+'.*', '$options': 'i'}
					elif k not in ["yearfrom","yearto","ma:date","part"]:
						q["@graph."+k]=v
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

@app.route('/language',methods=['GET'])
@crossdomain(origin='*',headers=['origin','x-requested-with','accept','Content-Type'])
def languages():
    from langs import langs
    return list_jsonify(langs)

@app.route('/')
def index():
    return jsonify({"API":"Humvideo","Version":2})
