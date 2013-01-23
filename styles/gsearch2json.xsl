<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    version="1.0">
    <xsl:output method="text" encoding="utf-8"/>
    <xsl:strip-space elements="*"/>
    <xsl:template match="/">
        [<xsl:for-each select=".//object">
            {
            "identifier": "<xsl:apply-templates select="field[@name='PID']"/>",
            "title": "<xsl:choose><xsl:when test="field[@name='TITLE_UNTOK']"><xsl:apply-templates select="field[@name='TITLE_UNTOK']"/></xsl:when><xsl:otherwise><xsl:apply-templates select="field[@name='dc.title'][last()]"/></xsl:otherwise></xsl:choose>",
	    "uri":"%APIHOST%/video/<xsl:apply-templates select="field[@name='PID']"/>"
            }<xsl:if test="position()!=last()">,</xsl:if>
        </xsl:for-each>
         ]
    </xsl:template>

<xsl:template name="escape-quote">
 <xsl:param name="string"/>
<xsl:variable name="quote">"</xsl:variable>
<xsl:choose>
 <xsl:when test='contains($string, $quote)'><xsl:value-of select="substring-before($string,$quote)"/><xsl:text>\"</xsl:text><xsl:call-template name="escape-quote"><xsl:with-param name="string" select="substring-after($string, $quote)" /></xsl:call-template></xsl:when>
 <xsl:otherwise><xsl:value-of select="$string"/></xsl:otherwise>
</xsl:choose>
</xsl:template>

    <xsl:template match="field">
	<xsl:call-template name="escape-quote">
	<xsl:with-param name="string"><xsl:value-of select="normalize-space(.)"/></xsl:with-param>
	</xsl:call-template>
    </xsl:template>

    <xsl:template match="span">
	<xsl:value-of select="."/><xsl:text> </xsl:text>
    </xsl:template>
</xsl:stylesheet>
