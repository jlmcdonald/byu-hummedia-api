from datetime import datetime
from os.path import splitext
from models import connection
from flask import request, Response, jsonify
from helpers import Resource, mongo_jsonify, parse_npt, plain_resp, resolve_type, uri_pattern, bundle_400, bundle_404, action_401, is_enrolled, getYtThumbs
from mongokit import cursor
from bson import ObjectId
from urlparse import urlparse, parse_qs
import clients, config, json, re, hashlib, time
from hummedia import app
from os import system, chmod, chdir, getcwd, listdir, path, remove
import vtt

db=connection[config.MONGODB_DB]
ags=db.assetgroups
assets=db.assets
annotations=db.annotations
users=db.users

class UserProfile(Resource):
    collection=users
    model=users.User
    namespace="hummedia:id/user"
    endpoint="account"

    def get(self,id,limit=0):
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
            self.bundle=self.collection.find(q).limit(limit)
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
            setattrs=self.set_attrs()
            if setattrs.get("resp")==200:
                return self.save_bundle()
            else:
                return bundle_400(setattrs.get("msg"))
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
    max_search_results = 20

    def patch(self, id):
        from auth import get_profile
        atts=get_profile()

        if self.request.json is None or 'replacement_file' not in self.request.json:
            return super(MediaAsset, self).patch(id)

        if not atts['superuser']:
            return action_401()

        found = assets.find_one({'_id': id})

        if not found:
            return bundle_404()

        file_id = None
        to_delete = []

        # find existing filenames
        for f in found['@graph']['ma:locator']:
            if file_id is not None and f['@id'] != file_id:
                raise Exception("Cannot replace file; multiple files with different IDs")

            file_id = f['@id']
            extension = f['ma:hasFormat'].split('/')[-1]
            fpath = config.MEDIA_DIRECTORY + f['@id'] + '.' + extension
            to_delete.append(fpath)

        from os import remove
        for f in to_delete:
            remove(f)

        assets.update({'_id': id}, {'$set': {'@graph.ma:locator': []}})

        result = self.set_new_file(id, file_id, self.request.json['replacement_file'])
        if not result[0]:
            return bundle_400(result[1])

        return self.serialize_bundle(assets.find_one({'_id': id}))

    @staticmethod
    def set_new_file(video_id, new_id, filepath):
        ''' Returns a tuple with the first value T/F, and the second, if False,
        the relevant message. '''

        from helpers import getVideoInfo
        from PIL import Image
        from shutil import move

        up = {'id': new_id, 'filepath': filepath, 'pid': video_id}

        i = up['id']
        dupe = assets.find_one({'@graph.ma:locator': {'$elemMatch': {'@id': i}}})
        mp4 = (unicode(config.MEDIA_DIRECTORY) + i + '.mp4').encode('utf-8')
        webm = (unicode(config.MEDIA_DIRECTORY) + i + '.webm').encode('utf-8')

        if path.isfile(webm) or path.isfile(mp4) or dupe is not None:
            return (False, "That file (%s) already exists; try another unique ID." %i)

        filepath=unicode(config.INGEST_DIRECTORY + up['filepath'])
        new_file=unicode(config.MEDIA_DIRECTORY + up['id'] + ".mp4")

        md=getVideoInfo(filepath.encode('utf-8'))
        poster = config.POSTERS_DIRECTORY + "%s.jpg" % (up["id"])
        thumb = config.POSTERS_DIRECTORY + "%s_thumb.jpg" % (up["id"])
        move(filepath.encode('utf-8'), new_file.encode('utf-8'))
        assets.update({"_id":up["pid"]},{"$set":{
            "@graph.ma:frameRate":float(md["framerate"]),
            "@graph.ma:averageBitRate":int(float(md["bitrate"])),
            "@graph.ma:frameWidth":int(md["width"]),
            "@graph.ma:frameHeight":int(md["height"]),
            "@graph.ma:duration":int( round(float(md["duration"])) )/60,
            "@graph.ma:locator": [
                {
                    "@id": up["id"],
                    "ma:hasFormat": "video/mp4",
                    "ma:hasCompression": {"@id":"http://www.freebase.com/view/en/h_264_mpeg_4_avc","name": "avc.42E01E"}
                },
                {
                    "@id": up["id"],
                    "ma:hasFormat": "video/webm",
                    "ma:hasCompression": {"@id":"http://www.freebase.com/m/0c02yk5","name":"vp8.0"}
                }
            ]
        }})
        imgcmd = "avconv -i '%s' -q:v 1 -r 1 -t 00:00:01 -ss 00:00:30 -f image2 '%s'" % (new_file,poster)
        system(imgcmd.encode('utf-8'))
        chmod(poster,0775)
        im=Image.open(poster)
        im.thumbnail((160,90))
        im.save(thumb)
        chmod(thumb,0775)

        if not app.config.get('TESTING'):
            from gearman import GearmanClient
            client = GearmanClient(config.GEARMAN_SERVERS)
            client.submit_job("generate_webm", str(up["id"]))
        else:
            from ingest import generate_webm
            result = generate_webm(file_id=up['id'])
            if result == "ERROR":
                raise Exception("Could not convert media file.")

        return (True,)
    
    def set_disallowed_atts(self):
        self.disallowed_atts=["dc:identifier","pid","dc:type","url","ma:duration"]
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.disallowed_atts.append("dc:creator")

    def get(self,id,limit=0):
        if self.request.args.get("q") is not None:
            if limit is 0:
                return super(MediaAsset, self).get(id, self.max_search_results)

        if "concise" in self.request.args:
            import json
            response = super(MediaAsset, self).get(id, limit, ('@graph.pid', '@graph.ma:title','@graph.ma:isMemberOf'))
            data = json.loads(response.data)

            for i in data:
              del i['ma:isMemberOf'] # we only want to return the pid and title in concise mode

            response.data = json.dumps(data)
            return response

        return super(MediaAsset, self).get(id, limit)
    
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
                elif k not in ["yearfrom","yearto","ma:date","part","inhibitor","concise"]:
                    q["@graph."+k]=v
        return q
        
    def get_list(self):
        if "concise" in self.request.args:
          self.bundle=self.auth_filter()
          return mongo_jsonify(map(lambda x: x['@graph'], self.bundle))

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
		    try:
			    image["thumb"] = ytThumbs[image["ytId"]]["thumb"]
			    image["poster"] = ytThumbs[image["ytId"]]["poster"]
		    except Exception:
			    image["thumb"] = None
			    image["poster"] = None
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
    
    def read_override(self,obj,username,role):
        from auth import get_profile
        atts=get_profile()
        if atts['superuser']:
            return True
        for c in obj["@graph"]["ma:isMemberOf"]:
            coll=ags.find_one({"_id":c["@id"]})
            try:
                if coll["@graph"].get("dc:creator")==atts['username'] or atts['username'] in coll['@graph']["dc:rights"]["read"] or coll['@graph']['dc:coverage'] == 'public':
                    return True
            except TypeError:
                   pass
            if is_enrolled(coll):
                return True
        return False

    def acl_write_check(self,bundle=None):
        from auth import get_profile
        atts=get_profile()
        if atts['superuser'] or (atts['role']=='faculty' and not bundle):
            return True
        if bundle:
            try:
                if bundle["@graph"].get("dc:creator")==atts['username'] or atts['username'] in bundle['@graph']["dc:rights"]["write"]:
                    return True
            except TypeError:
                   pass
            for coll in bundle["@graph"]["ma:isMemberOf"]:
                coll=ags.find_one({"_id":coll["@id"]})
                if coll["@graph"].get("dc:creator")==atts['username'] or atts['username'] in coll['@graph']["dc:rights"]["write"]:
                    return True
        return False
        
    def serialize_bundle(self,payload):
        payload["@graph"]["resource"]=uri_pattern(payload["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)    
        payload["@graph"]["type"]=resolve_type(payload["@graph"]["dc:type"])
        payload["@graph"]["url"]=[]
        payload["@graph"]["ma:image"]=[]
        if payload["@graph"]["type"]=="humvideo":
            prefix=config.HOST + '/'
            needs_ext=True
        elif payload['@graph']['type']=='humaudio':
            prefix=config.HOST + '/'
            needs_ext=True
        elif payload["@graph"]["type"]=="yt":
            prefix="http://youtu.be"
            needs_ext=False
        fromYt=[]
        for location in payload["@graph"]["ma:locator"]:
            if needs_ext:
                ext=location["ma:hasFormat"].split("/")[-1]
                fileName= '/' + location["@id"] + "." + ext
                hexTime="{0:x}".format(int(time.time()))
                token = hashlib.md5(''.join([
                    config.AUTH_TOKEN_SECRET,
                    fileName,
                    hexTime,
                    request.remote_addr if config.AUTH_TOKEN_IP else '' 
                ])).hexdigest()
                loc = ''.join([
                    config.AUTH_TOKEN_PREFIX,
                    token, "/", hexTime, fileName
                ])
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
                details=annotations.find_one({"_id":annot["restrictor"]})
                annot["transcript"]=bool(details['@graph']['vcp:playSettings']['vcp:showTranscript'])
            except (KeyError, TypeError):
                annot["transcript"] = False

	try:
            for track in payload["@graph"]["ma:hasRelatedResource"]:
            	track["@id"]=uri_pattern(track["@id"],config.HOST+"/text")
	except KeyError:
	    pass
        return mongo_jsonify(payload["@graph"])

    def set_attrs(self):
        if "subtitle" in request.files:
            try:
                subs = self.make_vtt(request.files['subtitle'],
                       name = request.form.get('name'),
                       lang = request.form.get('lang'))
            except vtt.SubtitleException as e:
                return ({"resp":400,"msg":"Invalid subtitle uploaded: {0}".format(e)})

            self.bundle["@graph"]["ma:hasRelatedResource"].append(subs)

        if self.request.json is None:
	    return ({"resp":200})

        if "type" in self.request.json:
            self.bundle["@graph"]["dc:type"]="hummedia:type/"+self.request.json["type"]
        for (k,v) in self.request.json.items():
            if k in self.model.structure['@graph'] and k not in self.disallowed_atts:
                if k in ["ma:features","ma:contributor"]:
                    for i in v:
                        self.bundle["@graph"][k].append({"@id":i["@id"],"name":unicode(i[k])})
                elif k in ["ma:isCopyrightedBy","ma:hasGenre"]:
                    self.bundle["@graph"][k]={"@id":v["@id"],"name":unicode(v["name"]) if v["name"] is not None else v["name"] }
		elif k=="ma:frameRate":
			if type(v)==type(2) or type(v)==type(2.0):
		        	self.bundle["@graph"][k]=v
			else:
				try:
                        		self.bundle["@graph"][k]=float(v)
                    		except ValueError:
                        		self.bundle["@graph"][k]=0
                elif self.model.structure['@graph'][k]==type(u""):
                    self.bundle["@graph"][k]=unicode(v)
                elif self.model.structure['@graph'][k]==type(2.0):
                    try:
                        self.bundle["@graph"][k]=float(v)
                    except ValueError:
                        self.bundle["@graph"][k]=0
                elif self.model.structure['@graph'][k]==type(2):
                    try:
                        self.bundle["@graph"][k]=int(v)
                    except ValueError:
                        self.bundle["@graph"][k]=0
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
			elif k=="ma:hasRelatedResource":
                            newdict={}
                            for (g,h) in i.items():
				if g=="@id" and "/" in h:
					h=h.rsplit("/",1)[1]
				newdict[g]=str(h)
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
                locator_found = False
                vid = assets.find_one({'_id': str(self.request.json.get('pid',"INGEST"))})
                if vid:
                    	locator_found = True
                    	self.bundle['@graph']['ma:locator'] = vid['@graph']['ma:locator']
                for i in v:
                    p=urlparse(i)
                    if p[1]=="youtube.com":
                        file=parse_qs(p[4])["v"]
                        ext="mp4"
                        commit = True
                    elif p[1]=="youtu.be":
                        file=p[2].split("/")[-1]
                        ext="mp4"
                        commit = True
                    else:
                        path=p[2].split("/")[-1]
                        file,ext=splitext(path)
                        ext=ext.replace(".","")
                        commit = False
                    if commit or not locator_found:
                        loc={"@id":file,"ma:hasFormat":"video/"+ext}
                        if ext=="mp4":
                            loc["ma:hasCompression"]={"@id":"http://www.freebase.com/view/en/h_264_mpeg_4_avc","name": "avc.42E01E"}
                        elif ext=="webm":
                            loc["ma:hasCompression"]={"@id":"http://www.freebase.com/m/0c02yk5","name":"vp8.0"}
			if loc not in self.bundle["@graph"]["ma:locator"]:
	                        self.bundle["@graph"]["ma:locator"].append(loc)
    	return ({"resp":200})

    def make_vtt(self, subs, name='Default', lang='en'):
        '''
        Given the subs file, copies to the subtitle directory as a VTT file.
        Returns a dictionary with information about the VTT
        '''

        import os
        import uuid
        from werkzeug.utils import secure_filename

        if not name: name = 'Default'
        if not lang: lang = 'en'

        ext = subs.filename.split('.')[-1]
        filename = secure_filename(subs.filename.split('.', 1)[0]) \
                   + str(uuid.uuid4()) + '.vtt'

        output = os.path.join(config.SUBTITLE_DIRECTORY, filename) 
       
        if ext == 'srt':
            vtt.from_srt(subs, output)
        elif ext == 'vtt':
            if not vtt.is_valid(subs):
                raise vtt.SubtitleException("Invalid VTT file")
            subs.save(output)
        else:
            raise vtt.SubtitleException("Extension must be .vtt or .srt. Given file: "\
                + filename + "\nExtension: " + ext)

        return {
            '@id': filename,
            'type': 'vtt',
            'name': name,
            'language': lang
        }

    def delete(self,id):
        from auth import get_profile
        atts=get_profile()
        if atts['superuser']:
            self.bundle=self.model.find_one({'_id': str(id)})
            result = self.delete_obj()
            if not result:
                return result
            else:
                for location in self.bundle['@graph']['ma:locator']:
                    basename = location['@id']
                    duplicates = self.model.find_one({"@graph.ma:locator": {"$elemMatch": {"@id": basename}}})
                    if duplicates is not None:
                        return result
                    extension = location['ma:hasFormat'].split('/')[-1]
                    filename = "{0}.{1}".format(basename, extension)
                    try:
                        remove(config.MEDIA_DIRECTORY + filename)
                    except IOError:
                        pass
                return result
        else:
            return action_401()
    
    def update_subtitle(self, filename, new_file):
        from helpers import endpoint_404

        query = {
          "@graph.ma:hasRelatedResource":{"$elemMatch": {"@id":filename}}
        }

        bundle = self.model.find_one(query)

        if bundle is None:
            return endpoint_404() 
        
        if not self.acl_write_check(bundle):
          return action_401()
        
        new_file.save(config.SUBTITLE_DIRECTORY + filename)
        
        return mongo_jsonify(bundle)
    
    def delete_subtitle(self, filename):
        from os import remove
        from helpers import endpoint_404

        query = {
          "@graph.ma:hasRelatedResource":{"$elemMatch": {"@id":filename}}
        }

        bundle = self.model.find_one(query)

        if bundle is None:
            return endpoint_404() 
        
        if not self.acl_write_check(bundle):
            return action_401()

        l = bundle.get("@graph").get("ma:hasRelatedResource")
        l[:] = [d for d in l if d.get('@id') != filename]
        bundle.save()
        
        remove(config.SUBTITLE_DIRECTORY + filename)

        return mongo_jsonify(bundle)

@app.route('/batch/audio/ingest',methods=['POST'])
def audioCreationBatch():
    import mutagen
    import uuid
    import os
    from werkzeug.utils import secure_filename
    from auth import is_superuser

    if not is_superuser():
      return action_401()

    files = request.files.getlist('audio[]')
    
    if not len(files):
      return bundle_400("Missing form field 'audio[]'")

    incompatible = filter(lambda x: not x.filename.endswith('mp3'), files)
    
    if len(incompatible):
      return bundle_400("Only MP3 files are supported.")

    results = []
    for f in files:
        ext = f.filename.split('.')[-1]
        filename = secure_filename(f.filename.split('.', 1)[0]) \
                   + str(uuid.uuid4()) + '.' + ext

        path = os.path.join(config.MEDIA_DIRECTORY, filename)
        f.save(path)

        id3 = mutagen.File(path, easy=True) # metadata
        _id = str(ObjectId())

        audio = assets.Video()
        audio['_id'] = _id
        audio['@graph']['dc:type'] = 'hummedia:type/humaudio'
        audio['@graph']['pid'] = _id
        audio['@graph']['ma:title'] = id3.get('title',[f.filename])[0]
        audio['@graph']['ma:hasContributor'] = [{'@id': '', 'name': x} for x in id3.get('artist',[])]

        try:
            audio['@graph']["ma:date"] = int(id3.get('date')[0])
        except:
            audio['@graph']['ma:date'] = 1970 # TODO: this requires a number, but I don't have one for it

        audio['@graph']["ma:locator"] = [
             {
                 "@id": '.'.join(filename.split('.')[0:-1]),
                 "ma:hasFormat": "audio/" + ext,
                 "ma:hasCompression": {}
             }
        ]
        audio.save()
        audio['@graph']['ma:locator'][0]['@id'] += '.mp3'
        results.append(audio['@graph'])

    return mongo_jsonify(results)

@app.route('/batch/video/ingest',methods=['GET','POST'])
def videoCreationBatch():
    from auth import get_user, is_superuser
    if not is_superuser():
        return action_401()
    if request.method=="GET":
        chdir(config.INGEST_DIRECTORY)
        files=[f for f in listdir(getcwd()) if f[0] != '.']
        return json.dumps(files)
    else:
        packet=request.json

        ids = [up.get('id') for up in packet]

        if len(set(ids)) is not len(ids):
            return bundle_400("Duplicate IDs found. Cannot update." % s)

        # test everything before we start ingesting, otherwise half the batch
        # might get completed before we get an error. easier to just reject everything
        # than half of everything
        for up in packet:
            i = up['id']
            dupe = assets.find_one({'@graph.ma:locator': {'$elemMatch': {'@id': i}}})
            mp4 = (unicode(config.MEDIA_DIRECTORY) + i + '.mp4').encode('utf-8')
            webm = (unicode(config.MEDIA_DIRECTORY) + i + '.webm').encode('utf-8')
            if path.isfile(mp4) or path.isfile(webm) or dupe is not None:
                return bundle_400("That file (%s) already exists; try another unique ID." %i)

        for up in packet:
            result = MediaAsset.set_new_file(up['pid'], up['id'], up['filepath'])
            if not result[0]:
                return bundle_400(result[1])

	return "Success"

class AssetGroup(Resource):
    collection=ags
    model=ags.AssetGroup
    namespace="hummedia:id/collection"
    endpoint="collection"
    override_only_triggers=['enrollment']
    
    def set_query(self):
        if "dc:creator" in self.request.args:
            return {"@graph.dc:creator":self.request.args.get("dc:creator")}
        elif "read" in self.request.args:
            read = self.request.args.get("read")
            return {"$or": [
                {"@graph.dc:creator": read},
                {"@graph.dc:rights.read": {"$in": [read]}},
            ]}
        return {}
        
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
        elif resolve_type(self.bundle["@graph"]["dc:type"]) in ["course_collection","themed_collection"]:
            return role=="student" and (is_enrolled(self.bundle) or username in self.bundle["@graph"]["dc:rights"]["read"])
	else:
            return False
            
    def preprocess_bundle(self):
        self.bundle["@graph"]["dc:identifier"] = "%s/%s" % (self.namespace,str(self.bundle["_id"]))
        self.bundle["@graph"]["pid"] = str(self.bundle["_id"])
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.bundle["@graph"]["dc:creator"]=atts['username']

    def find_by_relations(self, video, collection):
        """ Finds any one annotation tied to a given video-collection pair """

        v=assets.find_one({"_id":str(video)})
        if v:
            annots=[]
            # don't include required edits in collection queries
            for coll in v["@graph"]["ma:isMemberOf"]:
                if coll["@id"]==str(collection) and "restrictor" in coll:
                    annots.append(str(coll['restrictor']))
            q={"_id":{'$in':annots}}
            return annotations.find_one(q)

        return None
        
        
    def serialize_bundle(self,payload):
        if payload:
            v=assets.find({"@graph.ma:isMemberOf.@id":payload["_id"]})
            payload["@graph"]["videos"]=[]
            if not is_enrolled(payload) and not (payload['@graph']['dc:coverage'] == 'public'):
                v=self.auth_filter(v)
            thumbRetriever=[]
            for vid in v:
                if self.request.args.get("full",False):
                    resource=uri_pattern(vid["@graph"]["pid"],config.APIHOST+"/video")    
                    vid["@graph"]["type"]=resolve_type(vid["@graph"]["dc:type"])
                    vid["@graph"]["resource"]=resource
                    vid["@graph"]["ma:image"]=[]
                    
                    annot=self.find_by_relations(vid['@graph']['pid'], payload['_id'])
                    try:
                        vid['@graph']['transcript']=bool(annot['@graph']['vcp:playSettings']['vcp:showTranscript'])
                    except (TypeError, KeyError):
                        vid['@graph']['transcript']=False

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
	return ({"resp":200})

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

    def get_collection_query(self, media_id, collection_id):
        q={"_id":False}
        v=assets.find_one({"_id":str(media_id)})
        if v:
            annots=[]
            # don't include required edits in collection queries
            for coll in v["@graph"]["ma:isMemberOf"]:
                if coll["@id"]==str(collection_id) and "restrictor" in coll:
                    annots.append(str(coll['restrictor']))
            q={"_id":{'$in':annots}}
        return q
    
    def set_query(self):
        if self.request.args.get("dc:relation",False):
            if self.request.args.get("collection"):
                q=self.get_collection_query(self.request.args.get('dc:relation'), self.request.args.get('collection'))
            else:
                q={"@graph.dc:relation":str(self.request.args.get("dc:relation"))}
        elif self.request.args.get("dc:creator",False):
            q={"@graph.dc:creator":self.request.args.get("dc:creator")}
        else:
            q={}
        return q

    def get(self, id, limit=0):
        client = self.request.args.get('client', None)
        if client == 'ic':
            video = self.request.args.get('dc:relation')
            collection = self.request.args.get('collection')
            return clients.lookup['ic']().serialize(request, video, collection)
        return super(Annotation, self).get(id, limit)

    def get_list(self):
        alist=[]
        self.bundle=self.auth_filter()
        for d in self.bundle:
            client = self.request.args.get("client",None)
            if client:
                alist.append(self.client_process(d,True))
            else:
                d["@graph"]["resource"]=uri_pattern(d["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)
                alist.append(d["@graph"])
        return mongo_jsonify(alist)
        
    def set_resource(self):
        self.bundle["@graph"]["resource"]=uri_pattern(self.bundle["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)
        
    def client_process(self,bundle=None,list=False,client=None):
        if not bundle:
            bundle=self.bundle
        if not client:
            client = self.request.args.get("client")

        c=clients.lookup[client]()
        m=assets.find_one(bundle["@graph"]["dc:relation"])
        m["@graph"]["resource"]=uri_pattern(m["@graph"]["pid"],config.APIHOST+"/video")
        m["@graph"]["type"]=resolve_type(m["@graph"]["dc:type"])
        m["@graph"]["url"]=[]
        for url in m["@graph"]["ma:locator"]:
            if m["@graph"]["type"]=="humvideo":
                host=config.HOST+"/video"
                ext="."+url["ma:hasFormat"].replace("video/","")
            elif m["@graph"]["type"]=="humaudio":
                host=config.HOST+"/video"
                ext="."+url["ma:hasFormat"].replace("audio/","")
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

    def acl_write_check(self, bundle=None):
        if super(Annotation, self).acl_write_check(bundle=self.bundle):
            return True

        from auth import get_profile
        atts=get_profile()

        collection = request.args.get('collection')
        method = request.method
        name = atts['username']

        if method == 'POST' and collection is not None:
          # does the user have write access to this?
          query = {
            "@graph.pid": collection,
            "$or": [
              {"@graph.dc:rights.write": {"$in": [name] }},
              {"@graph.dc:creator": name}
            ]
          }
          return ags.find_one(query) is not None
        else:
          pid = bundle['@graph']['pid']

          vid=assets.find_one(bundle["@graph"]["dc:relation"])
          required = True if pid in vid["@graph"].get("ma:hasPolicy") else False

          if required and atts['role'] == 'faculty':
              return True

          # check to see if has write access to the collection
          for col in vid['@graph']['ma:isMemberOf']:
              query = {
                "@graph.pid": col['@id'],
                "$or": [
                  {"@graph.dc:rights.write": {"$in": [name] }},
                  {"@graph.dc:creator": name}
                ]
              }
              if ags.find_one(query) is not None:
                  return True

        return False
        
    def set_disallowed_atts(self):
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.disallowed_atts.append("dc:creator")
    
    def set_attrs(self):
        import traceback
        from flask import send_file
        if "client" in self.request.args:
            client_name = self.request.args.get("client")
            c=clients.lookup[client_name]()
            packet=c.deserialize(self.request)
        else:
            packet=self.request.json
        for (k,v) in packet.items():
            if k=="dc:title":
                self.bundle["@graph"]["dc:title"]=unicode(v)
            elif k=="vcp:playSettings" and v:
                if self.bundle["@graph"]["vcp:playSettings"] is None:
                    self.bundle["@graph"]["vcp:playSettings"] = {}
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
            if "collection" in self.request.args:
		assets.update({"_id":self.bundle["@graph"]["dc:relation"],"@graph.ma:isMemberOf.@id":self.request.args["collection"]},{"$set":{"@graph.ma:isMemberOf.$.restrictor":self.bundle["_id"]}})
            else:
		assets.update({"_id":self.bundle["@graph"]["dc:relation"]},{"$addToSet":{"@graph.ma:hasPolicy":self.bundle["_id"]}})
	return ({"resp":200})
