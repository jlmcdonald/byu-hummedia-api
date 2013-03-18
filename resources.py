from datetime import datetime
from models import connection as client
from flask import Response, jsonify
from helpers import Resource, mongo_jsonify, parse_npt, resolve_type, uri_pattern, bundle_400
from mongokit import ObjectId
from config import *
import clients

db=client.hummedia
ags=db.assetgroups
assets=db.assets
annotations=db.annotations
users=db.users

class UserProfile(Resource):
    collection=users
    model=users.User
    namespace="hummedia:id/user"
    endpoint="account"

    def post(self,pid=None):
        self.bundle=self.model()
        if not pid:
            if "username" in self.request.json:
                self.bundle["_id"]=ObjectId(self.request.json.username)
            else:
                return bundle_400()
        else:
            self.bundle["_id"]=ObjectId(pid)
        self.preprocess_bundle()
        self.set_attrs()
        return self.save_bundle()
    
    def set_query(self):
        q={}
        if self.request.args.get("oauth",False):
            q["oauth"][self.request.args.get("provider")]=self.request.args.get("provider_account")
        elif self.request.args.get("email",False):
            q["email"]=self.request.args.get("email")
        return q
      
class MediaAsset(Resource):
    collection=assets
    model=assets.Video
    namespace="hummedia:id/video"
    endpoint="video"
    
    def set_query(self):
        q={}
        v=self.request.args.get("q",False)
        if v:
            cire={'$regex':'.*'+v+'.*', '$options': 'i'}
            q["$or"]=[{"ititle":cire},
            {"@graph.ma:description":cire},
            {"@graph.ma:hasKeyword":cire}
            ]
        else:
            if any(x in self.request.args for x in ['yearfrom', 'yearto']):
                q["@graph.ma:date"]={}
                if "yearfrom" in self.request.args: 
                    q["@graph.ma:date"]["$gte"]=int(self.request.args.get("yearfrom"))
                if "yearto" in self.request.args and self.request.args.get("yearto").strip()!="": 
                    q["@graph.ma:date"]["$lte"]=int(self.request.args.get("yearto"))
            elif "ma:date" in self.request.args:
                q["@graph.ma:date"]=int(self.request.args.get("ma:date"))
            for (k,v) in self.request.args.items():
                cire={'$regex':'.*'+v+'.*', '$options': 'i'}
                if k == "ma:title":
                    q["ititle"]=cire
                elif k in ["ma:description","ma:hasKeyword"]:
                    q["@graph."+k]=cire
                elif k not in ["yearfrom","yearto","ma:date","part"]:
                    q["@graph."+k]=v
        return q
        
    def get_list(self):
        alist=[]
        for d in self.bundle:
            alist.append(self.model.make_part(d["@graph"],apihost,self.request.args.get("part","details")))
        return mongo_jsonify(alist)
        
    def set_resource(self):
        self.bundle["@graph"]["resource"]=uri_pattern(self.bundle["@graph"]["pid"],apihost+"/"+self.endpoint)

    def preprocess_bundle(self):
        self.bundle["@graph"]["dc:identifier"] = "%s/%s" % (self.namespace,str(self.bundle["_id"]))
        self.bundle["@graph"]["pid"] = str(self.bundle["_id"])
        
    def serialize_bundle(self,payload):
        if self.request.args.get("annotations",False):
            a=annotations.find({"@graph.dc:relation":payload["_id"]})
            payload["@graph"]["annotations"]=[]
            for ann in a:
                new_ann=Annotation(bundle=ann["@graph"],client=self.request.args.get("client",None))
                payload["@graph"]["annotations"].append(new_ann.part.data)
        payload["@graph"]["resource"]=uri_pattern(payload["@graph"]["pid"],apihost+"/"+self.endpoint)    
        payload["@graph"]["type"]=resolve_type(payload["@graph"]["dc:type"])
        if payload["@graph"]["type"]=="humvideo":
            payload["@graph"]["url"]=uri_pattern(payload["@graph"]["ma:locator"],host+"/"+self.endpoint)
        elif payload["@graph"]["type"]=="yt":
            payload["@graph"]["url"]=uri_pattern(payload["@graph"]["ma:locator"],"http://youtu.be")
        return mongo_jsonify(payload["@graph"])

    def set_attrs(self):
        if "type" in self.request.json:
            self.bundle["@graph"]["dc:type"]="hummedia:type/"+self.request.json["type"]
        for (k,v) in self.request.json.items():
            if k in self.model.structure['@graph'] and k not in ["dc:identifier","pid","dc:type"]:
                if k in ["ma:features","ma:contributor"]:
                    for i in v:
                        self.bundle["@graph"][k].append({"@id":i["@id"],"name":unicode(i["name"])})
                elif k in ["ma:isCopyrightedBy","ma:hasGenre"]:
                    self.bundle["@graph"][k]={"@id":v["@id"],"name":unicode(["name"]) }
                    self.bundle["@graph"][k]=ObjectId(v)
                elif self.model.structure['@graph'][k]==type(u""):
                    self.bundle["@graph"][k]=unicode(v)
                if k=="ma:title":
                    self.bundle["ititle"]=unicode(v).lower()
                    self.bundle["@graph"]["ma:title"]=unicode(v)
                elif self.model.structure['@graph'][k]==type(2):
                    self.bundle["@graph"][k]=int(v)
                elif self.model.structure['@graph'][k]==type(2.0):
                    self.bundle["@graph"][k]=float(v)
                elif type(self.model.structure['@graph'][k])==type([]):
                    self.bundle["@graph"][k]=[]
                    for i in v:
                        if k=="ma:isMemberOf":
                            membership={}
                            for (g,h) in i.items():
                                membership[g]=ObjectId(h) if g=="@id" else h
                            self.bundle["@graph"]["ma:isMemberOf"].append(membership)
                        else:
                            self.bundle["@graph"][k].append(i)    
                else: 
                    self.bundle["@graph"][k]=v

