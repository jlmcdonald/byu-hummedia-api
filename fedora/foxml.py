from lxml import etree
from copy import deepcopy
from datetime import datetime
from services.namespaces import *

class Foxml:
	def __init__(self,id,namespace="media",owner="fedoraAdmin"):
		self.id = id
		self.namespace = namespace
		self.owner=owner
		self.pid="%s:%s" % (namespace,id)
		self.addStreams=[]

	def getLabel(self):
		return self.title

	def buildDublinCore(self,atts={}):
		NSMAP = {"oai_dc" : OAI_DC_NAMESPACE, "dc" : DC_NAMESPACE}
		self.dc = etree.Element(OAI_DC + "dc", nsmap=NSMAP)
		pid = etree.SubElement(self.dc, DC+"identifier")
		pid.text = self.pid
		for k,v in atts.items():
			if k=="subject" or k=="language":
				for e in v:
					element=etree.SubElement(self.dc,DC+k)
					element.text=e
			elif k in ["title","description","coverage","creator","rights","date","type","source","relation","publisher","contributor","format"]:
				element=etree.SubElement(self.dc,DC+k)
				try:
					element.text=v
				except ValueError:
					element.text=""
		self.title = atts["title"]

	def buildRdf(self,model,model_namespace,rels={}):
		NSMAP = {"rdf":RDF_NAMESPACE}
		self.rdf = etree.Element(RDF + "RDF",nsmap=NSMAP)
		desc = etree.SubElement(self.rdf, RDF+"Description")
		desc.set(RDF+"about","info:fedora/%s" % (self.pid))
		hasModel = etree.SubElement(desc,RELS_EXT_MODEL+"hasModel",nsmap={"fedora-model":RELS_EXT_MODEL_NAMESPACE})
		hasModel.set(RDF+"resource",model_namespace+":"+model)
		for rel in rels:
			ADD_NS = "{%s}" % rel["namespace"]
			addRel = etree.SubElement(desc,ADD_NS+rel["predicate"],nsmap={rel["namespacePrefix"]:rel["namespace"]})
			addRel.set(RDF+"resource",rel["object"])

	def buildAdditionalStream(self,dstuple):
		self.addStreams.append(dstuple)

	def buildFoxml(self):
		NSMAP = {"foxml":FOXML_NAMESPACE, "xsi":XSI_NAMESPACE}
		self.foxml = etree.Element(FOXML + "digitalObject",nsmap=NSMAP)
		self.foxml.set("PID","%s" % (self.pid))
		self.foxml.set("VERSION","1.1")
		self.foxml.set(XSI+"schemaLocation","info:fedora/fedora-system:def/foxml# http://www.fedora.info/definitions/1/0/foxml1-1.xsd")
		objectProperties = etree.SubElement(self.foxml,FOXML+"objectProperties")
		state = etree.SubElement(objectProperties,FOXML+"property")
		state.set("NAME","info:fedora/fedora-system:def/model#state")
		state.set("VALUE","Active")
		label = etree.SubElement(objectProperties,FOXML+"property")
		label.set("NAME","info:fedora/fedora-system:def/model#label")
		label.set("VALUE",self.title)
		ownerId = etree.SubElement(objectProperties,FOXML+"property")
		ownerId.set("NAME","info:fedora/fedora-system:def/model#ownerId")
		ownerId.set("VALUE",self.owner)
		createdDate = etree.SubElement(objectProperties,FOXML+"property")
		createdDate.set("NAME","info:fedora/fedora-system:def/model#createdDate")
		createdDate.set("VALUE",str(datetime.today().isoformat()))
		lastModifiedDate = etree.SubElement(objectProperties,FOXML+"property")
		lastModifiedDate.set("NAME","info:fedora/fedora-system:def/view#lastModifiedDate")
		lastModifiedDate.set("VALUE",str(datetime.today().isoformat()))
		dc = etree.SubElement(self.foxml,FOXML+"datastream")
		dc.set("CONTROL_GROUP","X")
		dc.set("ID","DC")
		dc.set("STATE","A")
		dc.set("VERSIONABLE","true")
		version=etree.SubElement(dc,FOXML+"datastreamVersion")
		version.set("CREATED",str(datetime.today().isoformat()))
		version.set("FORMAT_URI","http://www.openarchives.org/OAI/2.0/oai_dc")
		version.set("ID","DC1.0")
		version.set("LABEL","Dublin Core Record for this object")
		version.set("MIMETYPE","text/xml")
		version.set("SIZE",str(len(etree.tostring(self.dc))))
		content=etree.SubElement(version,FOXML+"xmlContent")
		content.append(deepcopy(self.dc))
		del version

		relsext = etree.SubElement(self.foxml,FOXML+"datastream")
		relsext.set("CONTROL_GROUP","X")
		relsext.set("ID","RELS-EXT")
		relsext.set("STATE","A")
		relsext.set("VERSIONABLE","true")
		version=etree.SubElement(relsext,FOXML+"datastreamVersion")
		version.set("CREATED",str(datetime.today().isoformat()))
		version.set("FORMAT_URI","info:fedora/fedora-system:FedoraRELSExt-1.0")
		version.set("ID","RELS-EXT.0")
		version.set("LABEL","RDF Statements about this object")
		version.set("MIMETYPE","application/rdf+xml")
		version.set("SIZE",str(len(etree.tostring(self.rdf))))
		content=etree.SubElement(version,FOXML+"xmlContent")
		content.append(deepcopy(self.rdf))
		del version

		for ds in self.addStreams:
			addstream = etree.SubElement(self.foxml,FOXML+"datastream")
			addstream.set("CONTROL_GROUP","X")
			addstream.set("ID",ds[0])
			addstream.set("STATE","A")
			addstream.set("VERSIONABLE","true")
			version=etree.SubElement(addstream,FOXML+"datastreamVersion")
			version.set("CREATED",str(datetime.today().isoformat()))
			version.set("FORMAT_URI","info:fedora/fedora-system:FedoraRELSExt-1.0")
			version.set("ID",ds[0]+".0")
			version.set("LABEL",ds[1])
			version.set("MIMETYPE","text/xml")
			version.set("SIZE",str(len(ds[2])))
			content=etree.SubElement(version,FOXML+"xmlContent")
			content.append(deepcopy(etree.fromstring(ds[2])))
			del version

		return(etree.tostring(self.foxml,pretty_print=True))
