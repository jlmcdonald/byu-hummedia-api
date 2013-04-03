from helpers import OAuthProvider
from urllib import urlencode
from urlparse import urljoin
from lxml import etree
import urllib2, config

class GoogleOAuth2(OAuthProvider):

	def __init__(self,providerService):
		OAuthProvider.__init__(self,providerService)

	client_id=config.GOOGLE_CLIENT_ID
	client_secret=config.GOOGLE_CLIENT_SECRET
	base_url='https://www.google.com/accounts/'
	authorize_url='https://accounts.google.com/o/oauth2/auth'
	token_verify_url='https://www.googleapis.com/oauth2/v1/userinfo'
	request_token_params={'scope': 'https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile','response_type': 'code'}
	access_token_url='https://accounts.google.com/o/oauth2/token'

class CasAuth():
	CAS_NS="{http://www.yale.edu/tp/cas}"
	testresp='''<cas:serviceResponse xmlns:cas='http://www.yale.edu/tp/cas'>
		<cas:authenticationSuccess>
        <cas:user>jlm59</cas:user>
        <cas:attributes>
                <cas:restOfName>Jarom L</cas:restOfName>
                <cas:activeParttimeNonBYUEmployee>false</cas:activeParttimeNonBYUEmployee>
                <cas:activeParttimeInstructor>false</cas:activeParttimeInstructor>
            	<cas:inactiveFulltimeEmployee>false</cas:inactiveFulltimeEmployee>
                <cas:surname>McDonald</cas:surname>
                <cas:activeFulltimeInstructor>true</cas:activeFulltimeInstructor>
                <cas:memberOf>aagt,afins,alumni,agt,ains,netfse,cr03,EMPLOYEE DEPENDENT,ENTERPRISE DIRECTORY,FORMER STD--24 COMPLETED HRS,FULL TIME FACULTY,GRADUATED ALUMNI,LOAccess,OFFICE_OF_DIGITAL_HUMANITIES,QUALIFIED-FOR-LABS,QUALIFIED-FOR-ED2,SWEMP,STUDENT DEPENDENT,vnet</cas:memberOf>
                <cas:preferredFirstName>Jarom</cas:preferredFirstName>
                <cas:sortName>McDonald, Jarom L</cas:sortName>
                <cas:activeFulltimeNonBYUEmployee>false</cas:activeFulltimeNonBYUEmployee>
                <cas:inactiveParttimeNonBYUEmployee>false</cas:inactiveParttimeNonBYUEmployee>
                <cas:organization>false</cas:organization>
                <cas:activeEligibletoRegisterStudent>false</cas:activeEligibletoRegisterStudent>
                <cas:name>Jarom McDonald</cas:name>
                <cas:preferredSurname>McDonald</cas:preferredSurname>
                <cas:personId>353204382</cas:personId>
                <cas:inactiveParttimeInstructor>false</cas:inactiveParttimeInstructor>
                <cas:netId>jlm59</cas:netId>
                <cas:inactiveFulltimeNonBYUEmployee>false</cas:inactiveFulltimeNonBYUEmployee>
                <cas:byuId>035404758</cas:byuId>
                <cas:restricted>false</cas:restricted>
                <cas:emailAddress>jarom_mcdonald@byu.edu</cas:emailAddress>
                <cas:alumni>true</cas:alumni>
                <cas:inactiveParttimeEmployee>false</cas:inactiveParttimeEmployee>
                <cas:inactiveFulltimeInstructor>false</cas:inactiveFulltimeInstructor>
                <cas:activeFulltimeEmployee>false</cas:activeFulltimeEmployee>
                <cas:fullName>Jarom L McDonald</cas:fullName>
                <cas:activeParttimeEmployee>false</cas:activeParttimeEmployee>
        </cas:attributes>   
    	</cas:authenticationSuccess>
		</cas:serviceResponse>'''

	def verify_ticket(self,ticket, service):
		params={"ticket":ticket,"service":service}
		url=(urljoin(config.CAS_SERVER,'/cas/proxyValidate') + '?' + urlencode(params))
		v=urllib2.urlopen(url)
		try:
			user = None
			attributes = {}
			resp=etree.fromstring(v.read())[0]
			if resp.tag==self.CAS_NS+"authenticationSuccess":
				user=resp.findtext(self.CAS_NS+"user")
				atts=resp.find(self.CAS_NS+"attributes")
				for a in atts:
					qn=etree.QName(a)
					attributes[qn.localname]=a.text
			return user,attributes
		finally:
			v.close()

	def login_url(self,service_url):
		return config.CAS_SERVER + "/cas/login?service=" + service_url

    