class AssetGroup(Resource):
    collection=ags
    model=ags.AssetGroup
    namespace="hummedia:id/collection"
    endpoint="collection"
    
    def set_query(self):
        q={"@graph.dc:creator":self.request.args.get("dc:creator")} if "dc:creator" is self.request.args else {}
        return q
        
    def get_list(self):
        alist=[]
        for d in self.bundle:
            d["@graph"]["resource"]=uri_pattern(d["@graph"]["pid"],apihost+"/"+self.endpoint)
            d["@graph"]["type"]=resolve_type(d["@graph"]["dc:type"])
            alist.append(d["@graph"])
        return mongo_jsonify(alist)
        
    def set_resource(self):
        self.bundle["@graph"]["resource"]=uri_pattern(self.bundle["@graph"]["pid"],apihost+"/"+self.endpoint)

    def preprocess_bundle(self):
        self.bundle["@graph"]["dc:identifier"] = "%s/%s" % (self.namespace,str(self.bundle["_id"]))
        self.bundle["@graph"]["pid"] = str(self.bundle["_id"])
        
    def serialize_bundle(self,payload):
        v=assets.find({"@graph.ma:isMemberOf.@id":payload["_id"]})
        payload["@graph"]["videos"]=[]
        for vid in v:
            if self.request.args.get("full",False):
                resource=uri_pattern(vid["@graph"]["pid"],apihost+"/video")    
                vid["@graph"]["type"]=resolve_type(vid["@graph"]["dc:type"])
                vid["@graph"]["resource"]=resource
                payload["@graph"]['videos'].append(vid["@graph"])
            else:
                payload["@graph"]["videos"].append(assets.Video.make_part(vid["@graph"],apihost,self.request.args.get("part","details")))
        payload["@graph"]["type"]=resolve_type(payload["@graph"]["dc:type"])
        return mongo_jsonify(payload["@graph"])
    
    def set_attrs(self):
        if "type" in self.request.json:
            self.bundle["@graph"]["dc:type"]="hummedia:type/"+self.request.json["type"]
        for (k,v) in self.request.json.items():
            if k in self.model.structure['@graph'] and k not in ["dc:identifier","pid","dc:type"]:
                self.bundle["@graph"][k]=unicode(v) if k in ["dc:title","dc:description"] else v

class Annotation(Resource):
    collection=annotations
    model=annotations.AnnotationList
    namespace="hummedia:id/annotation"
    endpoint="annotation"
    
    def set_query(self):
        if self.request.args.get("dc:relation",False):
            q={"@graph.dc:relation":ObjectId(self.request.args.get("dc:relation"))}
        elif self.request.args.get("dc:creator",False):
            q={"@graph.dc:creator":self.request.args.get("dc:creator")}
        else:
            q={}
        return q
        
    def get_list(self):
        alist=[]
        for d in self.bundle:
            d["@graph"]["resource"]=uri_pattern(d["@graph"]["pid"],apihost+"/"+self.endpoint)
            alist.append(d["@graph"])
        return mongo_jsonify(alist)
        
    def set_resource(self):
        self.bundle["@graph"]["resource"]=uri_pattern(self.bundle["@graph"]["pid"],apihost+"/"+self.endpoint)
        
    def client_process(self):
        c=clients.lookup[self.request.args.get("client")]()
        m=assets.find_one(self.bundle["@graph"]["dc:relation"])
        m["@graph"]["resource"]=uri_pattern(m["@graph"]["pid"],apihost+"/video")
        m["@graph"]["type"]=resolve_type(m["@graph"]["dc:type"])
        if m["@graph"]["type"]=="humvideo":
            m["@graph"]["url"]=uri_pattern(m["@graph"]["ma:locator"],host+"/video")
        elif m["@graph"]["type"]=="yt":
            m["@graph"]["url"]=uri_pattern(m["@graph"]["ma:locator"],"http://youtu.be")
        return c.serialize(self.bundle["@graph"],m["@graph"])

    def preprocess_bundle(self):
        self.bundle["@graph"]["dc:identifier"] = "%s/%s" % (self.namespace,str(self.bundle["_id"]))
        self.bundle["@graph"]["pid"] = str(self.bundle["_id"])
        
    def serialize_bundle(self,payload):
        return mongo_jsonify(payload["@graph"])
    
    def set_attrs(self):
        if "client" in self.request.args:
            c=clients.lookup[self.request.args.get("client")]()
            packet=c.deserialize(self.request)
        else:
            packet=self.request.json
        for (k,v) in packet.items():
            if k=="dc:relation":
                self.bundle["@graph"][k]=ObjectId(v)
            elif k=="dc:title":
                self.bundle["@graph"]["dc:title"]=unicode(v)
            elif k=="vcp:playSettings":
                for (i,j) in v.items():
                    if i=="vcp:frameRate":
                        self.bundle["@graph"]["vcp:playSettings"][i]=float(j)
                    elif i=="vcp:videoCrop":
                        self.bundle["@graph"]["vcp:playSettings"][i]=j
                    else:
                        self.bundle["@graph"]["vcp:playSettings"][i]=int(j)
            elif k=="vcp:commands":
                self.bundle["@graph"]["vcp:commands"]=[]
                for i in v:
                    self.bundle["@graph"]["vcp:commands"].append(i)
            else:
                self.bundle["@graph"][k]=v

