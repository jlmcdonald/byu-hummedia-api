<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        xmlns:oa="http://www.w3.org/ns/openannotation/core/"
        xmlns:oax="http://www.w3.org/ns/openannotation/extension/"
        xmlns:dc="http://purl.org/dc/"
        xmlns:vcp="http://cvp.byu.edu/namespace/"
        xmlns:html="http://www.w3.org/1999/xhtml"
        rdf:about="http://humvideo.byu.edu/mediainfo/yt:EpohyP55WHo/"
version="1.0">
<xsl:output encoding="UTF-8" indent="no" media-type="application/json" method="text" omit-xml-declaration="yes"></xsl:output>
  <xsl:strip-space elements="*"></xsl:strip-space>

<xsl:template match="/">
{"media": [ 
{
<xsl:apply-templates select="//vcp:media"/>,
"tracks": [
{ "name": "<xsl:value-of select="//vcp:header/vcp:metadata/dc:title"/>",
"id": "<xsl:value-of select="//vcp:header/vcp:metadata/dc:identifier"/>",
"trackEvents" : [<xsl:apply-templates select="//vcp:commandlist"/>]
}
]
}
]}
</xsl:template>

<xsl:template match="vcp:media">
"id": "<xsl:value-of select="dc:identifier"/>",
"name":"<xsl:value-of select="dc:title"/>",
"url": [ "<xsl:apply-templates select="dc:source"/>" ],
<xsl:apply-templates select="following-sibling::vcp:playSettings"/>,
"target": "main"</xsl:template>

<xsl:template match="vcp:commandlist">
<xsl:apply-templates/>
</xsl:template>

<xsl:template match="vcp:playSettings">
"<xsl:value-of select="local-name()"/>": { <xsl:apply-templates/> }<xsl:if test="position()!=last()">,</xsl:if>
</xsl:template>

<xsl:template match="dc:title|dc:date|dc:identifier|vcp:forceRestricted|vcp:framerate|vcp:audioMargin|vcp:videoMargin|vcp:seekDelay">
<xsl:if test="node()">
"<xsl:value-of select="local-name()"/>": "<xsl:apply-templates/>"<xsl:if test="position()!=last()">,</xsl:if>
</xsl:if>
</xsl:template>

<xsl:template match="oa:annotation|oax:description|oax:classification">
<xsl:variable name='eventType'>
<xsl:call-template name="getEventType"><xsl:with-param name="annotType"><xsl:choose><xsl:when test="local-name()='annotation'"><xsl:value-of select="@vcp:hasPlaybackCommand"/></xsl:when><xsl:otherwise><xsl:value-of select="local-name()"/></xsl:otherwise></xsl:choose></xsl:with-param></xsl:call-template>
</xsl:variable>
<xsl:variable name='eventBody'><xsl:value-of select="@oa:hasBody"/></xsl:variable>
{"id": "TrackEvent<xsl:value-of select="position()-1"/>",
"type":"<xsl:value-of select="$eventType"/>",
"popcornOptions": <xsl:apply-templates select="." mode="options"/>
}<xsl:if test="position()!=last()">,</xsl:if>
</xsl:template>

<xsl:template name="getEventType">
<xsl:param name="annotType">annotation</xsl:param>
<xsl:choose>
<xsl:when test="$annotType='description'">modal</xsl:when>
<xsl:when test="$annotType='classification' or $annotType='reference' or $annotType='tag'">reference</xsl:when>
<xsl:otherwise><xsl:value-of select="$annotType"/></xsl:otherwise>
</xsl:choose>
</xsl:template>

<xsl:template match="oa:annotation|oax:description|oax:classification" mode="options">
<xsl:variable name="timecode" select="substring-after(@oa:hasTarget,'#t=')"/>
<xsl:variable name="format" select="substring-before($timecode,':')"/>
<xsl:variable name="timestamp" select="substring-after($timecode,':')"/>
<xsl:variable name="trigger" select="substring-before($timestamp,',')"/>
<xsl:variable name="target" select="substring-after($timestamp,',')"/>
{"start":"<xsl:value-of select="$trigger"/>",
"end":"<xsl:value-of select="$target"/>"
<xsl:choose>
<xsl:when test="local-name()='classification'">
,"item":"<xsl:value-of select="substring-before(dc:description,'|')"/>",
<xsl:if test="@oax:hasSemanticTag='vocabulary'">"text":"<xsl:value-of select="substring-after(dc:description,'|')"/>",</xsl:if>
"list":"<xsl:value-of select="@oax:hasSemanticTag"/>"
</xsl:when>
<xsl:when test="local-name()='description'">
,"description":"<xsl:apply-templates select="dc:description" mode="safe"/>"
</xsl:when>
</xsl:choose>,
"target":"<xsl:choose><xsl:when test="dc:description[@target]"><xsl:value-of select="dc:description/@target"/></xsl:when>
<xsl:when test="local-name()='description'"><xsl:value-of select="@oax:hasSemanticTag"/></xsl:when><xsl:otherwise>main</xsl:otherwise></xsl:choose>"}
</xsl:template> 

<xsl:template match="*" mode="safe">
  <xsl:choose>
    <xsl:when test="local-name()='a' or local-name()='p' or local-name()='br'">
      <xsl:variable name="newelement">
        <xsl:value-of select="local-name()"/> 
      </xsl:variable>
      <xsl:text>&lt;</xsl:text><xsl:value-of select="$newelement"/><xsl:if test="not(node())">/</xsl:if><xsl:text>&gt;</xsl:text> <xsl:apply-templates mode="safe"/><xsl:if test="node()"><xsl:text>&lt;/</xsl:text><xsl:value-of select="$newelement"/><xsl:text>&gt;</xsl:text></xsl:if>
    </xsl:when>
    <xsl:otherwise>
     <xsl:apply-templates mode="safe"/>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>
  
</xsl:stylesheet>
