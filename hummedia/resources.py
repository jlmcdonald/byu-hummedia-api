from datetime import datetime
from os.path import splitext
from models import connection
from flask import request, Response, jsonify
from helpers import Resource, mongo_jsonify, parse_npt, plain_resp, resolve_type, uri_pattern, bundle_400, bundle_404, action_401, action_501, is_enrolled, can_read, getYtThumbs, send_file_partial
from mongokit import cursor
from bson import ObjectId
from urlparse import urlparse, parse_qs
import clients, config, json, re
from hummedia import app
from os import system, chmod, chdir, getcwd, listdir, rename, path
from gearman import GearmanClient

db=connection[config.MONGODB_DB]
ags=db.assetgroups
assets=db.assets
annotations=db.annotations
users=db.users

class NotImplemented(Resource):

    def get(self,id):
	return action_501()

class UserProfile(Resource):
    collection=users
    model=users.User
    namespace="hummedia:id/user"
    endpoint="account"

    def get(self,id):
        q=self.set_query()
        if id:
            try:
                q['_id']=ObjectId(str(id))
            except Exception as e:
                return bundle_400("The ID you submitted is malformed.")
            self.bundle=self.get_bundle(q)
            if self.bundle:
                self.bundle=self.auth_filter(self.bundle)
                if not self.bundle:
                    return action_401()
                self.set_resource()
                return self.serialize_bundle(self.bundle)
            else:
                return bundle_404()
        else:
            self.bundle=self.collection.find(q)
            return self.get_list()

    def auth_filter(self,bundle=None):
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            bundle=self.acl_filter(atts['username'],bundle)
            self.bundle=bundle
        return self.bundle
    
    def set_disallowed_atts(self):
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.disallowed_atts=['role','superuser']
        
    def acl_filter(self,username="unauth",bundle=None):
        if not bundle:
            bundle=self.bundle
        if type(bundle)==cursor.Cursor:
            bundle=list(bundle)
            for obj in bundle[:]:
                if obj["username"] != username:
                    bundle.remove(obj)
        elif bundle["username"] != username:
                bundle={}
        return bundle

    def acl_write_check(self,bundle=None):
        from auth import get_profile
        atts=get_profile()
        return atts['superuser']

    def post(self,pid=None):
        if self.acl_write_check():
            self.bundle=self.model()
            if not pid:
                if "username" in self.request.json:
                    self.bundle["_id"]=str(self.request.json.username)
                else:
                    return bundle_400()
            else:
                self.bundle["_id"]=str(ObjectId(pid))
            self.preprocess_bundle()
            self.set_attrs()
            return self.save_bundle()
        else:
            return action_401()
    
    def set_query(self):
        q={}
        if self.request:
            if self.request.args.get("oauth",False):
                q["oauth"][self.request.args.get("provider")]=self.request.args.get("provider_account")
            elif self.request.args.get("email",False):
                q["email"]=self.request.args.get("email")
        else:
            q["oauth"][self.manual_request["provider"]]=self.manual_request["provider_id"]
        return q
      
