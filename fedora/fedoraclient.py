from services.rest import Service
from services.namespaces import *
from lxml import etree
from urllib import quote, quote_plus

class FedoraClient:
	def __init__(self,authenticated=False,credentials=""):
		if authenticated:
			self.protocol="https"
			self.port="8443"
		else:
			self.protocol="http"
			self.port="8080"
		self.fedora_service=Service("humvideo.byu.edu",self.protocol,self.port)
		self.authenticated = authenticated
		self.credentials = credentials

	def checkCoverage(self,pid,scope):
		dc=self.getDataStream(pid,"DC")
		return dc.find(".//"+DC+"coverage").text==scope

	def getNextPid(self,namespace):
		service_params=["fedora","objects","nextPID?namespace=%s&format=xml" % (namespace)]
		return etree.fromstring(self.fedora_service.sendRequest(service_params,"POST",authenticated=True,credentials=self.credentials)).findtext(".//"+MANAGEMENT+"pid")

	def getLabel(self,pid):
		tree=etree.fromstring(self.findObjects(pid))
		return tree.find(".//"+RESULT+"label").text

	def findObjects(self,pid):
                service_params=["fedora","objects?resultFormat=xml&title=true&pid=true&creator=true&label=true&query=pid&terms=%s" % (pid)]
                return self.fedora_service.sendRequest(service_params)		

	def gSearch(self,query):
		resource="rest?operation=gfindObjects&restXslt=copyXml&query=%s" % (quote_plus(query))
		service_params=["fedoragsearch",resource]
		try:
	                return etree.fromstring(self.fedora_service.sendRequest(service_params))
		except Exception,err:
			return self.fedora_service.sendRequest(service_params,debug=True)
			return query

	def ingest(self,foxml,pid,label=""):
		(namespace,id)=str(pid).split(":")
                handler=pid+"?"+ quote("label=%s&namespace=%s&ownerId=1&logMessage=Ingested FOXML for %s" % (label.encode('utf-8'),namespace,id))
		return self.fedora_service.sendRequest(["fedora","objects",handler],"POST",foxml,"text/xml",authenticated=self.authenticated,credentials=self.credentials)

	def getObject(self,pid):
		service_params=["fedora","objects",pid,"objectXML"]
		return etree.fromstring(self.fedora_service.sendRequest(service_params,authenticated=self.authenticated,credentials=self.credentials))

	def getDataStream(self,pid,ds):
		service_params=["fedora","get","%s" % (pid),ds]
		return etree.fromstring(self.fedora_service.sendRequest(service_params))

	def modifyDatastream(self,pid,datastream,body):
		service_params=["fedora","objects","%s" % (pid), "datastreams",datastream]
		return self.fedora_service.sendRequest(service_params,"PUT",body,"text/xml",self.authenticated,self.credentials)

	def modifyObject(self,pid,label=None,owner=None,state=None,logMessage=None):
		if label or owner or state:
			query=[]
			if label:
				query.append("label=%s" % (quote(label.encode('utf-8'))))
			if owner:
				query.append("ownerId=%s" % (owner))
			if state:
				query.append("state=%s" % (quote(state)))
			if logMessage:
				query.append("logMessage=%s" % (logMessage))
			query="?"+"&".join(query)
		service_params=["fedora","objects","%s%s" % (pid,query)]
		return self.fedora_service.sendRequest(service_params,"PUT",authenticated=self.authenticated,credentials=self.credentials)		

	def changeLabel(self,pid,label):
		return self.modifyObject(pid,label=label)

	def purge(self,pid):
		return self.fedora_service.sendRequest(["fedora","objects",pid],"DELETE",authenticated=self.authenticated,credentials=self.credentials)

	def risearch(self,query,querylang="iTQL",queryformat="URL"):
		if queryformat=="text":
			query=quote_plus(query)
		service_params=["fedora","risearch?type=tuples&lang=%s&format=sparql&query=%s" % (querylang,query)]
                return self.fedora_service.sendRequest(service_params)

	def pidExists(self,pid):
                results=[]
                xml = etree.fromstring(self.findObjects(pid))
                for result in xml[0]:
                        results.append(result.findtext(".//"+RESULT+"pid"))
		if len(results)>0:
			return True
		else:
			return False

	def checkCreator(self, pid, personid):
                if etree.fromstring(self.findObjects(pid)).findtext(".//"+RESULT+"creator")==personid:
                	return True
		else:
			return False

	def addExternalRel(self,pid,rel,relns,relprefix,resource,attrs=None):
		if not rels_ext:
			rels_ext=self.getDataStream(pid,"RELS-EXT")
		REL = "{%s}" % (relns)
		NSMAP = {"rdf" : RDF_NAMESPACE, relprefix : relns}
		new = etree.SubElement(rels_ext[0],REL+rel,nsmap=NSMAP)
		new.set(RDF+"resource",resource)
		if attrs:
			for k,v in attrs.items():
				new.set(REL+k,v)
		return self.modifyDatastream(pid,"RELS-EXT",etree.tostring(rels_ext,pretty_print=True))

	def removeExternalRel(self,pid,rel,relns,resource):
		if not rels_ext:
			rels_ext=self.getDataStream(pid,"RELS-EXT")
		REL = "{%s}" % (relns)
		for r in rels_ext.iterfind(".//"+REL+rel):
			if r.get(RDF+"resource")==resource:
				r.getparent().remove(r) 		
		return self.modifyDatastream(pid,"RELS-EXT",etree.tostring(rels_ext,pretty_print=True))

	def addAsMemberOf(self,pid,collection):
		return self.addExternalRel(pid,"isMemberOf","info:fedora/fedora-system:def/relations-external#","fedora-rels-ext","collection:%s" % (collection))

	def removeAsMemberOf(self,pid,collection):
		return self.removeExternalRel(pid,"isMemberOf","info:fedora/fedora-system:def/relations-external#","collection:%s" % (collection))

	def updateMemberships(self,pid,collections,netid,isadmin,scope):
		#no granular security yet
		packet={"added":[],"denied":[],"netid":netid}
		rels_ext=self.getDataStream(pid,"RELS-EXT")
		for r in rels_ext.iterfind(".//"+RELS_EXT+"isMemberOf"):
			cpid=r.get(RDF+"resource")
			c=cpid.rpartition(":")[2]
			if isadmin or (c not in collections and self.checkCreator(cpid,netid)):
				r.getparent().remove(r)
		REL = RELS_EXT
		NSMAP = {"rdf" : RDF_NAMESPACE, "fedora-rels-ext" : RELS_EXT_NAMESPACE}
		for coll in collections:		
			if isadmin or ((self.checkCreator(pid,netid) or self.checkCoverage(pid,scope)) and self.checkCreator("collection:%s" % (coll),netid)):
				new = etree.SubElement(rels_ext[0],REL+"isMemberOf",nsmap=NSMAP)
				new.set(RDF+"resource","info:fedora/collection:%s" % (coll))
				packet["added"].append(coll)
			else:
				packet["denied"].append(coll)
		packet["success"] = self.modifyDatastream(pid,"RELS-EXT",etree.tostring(rels_ext,pretty_print=True))
		return packet
