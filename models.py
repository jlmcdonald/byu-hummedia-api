from mongokit import Document, Connection, CustomType, ObjectId
import datetime

class IsoDate(CustomType):
    mongo_type = unicode
    python_type = datetime.datetime
    init_type = None

    def to_bson(self, value):
        return unicode(datetime.datetime.strftime(value,'%Y-%m-%d'))

    def to_python(self, value):
        if value is not None:
	    return datetime.datetime.strptime(value, '%Y-%m-%d')

connection=Connection()

@connection.register
class AnnotationList(Document):
	__collection__="annotations"
	__database__="hummedia"
	use_schemaless=True
	structure= {
		"@context": dict,
		"@graph": {
	        "pid": basestring,
	        "dc:identifier":basestring,
			"dc:title": unicode,
			"dc:relation": ObjectId,
	        "dc:creator": basestring,
	        "dc:date":IsoDate(),
	        "vcp:playSettings": dict,
	        "vcp:commands":[dict]
		}
	}
	required_fields=["@context","@graph.dc:creator",
	                 "@graph.dc:date","@graph.dc:title","@graph.vcp:playSettings"]
	default_values={
		"@context": {
    		"dc":"http://purl.org/dc/",
			"oa":"http://www.w3.org/ns/oa#",
			"oax":"http://www.w3.org/ns/openannotation/extension/",
			"vcp":"http://cvp.byu.edu/namespace/",
	        "dc:identifier": "@id"    
  		},
	    "@graph.dc:creator":"Hummedia",
	    "@graph.dc:title":u"New Hummedia Annotation",
	    "@graph.dc:date":datetime.datetime.utcnow(),
	    "@graph.vcp:playSettings": {
			"vcp:audioOffset":0,
			"vcp:videoOffset":0,
			"vcp:videoCrop":0,
			"vcp:frameRate":23.976
		}     
	}

@connection.register
class AssetGroup(Document):
	__collection__="assetgroups"
	__database__="hummedia"
	use_schemaless=True
	structure= {
		"@context": dict,
		"@graph": {
	        "pid": basestring,
	        "dc:identifier":basestring,
			"dc:type": basestring,
			"dc:title": unicode,
			"dc:description": unicode,
			"dc:relation": basestring,
			"dc:creator": basestring,
			"dc:date":IsoDate(),
			"dc:coverage": int
		}
	}
	required_fields=["@context","@graph.dc:type","@graph.dc:creator",
	                 "@graph.dc:date","@graph.dc:title"]
	default_values={
		"@context": {
    			"dc": "http://purl.org/dc/elements/1.1/",
    			"hummedia": "http://humanities.byu.edu/hummedia/",
	                "dc:identifier": "@id",
	                "dc:type": "@type"
  		},
	        "@graph.dc:creator":"Hummedia",
	        "@graph.dc:title":u"New Hummedia Collection",
		"@graph.dc:type":"hummedia:type/course_collection",
	        "@graph.dc:date":datetime.datetime.utcnow(),        
	}
	


@connection.register
class Video(Document):
	__collection__="assets"
	__database__="hummedia"
	use_schemaless=True
	structure= {
		"@context": dict,
		"ititle":unicode,
		"@graph": {
	                "dc:creator": basestring,
	                "dc:date": IsoDate(),	
			"dc:identifier": basestring,
			"dc:type": basestring,
			"ma:averageBitRate": int,
			"ma:isCopyrightedBy": {
            			"@id": basestring,
            			"name": unicode
       			},
      			"ma:date": int,
      			"ma:description": unicode,
      			"ma:duration": int,
      			"ma:features": [
          			{ 
					"@id": basestring,
            				"name": unicode
           			}
       			],
		      	"ma:frameHeight": int,
      			"ma:frameRate": float,
      			"ma:frameSizeUnit": basestring,
      			"ma:frameWidth": int,
      			"ma:hasCompression": {
        			"@id": basestring,
        			"name": basestring
      			},
      			"ma:hasContributor": [
				{
        				"@id": basestring,
        				"name": unicode  
      				}
			],
      			"ma:hasFormat": basestring,
      			"ma:hasGenre": {
        			"@id": basestring,
        			"name": unicode
      			},
      			"ma:hasLanguage": [basestring],
      			"ma:hasPolicy": basestring,
      			"ma:isMemberOf": [dict],
      			"ma:isRelatedTo": [basestring],
      			"ma:hasKeyword": [basestring],
      			"ma:locator": basestring,
      			"ma:title": unicode
    		}

	}
	required_fields=["@context","@graph.dc:creator","@graph.dc:date","@graph.dc:type","@graph.ma:date","@graph.ma:hasLanguage","@graph.ma:title"]
	default_values={
		"@context": {
    			"dc": "http://purl.org/dc/elements/1.1/",
	                "dc:identifier": "@id",
	                "dc:type": "@type",
    			"ma": "http://www.w3.org/ns/ma-ont/",
    			"hummedia": "http://humanities.byu.edu/hummedia/"
  		},
	        "@graph.ma:hasCompression.@id":"http://www.freebase.com/view/en/h_264_mpeg_4_avc",
	        "@graph.ma:hasCompression.name": "avc.42E01E",	        
	        "@graph.dc:creator":"Hummedia",
		"@graph.dc:date": datetime.datetime.utcnow(),
		"@graph.dc:type": "hummedia:type/humvideo",
	        "@graph.ma:title":u"New Hummedia Video",
	        "@graph.ma:date": 1900,
	        "@graph.ma:hasLanguage":["en"],
	        "@graph.ma:hasPolicy":"BYU",
	        "@graph.ma:hasFormat": "video/mp4",
	        "@graph.ma:frameRate": 23.976,
	        "@graph.ma:averageBitRate":768000,
	        "@graph.ma:frameHeight": 360,
	        "@graph.ma:frameWidth": 640,
	        "@graph.ma:frameSizeUnit":"px"
	}

	def make_part(self,vid,host,part):
		from helpers import uri_pattern
		resource=uri_pattern(vid["pid"],host+"/video")
		thepart={"ma:title":vid["ma:title"],"pid":vid["pid"],"resource":resource}
		if part!="snippet":
			thepart["ma:date"]=vid["ma:date"]
			thepart["ma:description"]=vid["ma:description"]
			thepart["ma:hasLanguage"]=vid["ma:hasLanguage"]
		return thepart