class MediaAsset(Resource):
    collection=assets
    model=assets.Video
    namespace="hummedia:id/video"
    endpoint="video"
    override_only_triggers=['enrollment']
    
    def set_disallowed_atts(self):
        self.disallowed_atts=["dc:identifier","pid","dc:type"]
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.disallowed_atts.append("dc:creator")
    
    def set_query(self):
        q={}
        v=self.request.args.get("q",False)
        if v:
            cire={'$regex':'.*'+v+'.*', '$options': 'i'}
            q["$or"]=[{"@graph.ma:title":cire},
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
                    q["@graph.ma:title"]=cire
                elif k in ["ma:description","ma:hasKeyword"]:
                    q["@graph."+k]=cire
                elif k not in ["yearfrom","yearto","ma:date","part","inhibitor"]:
                    q["@graph."+k]=v
        return q
        
    def get_list(self):
        alist=[]
        self.bundle=self.auth_filter()
        thumbRetriever=[]
        for d in self.bundle:
            alist.append(self.model.make_part(d["@graph"],config.APIHOST,self.request.args.get("part","details")))
            thumbRetriever.extend(alist[-1].get("fromYt"))
            alist[-1].pop("fromYt",None)
        ytThumbs=getYtThumbs(thumbRetriever)
        for vid in alist:
            for image in vid["ma:image"]:
                if image.get("ytId"):
                    image["thumb"] = ytThumbs[image["ytId"]]["thumb"]
                    image["poster"] = ytThumbs[image["ytId"]]["poster"]
                    image.pop("ytId",None)
        return mongo_jsonify(alist)
        
    def set_resource(self):
        self.bundle["@graph"]["resource"]=uri_pattern(self.bundle["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)

    def preprocess_bundle(self):
        self.bundle["@graph"]["dc:identifier"] = "%s/%s" % (self.namespace,str(self.bundle["_id"]))
        self.bundle["@graph"]["pid"] = str(self.bundle["_id"])
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.bundle["@graph"]["dc:creator"]=atts['username']
    
    # returns a filepath for a given video id and filetype
    # valid filetypes: mp4, webm
    def get_filepath(self, id, type="mp4"):
        whitelist = ["mp4", "webm"]
        
        if type not in whitelist: return None
    
        try:
            obj = self.model.find_one({"_id":str(id)})
            files = obj["@graph"]["ma:locator"]
            
            from auth import get_profile
            atts=get_profile()
            
            # TODO: Return something more obvious
            if not self.read_override(obj, atts["username"], atts["role"]): return None
            
            for file in files:
                if file['ma:hasFormat'] == 'video/' + type:
                    return config.MEDIA_DIRECTORY + file['@id'] + '.' + type

        except Exception as e:
            return None
        
        return None

    def read_override(self,obj,username,role):
        for parent in obj['@graph']['ma:isMemberOf']:
            id=parent['@id'] if '@id' in parent else None
            c=ags.find_one({"_id":str(id)})
            if c:
                if is_enrolled(c) or can_read(c):
                    return True
        return False
        
    def serialize_bundle(self,payload):
        payload["@graph"]["resource"]=uri_pattern(payload["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)    
        payload["@graph"]["type"]=resolve_type(payload["@graph"]["dc:type"])
        payload["@graph"]["url"]=[]
        payload["@graph"]["ma:image"]=[]
        if payload["@graph"]["type"]=="humvideo":
            prefix=config.APIHOST+"/"+self.endpoint
            needs_ext=True
        elif payload["@graph"]["type"]=="yt":
            prefix="http://youtu.be"
            needs_ext=False
        fromYt=[]
        for location in payload["@graph"]["ma:locator"]:
            if needs_ext:
                ext=location["ma:hasFormat"].split("/")[-1]
                loc=location["@id"] + "/file/" + ext
                poster=uri_pattern(location["@id"]+".jpg",config.HOST+"/posters")
                thumb=uri_pattern(location["@id"]+"_thumb.jpg",config.HOST+"/posters")
                payload["@graph"]["ma:image"].append({"poster":poster,"thumb":thumb})
            else:
                loc=location["@id"]
                fromYt.append(loc)
                payload["@graph"]["ma:image"].append({"ytId":loc})
            payload["@graph"]["url"].append(uri_pattern(loc,prefix))
        ytThumbs=getYtThumbs(fromYt)
        for image in payload["@graph"]["ma:image"]:
            if image.get("ytId"):
                image["thumb"] = ytThumbs[image["ytId"]]["thumb"]
                image["poster"] = ytThumbs[image["ytId"]]["poster"]
                image.pop("ytId",None)
        for annot in payload["@graph"]["ma:isMemberOf"]:
            coll=ags.find_one({"_id":annot["@id"]})
            annot["title"]=coll["@graph"]["dc:title"]
	try:
            for track in payload["@graph"]["ma:hasRelatedResource"]:
            	track["@id"]=uri_pattern(track["@id"],config.HOST+"/text")
	except KeyError:
	    pass
        return mongo_jsonify(payload["@graph"])

    def set_attrs(self):
        if "type" in self.request.json:
            self.bundle["@graph"]["dc:type"]="hummedia:type/"+self.request.json["type"]
        for (k,v) in self.request.json.items():
            if k in self.model.structure['@graph'] and k not in self.disallowed_atts:
                if k in ["ma:features","ma:contributor"]:
                    for i in v:
                        self.bundle["@graph"][k].append({"@id":i["@id"],"name":unicode(i[k])})
                elif k in ["ma:isCopyrightedBy","ma:hasGenre"]:
                    self.bundle["@graph"][k]={"@id":v["@id"],"name":unicode(v["name"]) if v["name"] is not None else v["name"] }
                elif self.model.structure['@graph'][k]==type(u""):
                    self.bundle["@graph"][k]=unicode(v)
                elif self.model.structure['@graph'][k]==type(2):
                    self.bundle["@graph"][k]=int(v) if v is not None else 0
                elif self.model.structure['@graph'][k]==type(2.0):
                    self.bundle["@graph"][k]=float(v) if v is not None else 0
                elif type(self.model.structure['@graph'][k])==type([]):
                    self.bundle["@graph"][k]=[]
                    for i in v:
                        if k=="ma:isMemberOf":
                            membership={}
                            for (g,h) in i.items():
                                membership[g]=str(h)
                            self.bundle["@graph"][k].append(membership)
                        elif k in ["ma:hasContributor","ma:features","ma:isCopyrightedBy","ma:hasGenre"]:
                            newdict={}
                            for (g,h) in i.items():
                                newdict[g]=unicode(h) if self.model.structure['@graph'][k][0][g]==type(u"") else str(h)
                            self.bundle["@graph"][k].append(newdict)
                        else:
                            self.bundle["@graph"][k].append(i)    
                elif k=="dc:date":
                    self.bundle["@graph"][k]=datetime.strptime(v, '%Y-%m-%d')
                else: 
                    self.bundle["@graph"][k]=v
            elif k=="url":
                if type(v)!=type([]):
                    v=[v]
                self.bundle["@graph"]["ma:locator"]=[]
                for i in v:
                    p=urlparse(i)
                    if p[1]=="youtube.com":
                        file=parse_qs(p[4])["v"]
                        ext="mp4"
                    elif p[1]=="youtu.be":
                        file=p[2].split("/")[-1]
                        ext="mp4"
                    else:
                        path=p[2].split("/")[-1]
                        file,ext=splitext(path)
                        ext=ext.replace(".","")
                    loc={"@id":file,"ma:hasFormat":"video/"+ext}
                    if ext=="mp4":
                        loc["ma:hasCompression"]={"@id":"http://www.freebase.com/view/en/h_264_mpeg_4_avc","name": "avc.42E01E"}
                    elif ext=="webm":
                        loc["ma:hasCompression"]={"@id":"http://www.freebase.com/m/0c02yk5","name":"vp8.0"}
                    self.bundle["@graph"]["ma:locator"].append(loc)

    def delete(self,id):
        from auth import get_profile
        atts=get_profile()
        if atts['superuser']:
            self.bundle=self.model.find_one({'_id': str(id)})
            return self.delete_obj()
        else:
            return action_401()

@app.route('/video/<id>/file', methods=['GET'])
@app.route('/video/<id>/file/<type>', methods=['GET'])
def File(id, type="mp4"):
        # videos cannot be watched outside of the allowed referrer, which must be the host followed by /video
        if not re.compile("^" + config.HOST + "/video/").match(str(request.referrer)):
            return bundle_404()

        video = MediaAsset(request)
        filepath = video.get_filepath(id, type)
        try:
            return send_file_partial(filepath)
        except Exception:
            return bundle_404()

@app.route('/batch/video/ingest',methods=['GET','POST'])
def videoCreationBatch():
    from auth import get_user, superuser
    if not superuser():
        return action_401()
    if request.method=="GET":
        chdir(config.INGEST_DIRECTORY)
        files=listdir(getcwd())
        try:
            files.remove(".DS_Store")
        except ValueError:
            pass
        return json.dumps(files)
    else:
        from PIL import Image
        from omcreator.videoMetadata import getVideoInfo
        packet=request.json
        for up in packet:
            filepath=unicode(config.INGEST_DIRECTORY + up['filepath'])
	    if path.isfile(config.MEDIA_DIRECTORY + up['id'] + ".mp4"):
		return bundle_400("That file already exists; try another unique ID.")
            if path.isfile(filepath.encode('utf-8')):
                md=getVideoInfo(filepath.encode('utf-8'))
                poster = config.POSTERS_DIRECTORY + "%s.jpg" % (up["id"])
                thumb = config.POSTERS_DIRECTORY + "%s_thumb.jpg" % (up["id"])
                imgcmd = "avconv -i '%s' -q:v 1 -r 1 -t 00:00:01 -ss 00:00:30 -f image2 '%s'" % (filepath,poster)
                system(imgcmd.encode('utf-8'))
                chmod(poster,0775)
                im=Image.open(poster)
                im.thumbnail((160,90))
                im.save(thumb)
                chmod(thumb,0775)
                rename(filepath.encode('utf-8'), config.MEDIA_DIRECTORY + up["id"] + ".mp4")

                client = GearmanClient(config.GEARMAN_SERVERS)
                client.submit_job("generate_webm", str(up["id"]))
                assets.update({"_id":up["pid"]},{"$set":{"@graph.ma:frameRate":float(md["framerate"]),"@graph.ma:averageBitRate":int(md["bitrate"]),"@graph.ma:frameWidth":int(md["width"]),"@graph.ma:frameHeight":int(md["height"]),"@graph.ma:duration":int(md["duration"])/60}})
	return True

class AssetGroup(Resource):
    collection=ags
    model=ags.AssetGroup
    namespace="hummedia:id/collection"
    endpoint="collection"
    override_only_triggers=['enrollment']
    
    def set_query(self):
        q={"@graph.dc:creator":self.request.args.get("dc:creator")} if "dc:creator" in self.request.args else {}
        return q
        
    def get_list(self):
        alist=[]
        self.bundle=self.auth_filter()
        if self.bundle:
            for d in self.bundle:
                d["@graph"]["resource"]=uri_pattern(d["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)
                d["@graph"]["type"]=resolve_type(d["@graph"]["dc:type"])
                alist.append(d["@graph"])
        return mongo_jsonify(alist)
        
    def set_resource(self):
        self.bundle["@graph"]["resource"]=uri_pattern(self.bundle["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)
        
    def read_override(self,obj,username,role):
        if resolve_type(obj["@graph"]["dc:type"]) in ["course_collection","themed_collection"]:
            return role=="student" and is_enrolled(obj)
        else:
            return False
            
    def preprocess_bundle(self):
        self.bundle["@graph"]["dc:identifier"] = "%s/%s" % (self.namespace,str(self.bundle["_id"]))
        self.bundle["@graph"]["pid"] = str(self.bundle["_id"])
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.bundle["@graph"]["dc:creator"]=atts['username']
        
    def serialize_bundle(self,payload):
        if payload:
            v=assets.find({"@graph.ma:isMemberOf.@id":payload["_id"]})
            payload["@graph"]["videos"]=[]
            if not is_enrolled(payload):
                v=self.auth_filter(v)
            thumbRetriever=[]
            for vid in v:
                if self.request.args.get("full",False):
                    resource=uri_pattern(vid["@graph"]["pid"],config.APIHOST+"/video")    
                    vid["@graph"]["type"]=resolve_type(vid["@graph"]["dc:type"])
                    vid["@graph"]["resource"]=resource
                    vid["@graph"]["ma:image"]=[]
                    if vid["@graph"]["type"]=="humvideo":
                        needs_ext=True
                    elif vid["@graph"]["type"]=="yt":
                        needs_ext=False
                    for location in vid["@graph"]["ma:locator"]:
                        if needs_ext:
                            poster=uri_pattern(location["@id"]+".jpg",config.HOST+"/posters")
                            thumb=uri_pattern(location["@id"]+"_thumb.jpg",config.HOST+"/posters")
                            vid["@graph"]["ma:image"].append({"poster":poster,"thumb":thumb})
                        else:
                            loc=location["@id"]
                            vid["@graph"]["ma:image"].append({"ytId":loc})
                            thumbRetriever.append(loc)
                    payload["@graph"]['videos'].append(vid["@graph"])
                else:
                    payload["@graph"]["videos"].append(assets.Video.make_part(vid["@graph"],config.APIHOST,self.request.args.get("part","details")))
                    thumbRetriever.extend(payload["@graph"]["videos"][-1].get("fromYt"))
                    payload["@graph"]["videos"][-1].pop("fromYt",None)
            payload["@graph"]["type"]=resolve_type(payload["@graph"]["dc:type"])
            ytThumbs=getYtThumbs(thumbRetriever)
            for vid in payload["@graph"]["videos"]:
                for image in vid["ma:image"]:
                    if image.get("ytId"):
                        image["thumb"] = ytThumbs[image["ytId"]]["thumb"]
                        image["poster"] = ytThumbs[image["ytId"]]["poster"]
                        image.pop("ytId",None)
            return mongo_jsonify(payload["@graph"])
        else:
            return mongo_jsonify({})
            
    def set_disallowed_atts(self):
        self.disallowed_atts=["dc:identifier","pid","dc:type"]
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.disallowed_atts.append("dc:creator")
    
    def set_attrs(self):
        if "type" in self.request.json:
            self.bundle["@graph"]["dc:type"]="hummedia:type/"+self.request.json["type"]
        for (k,v) in self.request.json.items():
            if k in self.model.structure['@graph'] and k not in self.disallowed_atts:
                if self.model.structure['@graph'][k]==type(u""):
                    self.bundle["@graph"][k]=unicode(v)
                elif type(self.model.structure['@graph'][k])==type([]):
                    self.bundle["@graph"][k]=[]
                    for i in v:
                        self.bundle["@graph"][k].append(i)  
                else:
                    self.bundle["@graph"][k]=v

    def delete_associated(self,id):
        d=assets.update({"@graph.ma:isMemberOf.@id":str(id)},{'$pull': {"@graph.ma:isMemberOf":{"@id":str(id)}}},multi=True)

@app.route('/batch/video/membership',methods=['POST'])
def videoMembershipBatch():
    status={}
    packet=request.json
    for up in packet:
        status[up['collection']['id']]=assets.update({'@graph.pid':{'$in':up['videos']}}, {'$addToSet':{"@graph.ma:isMemberOf":{'@id':up['collection']['id'],'title':up['collection']['id']}}},multi=True)
    return jsonify(status)

class Annotation(Resource):
    collection=annotations
    model=annotations.AnnotationList
    namespace="hummedia:id/annotation"
    endpoint="annotation"

    def read_override(self,obj,username,role):
        return True
    
    def set_query(self):
        if self.request.args.get("dc:relation",False):
            if self.request.args.get("collection"):
                q={"_id":False}
                v=assets.find_one({"_id":str(self.request.args.get("dc:relation"))})
                if v:
                    annots=[]
                    for coll in v["@graph"]["ma:isMemberOf"]:
                        if coll["@id"]==str(self.request.args.get("collection")) and "restrictor" in coll:
                            annots.append(str(coll['restrictor']))
                    for annot in v["@graph"].get("ma:hasPolicy"):
                            annots.append((str(annot)))
                    q={"_id":{'$in':annots}}
            else:
                q={"@graph.dc:relation":str(self.request.args.get("dc:relation"))}
        elif self.request.args.get("dc:creator",False):
            q={"@graph.dc:creator":self.request.args.get("dc:creator")}
        else:
            q={}
        return q

    def get_list(self):
        alist=[]
        self.bundle=self.auth_filter()
        for d in self.bundle:
            if self.request.args.get("client",None):
                alist.append(self.client_process(d,True))
            else:
                d["@graph"]["resource"]=uri_pattern(d["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)
                alist.append(d["@graph"])
        return mongo_jsonify(alist)
        
    def set_resource(self):
        self.bundle["@graph"]["resource"]=uri_pattern(self.bundle["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)
        
    def client_process(self,bundle=None,list=False):
        if not bundle:
            bundle=self.bundle
        c=clients.lookup[self.request.args.get("client")]()
        m=assets.find_one(bundle["@graph"]["dc:relation"])
        m["@graph"]["resource"]=uri_pattern(m["@graph"]["pid"],config.APIHOST+"/video")
        m["@graph"]["type"]=resolve_type(m["@graph"]["dc:type"])
        m["@graph"]["url"]=[]
        for url in m["@graph"]["ma:locator"]:
            if m["@graph"]["type"]=="humvideo":
                host=config.HOST+"/video"
                ext="."+url["ma:hasFormat"].replace("video/","")
            elif m["@graph"]["type"]=="yt":
                host="http://youtu.be"
                ext=""
            m["@graph"]["url"].append(uri_pattern(url["@id"]+ext,host))
        resp_context=True if not list else False
        try:
            required = True if bundle["@graph"]["pid"] in m["@graph"].get("ma:hasPolicy") else False
        except TypeError:
            return bundle_400("That annotation list isn't currently associated with any media.")
        return c.serialize(bundle["@graph"],m["@graph"],resp_context,required)

    def preprocess_bundle(self):
        self.bundle["@graph"]["dc:identifier"] = "%s/%s" % (self.namespace,str(self.bundle["_id"]))
        self.bundle["@graph"]["pid"] = str(self.bundle["_id"])
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.bundle["@graph"]["dc:creator"]=atts['username']
        
    def serialize_bundle(self,payload):
        return mongo_jsonify(payload["@graph"])
        
    def set_disallowed_atts(self):
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.disallowed_atts.append("dc:creator")
    
    def set_attrs(self):
        if "client" in self.request.args:
            c=clients.lookup[self.request.args.get("client")]()
            packet=c.deserialize(self.request)
        else:
            packet=self.request.json
        for (k,v) in packet.items():
            if k=="dc:title":
                self.bundle["@graph"]["dc:title"]=unicode(v)
            elif k=="vcp:playSettings" and v:
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
        if self.request.method == "POST":
            m=connection.Video.find_one(self.bundle["@graph"]["dc:relation"])
            if "collection" in self.request.args:
                for c in m["@graph"]["ma:isMemberOf"]:
                    if c["@id"]==self.request.args["collection"]:
                        c["restrictor"]=self.bundle["_id"]
                        m.save()
                        break
            else:
                if self.bundle["_id"] not in m["@graph"]["ma:hasPolicy"]:
                    m["@graph"]["ma:hasPolicy"].append(self.bundle["_id"]) 
                    m.save()
