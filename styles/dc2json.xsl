<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        xmlns:oa="http://www.w3.org/ns/openannotation/core/"
        xmlns:oax="http://www.w3.org/ns/openannotation/extension/"
        xmlns:dc="http://purl.org/dc/elements/1.1/"
        xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
        xmlns:foxml="info:fedora/fedora-system:def/foxml#"
        xmlns:html="http://www.w3.org/1999/xhtml"
        rdf:about="#"
version="1.0">
<xsl:output encoding="UTF-8" indent="no" media-type="application/json" method="text" omit-xml-declaration="yes"></xsl:output>
  <xsl:variable name="subject"/>
  
  <xsl:strip-space elements="*"></xsl:strip-space>

  <xsl:template name="escapeQuote">
    <xsl:param name="pText" select="."/>
    
    <xsl:if test="string-length($pText) >0">
      <xsl:value-of select=
        "substring-before(concat($pText, '&quot;'), '&quot;')"/>
      
      <xsl:if test="contains($pText, '&quot;')">
        <xsl:text>\"</xsl:text>
        
        <xsl:call-template name="escapeQuote">
          <xsl:with-param name="pText" select=
            "substring-after($pText, '&quot;')"/>
        </xsl:call-template>
      </xsl:if>
    </xsl:if>
  </xsl:template>

<xsl:template match="oai_dc:dc">{<xsl:for-each select="*[not(self::dc:subject)][text()]"><xsl:if test="node()">"<xsl:value-of select="local-name()"/>": "<xsl:call-template name="escapeQuote"/>"<xsl:if test="position()!=last()">,</xsl:if></xsl:if></xsl:for-each><xsl:if test="dc:subject">,"subject": "<xsl:for-each select="dc:subject"><xsl:call-template name="escapeQuote"/><xsl:if test="position()!=last()">,</xsl:if></xsl:for-each>"</xsl:if>}</xsl:template>
</xsl:stylesheet>
