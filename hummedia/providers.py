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

    
