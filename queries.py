def vcpList(filter=None,**kwargs):
	if filter=="video":
		return "SELECT ?object ?title ?pid FROM <#ri>\nWHERE {\n?object <fedora-rels-ext:isAnnotationOf> <info:fedora/%s> ;\n\t<dc:title> ?title ;\n\t<dc:identifier> ?pid .\n}" % (kwargs['pid'])

	else:
		return "SELECT ?object ?title ?pid FROM <#ri>\nWHERE {\n?object <fedora-model:hasModel> <data:VideoclipPlaylistModel> ;\n\t<dc:title> ?title ;\n\t<dc:identifier> ?pid .\n}\nORDER BY ?pid"
	
def collectionList(filter=None,**kwargs):
	if filter=="creator":
		whereFilter=";\n\t<dc:creator> '%s' " % (kwargs['netid'])
	else:
		whereFilter=""
	return "SELECT ?object ?title ?pid FROM <#ri>\nWHERE {\n?object <fedora-model:hasModel> <collection:VideoCollectionModel> ;\n\t<dc:title> ?title ;\n\t<dc:identifier> ?pid %s.\n}\nORDER BY ?title" % (whereFilter)

def videoList(filter=None,**kwargs):
	if filter=="creator":
		whereFilter=";\n\t<dc:creator> '%s' " % (kwargs['netid'])
	else:
		whereFilter=""
	return "SELECT ?object ?title ?pid FROM <#ri>\nWHERE {\n?object <fedora-model:hasModel> <media:VideoAssetModel> ;\n\t<dc:title> ?title ;\n\t<dc:identifier> ?pid %s.\n}\nORDER BY ?title" % (whereFilter)

def mediaInCollection(filter=None,**kwargs):
	return "select $a $b\nsubquery ( select $pid from <#ri>\nwhere $a <dc:identifier> $pid)\nfrom <#ri>\nwhere  walk (\n$a <fedora-rels-ext:isMemberOf> <info:fedora/%s>\nand $a <fedora-rels-ext:isMemberOf> $b)\nminus $a <fedora-model:hasModel> <collection:VideoCollectionModel>" % (kwargs['pid'])

#class CollectionsWithSchedule:
#    def GET(self,id):
#	return "SELECT ?object FROM <#ri>\nWHERE { ?object <http://humtv.byu.edu/tvinfo/namespace/hasSchedule> <http://humtv.byu.edu/tvinfo/schedule/%s> . }" % (id)

#class CollectionList:
#    def GET(self,id):
	#return "SELECT ?object ?title FROM <#ri>\nWHERE {\n?object <fedora-model:hasModel> <collection:VideoCollectionModel> ;\n\t<dc:title> ?title ;\n}"


#class RecordingsFromSchedule:
#    def GET(self,id):
#	return "SELECT ?object ?broadcastDate ?createdDate ?location ?pid FROM <#ri>\nWHERE {\n?object <http://humtv.byu.edu/tvinfo/namespace/isRecordingOf> <http://humtv.byu.edu/tvinfo/schedule/%s> ;\n\t<dc:date> ?broadcastDate ;\n\t<fedora-model:createdDate> ?createdDate ;\n\t<dc:source> ?location ;\n\t<dc:identifier> ?pid . \n}\nORDER BY ?createdDate" % (id)

#class MediaInCollection:
#    def GET(self,id):
#	return "select $a $b\nsubquery ( select $pid $broadcastDate $createdDate $location $title $type $desc $rights $coverage from <#ri>\nwhere $a <dc:identifier> $pid\nand $a <dc:date> $broadcastDate\nand $a <fedora-model:createdDate> $createdDate\nand $a <dc:source> $location\nand $a <dc:rights> $rights\nand $a <dc:coverage> $coverage\nand $a <dc:title> $title\nand $a <dc:type> $type\nand $a <dc:description> $desc\norder by $type $createdDate $title desc)\nfrom <#ri>\nwhere  walk (\n$a <fedora-rels-ext:isMemberOf> <info:fedora/collection:%s>\nand $a <fedora-rels-ext:isMemberOf> $b)\nminus $a <fedora-model:hasModel> <collection:VideoCollectionModel>" % (id)

#class PlaylistForVideo:
#    def GET(self,pid):
#	return "SELECT ?object ?title ?pid FROM <#ri>\nWHERE {\n?object <fedora-rels-ext:isAnnotationOf> <info:fedora/%s> ;\n\t<dc:title> ?title ;\n\t<dc:identifier> ?pid .\n}" % (pid)

#class CollectionInCollection:
#    def GET(self,id):
#	return "SELECT ?object ?title ?pid ?desc FROM <#ri>\nWHERE {\n?object <fedora-rels-ext:isMemberOf> <info:fedora/collection:%s> ;\n\t<fedora-model:hasModel> <collection:VideoCollectionModel> ;\n\t<dc:title> ?title ;\n\t<dc:description> ?desc ;\n\t<dc:identifier> ?pid .\n}" % (id)

#class CollectionOfPlaylists:
#    def GET(self,vcplist):
#	return "PREFIX dc: <http://purl.org/dc/elements/1.1/>\nSELECT ?object ?title ?pid ?asset\nWHERE {\n?object <fedora-model:hasModel> <data:VideoclipPlaylistModel> ;\n\tdc:identifier ?pid ;\n\tdc:title ?title .\n?object <fedora-rels-ext:isAnnotationOf> ?asset .\nFILTER regex(?pid, \"(%s)\")\n}" % (vcplist)

