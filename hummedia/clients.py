from flask import Response
import json, helpers, copy
from auth import get_user
import config

class Client():
  pass

class Popcorn_Client(Client):
    TYPES={"oax:classification": "reference","oax:description":"modal","oax:comment":"comment","oax:question":"interaction","oax:link":"link"}
    TARGETS={"popup":"target-0","comment":"target-1","reference":"target-2","interaction":"target-3", "link":"target-4"}
    def deserialize(self,request):
        # invert the type map
        types=dict((v,k) for k, v in copy.deepcopy(self.TYPES).items())
        targets=dict((v,k) for k, v in copy.deepcopy(self.TARGETS).items())
        packet={}
        packet["dc:relation"]=request.json["media"][0].get("id")
        packet["dc:creator"]=request.json.get("creator") if "creator" in request.json else get_user()

        for idx,track in enumerate(request.json["media"][0]["tracks"]):
            if idx==0:
                packet["dc:title"]=track.get("name")
                packet["vcp:playSettings"]=track.get("settings")
                packet["vcp:commands"]=[]
            for event in track["trackEvents"]:
                if event["type"] in types:
                    etype=types[event["type"]]
                elif event["popcornOptions"].get("target")=="target-4":
                    etype="oax:link"
                else:
                    etype="oa:annotation"
                if event["popcornOptions"]["target"] not in ["target-0","target-4"]:
                    if etype=="oax:comment":
                        semantic="note"
                    elif etype=="oax:classification":
                        semantic=event["popcornOptions"]["list"]
                    elif etype=="oax:question":
                        semantic="question"
                    else:
                        semantic=targets[event["popcornOptions"]["target"]]
                else:
                    semantic=event["type"] if etype!="oax:description" else "popup"
                end=event["popcornOptions"]["end"] if event["popcornOptions"]["end"] != "0" else ""
                npt="npt:%s,%s" % (event["popcornOptions"]["start"],end)
                b={etype:{"oax:hasSemanticTag":semantic,"oa:hasTarget":npt}}
                if "text" in event["popcornOptions"] or "item" in event["popcornOptions"]:
                    hasBody={"content":event["popcornOptions"].get("text"),"dc:title":event["popcornOptions"].get("item")}
                    if etype=="oax:link":
                        hasBody["content"],hasBody["dc:title"]=hasBody["dc:title"],hasBody["content"]
                    b[etype]["oa:hasBody"]=hasBody
                packet["vcp:commands"].append(b)
        return packet                
    
    def serialize(self,obj,media,resp=True,required=False):
        types=copy.deepcopy(self.TYPES)
        popcorn={"targets":[],"media":[],"creator": obj["dc:creator"]}
        popcorn["media"].append({
        	"id": media["pid"],
        	"url": media["url"],
        	"duration": media["ma:duration"],
        	"name": media["ma:title"],
        	"target": "player",
        	"tracks": [{"name":obj["dc:title"],"id":obj["pid"],"settings":obj["vcp:playSettings"],"required":required,"trackEvents":[]}]
        })
        for a in obj["vcp:commands"]:
            event={}
            for (ctype,command) in a.items():
                event["type"]=types[ctype] if ctype in types else command["oax:hasSemanticTag"]
                event["popcornOptions"]=helpers.parse_npt(command["oa:hasTarget"])
                event["popcornOptions"]["target"]=self.TARGETS[event['type']] if event['type'] in self.TARGETS else "target-0"
                if event["type"]in ("reference","modal","comment","interaction"):
                    event["popcornOptions"]["item"]=command["oa:hasBody"].get("dc:title")
                    event["popcornOptions"]["text"]=command["oa:hasBody"]["content"]
                if event["type"]=="reference":
                    event["popcornOptions"]["list"]=command["oax:hasSemanticTag"]
                if event["type"]=="link":
                    event["popcornOptions"]["item"]=command["oa:hasBody"]["content"]
                    event["popcornOptions"]["text"]=command["oa:hasBody"]["dc:title"]
                    if command["oax:hasSemanticTag"] in ["freebase-search","google-search","youtube-search"]:
			event["type"]=command["oax:hasSemanticTag"]
		    else:
		    	event["popcornOptions"]["service"]=command["oax:hasSemanticTag"]     
            popcorn["media"][0]["tracks"][0]["trackEvents"].append(event)
        if resp:
            return Response(json.dumps(popcorn, cls=helpers.mongokitJSON),status=200,mimetype="application/json")
        else:
            return popcorn

class IC_Client(Client):
    ''' For the international cinema. Provides a zip file. Serialization only '''

    def serialize(self, request, video_id, collection_id):

        import json, string, io
        import traceback
        import tempfile
        from flask import send_file
        from zipfile import ZipFile
        from resources import Annotation, MediaAsset

        media = MediaAsset.collection.find_one({'_id': video_id})['@graph']

        annotations = []

        a = Annotation(request=request)
        for _id in media.get('ma:hasPolicy',[]):
            required_bundle = Annotation.collection.find_one({'_id': _id})
            required = a.client_process(bundle=required_bundle, client='popcorn')
            annotations.append(json.loads(required.data))

        query = Annotation(request).get_collection_query(video_id, collection_id)
        collection_bundle = Annotation.collection.find(query)

        if collection_bundle is not None:
            for c in collection_bundle:
                collection = a.client_process(bundle=c, client='popcorn')
                annotations.append(json.loads(collection.data))

        filename = filter(lambda x: x in string.ascii_letters, media['ma:title'])

        try:
            subtitle_name = media['ma:hasRelatedResource'][0]['@id'].split('/')[-1]
            subtitle = config.SUBTITLE_DIRECTORY + subtitle_name
        except (KeyError, IndexError) as e:
            subtitle = None

        icf = {
            'video': filename + '.mp4',
            'annotation': filename + '.json',
            'subtitle': None if subtitle is None else filename + '.vtt'
        }


        zipholder = tempfile.NamedTemporaryFile()
        z = ZipFile(zipholder, 'w')
        z.writestr(filename + '.json', json.dumps(annotations))
        z.writestr(filename + '.icf', json.dumps(icf))
        if subtitle is not None:
            z.write(subtitle, filename + '.vtt')

        z.close()

        return send_file(
            zipholder.name,
            mimetype='application/zip',
            as_attachment=True,
            attachment_filename=media['ma:title'] + '.zip'
        )

lookup={"popcorn": Popcorn_Client, "ic": IC_Client}
