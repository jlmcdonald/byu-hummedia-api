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
  <xsl:strip-space elements="*"></xsl:strip-space>

<xsl:template match="/">
{
  <xsl:for-each select="*">
    <xsl:if test="node()">
      "<xsl:value-of select="local-name()"/>": "<xsl:apply-templates/>"<xsl:if test="position()!=last()">,</xsl:if>
    </xsl:if>
  </xsl:for-each>
}
</xsl:template>

</xsl:stylesheet>
