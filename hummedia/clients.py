from flask import Response
import json, helpers

class Popcorn_Client():
    def deserialize(self,request):
        types={"reference":"oax:classification","modal":"oax:description","comment":"oax:comment"}
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
    
    def serialize(self,obj,media,resp=True,required=False):
        types={"oax:classification": "reference","oax:description":"modal","oax:comment":"comment","oax:question":"interaction","oax:link":"link"}
        targets={"comment":"target-1","reference":"target-2","interaction":"target-3", "link":"target-3"}
        popcorn={"targets":[],"media":[],"creator": obj["dc:creator"]}
        popcorn["media"].append({
        	"id": media["pid"],
        	"url": media["url"],
        	"duration": media["ma:duration"],
        	"name": media["ma:title"],
        	"target": "player",
        	"tracks": [{"name":obj["dc:title"],"id":obj["pid"],"settings":obj["vcp:playSettings"],"required":required,"trackEvents":[]}]
        })
        #for a in range(0,len(obj["vcp:commands"])):
        for a in obj["vcp:commands"]:
            event={}
            #for (ctype,command) in obj["vcp:commands"][a].items():
            for (ctype,command) in a.items():
                event["type"]=types[ctype] if ctype in types else command["oax:hasSemanticTag"]
                event["popcornOptions"]=helpers.parse_npt(command["oa:hasTarget"])
                event["popcornOptions"]["target"]=targets[event['type']] if event['type'] in targets else "target-0"
                if event["type"]in ("reference","modal","comment","interaction"):
                    event["popcornOptions"]["item"]=command["oa:hasBody"]["dc:title"]
                    event["popcornOptions"]["text"]=command["oa:hasBody"]["content"]
                if event["type"]=="reference":
                    event["popcornOptions"]["list"]=command["oax:hasSemanticTag"]
                if event["type"]=="link":
                    event["popcornOptions"]["item"]=command["oa:hasBody"]["content"]
                    if command["oax:hasSemanticTag"] in ["freebase-search","google-search","youtube-search"]:
			event["type"]=command["oax:hasSemanticTag"]
		    else:
		    	event["popcornOptions"]["service"]=command["oax:hasSemanticTag"]     
            popcorn["media"][0]["tracks"][0]["trackEvents"].append(event)
        if resp:
            return Response(json.dumps(popcorn, cls=helpers.mongokitJSON),status=200,mimetype="application/json")
        else:
            return popcorn
        
lookup={"popcorn": Popcorn_Client}
