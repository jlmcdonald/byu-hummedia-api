import urllib, urlparse, json
import config
from flask import request, session, redirect, url_for, jsonify
from models import connection
from urllib2 import Request, urlopen, URLError
from providers import *
from helpers import crossdomain, plain_resp, get_enrollments
from interfaces import ItsdangerousSessionInterface
from os import environ

from hummedia import app
#app.session_interface = ItsdangerousSessionInterface()
app.secret_key=config.SECRET_KEY
app.session_cookie_name=config.COOKIE_NAME
app.config['SESSION_COOKIE_DOMAIN']=config.COOKIE_DOMAIN
app.config['APPLICATION_ROOT']=config.APPLICATION_ROOT
app.config['SESSION_COOKIE_PATH']=app.config['APPLICATION_ROOT']
provider_lookup={"google":GoogleOAuth2,"cas":CasAuth}
oAuthService = provider_lookup["google"]("google") # done this way so eventually we can have multiple providers ... for now, it's hard coded
cas = provider_lookup["cas"]()
provider = oAuthService.get_remote_app()

@provider.tokengetter
def get_access_token():
    return session.get('access_token')
    
def get_user():
    return session.get('username')

def get_userid():
    return session.get('userid')
    
def get_role():
    return session.get('role')
    
def is_superuser():
    return session.get('superuser')
    
def get_profile():
    atts={}
    for att in ['username','userid','role','superuser','fullname','preferredLanguage','ta']:
        atts[att]=session.get(att)
    if (atts['username'] is None or atts['username']=="") and session.get('oauth'):
	atts['oauth']=session.get('oauth')['provider']
    return atts
    
def get_redirect_url():
    return session.get("redirect") if session.get("redirect") else url_for("profile")
  
def set_session_vars(user):
    for att in ('username','userid','role','superuser','fullname','preferredLanguage','ta'):
        if att in user:
            session[att]=user[att]

def make_token_header():
    access_token = get_access_token()
    if access_token is None:
        return False
    else:
        return 'OAuth '+access_token[0]

def verify_oauth_access(th):
    headers = {'Authorization': th}
    req = Request(oAuthService.token_verify_url,None, headers)
    try:
        res = urlopen(req)
    except URLError, e:
        if e.code == 401:
            session.pop('access_token', None)
            return False
    return json.loads(res.read())

def get_user_from_oauth(provider,atts,access_token=None):
    q = {"oauth.%s.id" % (provider):atts['id']}
    user=connection.User.find_one(q)
    if user is None:
        session["oauth"]={"provider":provider,"id":atts['id'],"access_token":access_token,"email":atts['email']}
        user={"username":"","role":"","superuser":False,"fullname":"","preferredLanguage":"en", "ta":False}
    return {"username":user['username'],"role":user['role'],"superuser":user["superuser"],"fullname":user["fullname"],"preferredLanguage":user["preferredLanguage"], "ta":user.get("ta",False)}
    
def get_user_from_cas(netid=None,atts=None):
    if not netid:
        netid=get_user()
    q = {"username":netid.lower()}
    user=connection.User.find_one(q)
    if user is None:
        user=connection.User()
        faculty_positions=["activeFulltimeInstructor","activeParttimeInstructor"]
        user["username"]=netid.lower()
        user["firstname"]=unicode(atts["preferredFirstName"])
        user["lastname"]=unicode(atts["preferredSurname"])
        user["email"]=atts["emailAddress"]
        user["fullname"]="%s %s" % (user["firstname"],user["lastname"])
        user["userid"]=str(atts["personId"])
        for ap in faculty_positions:
            if atts[ap]=="true":
                user["role"]="faculty"
    oauth=session.get('oauth',[])
    if "provider" in oauth:
        if user['oauth'][oauth['provider']]['id'] is None:
            user["oauth"][oauth['provider']]={"id":oauth['id'],"email": oauth['email'],"access_token":oauth['access_token']}
    user.save()
    set_session_vars(user)
    return {"user":get_user()}

@crossdomain(origin=config.CROSS_DOMAIN_HOSTS,headers=['Origin','x-requested-with','accept','Content-Type', 'Authorization'],credentials=True)
def auth_redirect(provider="cas",authUser=None,proxyUser=None):
    if provider=="google":
        th=make_token_header()
        if th:
            verification=verify_oauth_access(th)
            if verification:
                user=get_user_from_oauth(provider,verification,get_access_token())
                if user['username']!="":
                    set_session_vars(user)
                elif get_user():
                    get_user_from_cas()
                return redirect(get_redirect_url())
        return redirect(url_for("apiLogin",providerService=provider))
    elif provider in ["authUser","proxy"] and authUser is not None:
        user=connection.User.find_one({"username":authUser})
        if provider=="authUser":
            set_session_vars(user)
        elif user["superuser"] and proxyUser is not None:
            set_session_vars(connection.User.find_one({"username":proxyUser}))
    return redirect(get_redirect_url())

@app.route('/account/enrollments',methods=['GET'])
def enrollmentTest():
    return plain_resp(get_enrollments())

@app.route('/account/login',methods=['GET'])
@app.route('/account/login/<providerService>',methods=['GET','OPTIONS'])
@app.route('/account/login/<providerService>/<proxyUser>',methods=['GET','OPTIONS'])
@crossdomain(origin=config.CROSS_DOMAIN_HOSTS,headers=['Origin','x-requested-with','accept','Content-Type', 'Authorization'],credentials=True)
def apiLogin(providerService="cas",proxyUser=None):
    session["redirect"]=request.args.get("r",session.get("redirect"))
    if get_user() and request.args.get("connect") is None:
        return auth_redirect()
    if providerService == "google":
        if get_access_token():
            return auth_redirect(provider=providerService)
        else:
            return provider.authorize(callback=config.APIHOST+config.GOOGLE_REDIRECT_URI)
    elif providerService in ["authUser","proxy"]:
        return auth_redirect(providerService,request.headers.get("Authorization"),proxyUser)
    else:
        return redirect(cas.login_url(config.APIHOST+config.REDIRECT_URI))
        
@app.route('/account/logout',methods=['GET','OPTIONS'])
@crossdomain(origin=config.CROSS_DOMAIN_HOSTS,headers=['Origin','x-requested-with','accept','Content-Type'],credentials=True)
def apiLogout():
    if "username" in session:
        session.pop('username')
    r=request.args.get("r",get_redirect_url())
    session.clear()
    return plain_resp("logout successful")

@app.route(config.REDIRECT_URI)
@provider.authorized_handler
def authorized(resp):
    provider=request.args.get("auth","cas")
    if get_user() and provider=="cas":
        return auth_redirect()
    if provider=="google":
        if not get_access_token():
            access_token = resp['access_token']
            session['access_token'] = [access_token, '']
    else:
        if "ticket" in request.args:
            user,atts=cas.verify_ticket(request.args.get('ticket'),config.APIHOST+config.REDIRECT_URI)
            if user:
                get_user_from_cas(user,atts)
    return auth_redirect(provider=provider)

@app.route('/account/profile',methods=['GET','OPTIONS'])
@crossdomain(origin=config.CROSS_DOMAIN_HOSTS,headers=['Origin','x-requested-with','accept','Content-Type'],credentials=True)
def profile():
    return jsonify(get_profile())
