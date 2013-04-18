from flask import Response
import json, helpers

class Popcorn_Client():
    def deserialize(self,request):
        types={"reference":"oax:classification","modal":"oax:description"}
        packet={}
        if "id" in request.json["media"][0]:
            packet["dc:relation"]=request.json["media"][0]["id"]
        if "creator" in request.json:
            packet["dc:creator"]=request.json["creator"]
        for track in request.json["media"][0]["tracks"]:
            if "name" in track:
                packet["dc:title"]=track["name"]
            if "settings" in track:
                packet["vcp:playSettings"]=track["settings"]
            packet["vcp:commands"]=[]
            for event in track["trackEvents"]:
                etype=types[event["type"]] if event["type"] in types else "oa:annotation"
                npt="npt:%s,%s" % (event["popcornOptions"]["start"],event["popcornOptions"]["end"])
                if "target" in event["popcornOptions"]:
                    if event["type"]=="reference":
                        semantic=event["popcornOptions"]["list"]
                    elif event["popcornOptions"]["target"]=="main":
                        semantic=event["type"]
                    else:
                        semantic=event["popcornOptions"]["target"]
                    target=event["popcornOptions"]["target"]
                else:
                    semantic=event["type"]
                    target=None
                b={etype:{"oax:hasSemanticTag":semantic,"oa:hasTarget":npt}}
                if "text" in event["popcornOptions"] or "item" in event["popcornOptions"]:
                    hasBody={}
                    if "text" in event["popcornOptions"]:
                        hasBody["content"]=event["popcornOptions"]["text"]
                    if "item" in event["popcornOptions"]:
                        hasBody["dc:title"]=event["popcornOptions"]["item"]
                    if target:
                        hasBody["@target"]=target
                    b[etype]["oa:hasBody"]=hasBody
                packet["vcp:commands"].append(b)
        return packet                
    
    def serialize(self,obj,media):
        types={"oax:classification": "reference","oax:description":"modal"}
        popcorn={"targets":[],"media":[],"creator": obj["dc:creator"]}
        targets=["main","_caption","popup","sidebar"]
        for i in range(0,len(targets)):
           popcorn["targets"].append({
    		"id": "Target"+str(i),
    		"name": "Target"+str(i),
    		"element": targets[i]
    	   })
        popcorn["media"].append({
        	"id": media["pid"],
        	"url": [media["url"]],
        	"duration": media["ma:duration"],
        	"name": media["ma:title"],
        	"target": "player",
        	"tracks": [{"name":obj["dc:title"],"id":obj["pid"],"settings":obj["vcp:playSettings"],"trackEvents":[]}]
        })
        for a in range(0,len(obj["vcp:commands"])):
            event={"id":"TrackEvent"+str(a)}
            for (ctype,command) in obj["vcp:commands"][a].items():
                event["type"]=types[ctype] if ctype in types else command["oax:hasSemanticTag"]
                event["popcornOptions"]=helpers.parse_npt(command["oa:hasTarget"])
                if "oa:hasBody" in command:
                    event["popcornOptions"]["target"]=command["oa:hasBody"]["target"] if "target" in command["oa:hasBody"] else command["oax:hasSemanticTag"]
                else:
                    event["popcornOptions"]["target"]="main"
                if event["type"]in ("reference","modal"):
                    event["popcornOptions"]["item"]=command["oa:hasBody"]["dc:title"]
                    event["popcornOptions"]["text"]=command["oa:hasBody"]["content"]
                if event["type"]=="reference":
                    event["popcornOptions"]["list"]=command["oax:hasSemanticTag"]          
            popcorn["media"][0]["tracks"][0]["trackEvents"].append(event)
        return Response(json.dumps(popcorn, cls=helpers.mongokitJSON),status=200,mimetype="application/json")
        
lookup={"popcorn": Popcorn_Client}
