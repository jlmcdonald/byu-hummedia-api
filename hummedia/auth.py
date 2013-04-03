from flask import request, session, redirect, url_for, jsonify
from models import connection as conn
from urllib2 import Request, urlopen, URLError
from providers import *
import json, config

from hummedia import app
app.secret_key=config.SECRET_KEY

provider_lookup={"google":GoogleOAuth2,"cas":CasAuth}
oAuthService = provider_lookup["google"]("google") # done this way so eventually we can have multiple providers ... for now, it's hard coded
cas = provider_lookup["cas"]()
provider = oAuthService.get_remote_app()

@provider.tokengetter
def get_access_token():
    return session.get('access_token')

def make_token_header():
    access_token = session.get('access_token')
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
    user=conn.User.find_one(q)
    if user is None:
        session["oauth"]={"provider":provider,"id":atts['id'],"access_token":access_token,"email":atts['email']}
        user={"username":""}
    return {"username":user['username']}
    
def get_user_from_cas(netid=None,atts=None):
    if not netid:
        netid=session.get('user')
    q = {"username":netid}
    user=conn.User.find_one(q)
    if user is None:
        user=conn.User()
        faculty_positions=["activeFulltimeEmployee","activeFulltimeInstructor","activeParttimeEmployee","activeParttimeInstructor"]
        user["username"]=netid
        user["firstname"]=unicode(atts["preferredFirstName"])
        user["lastname"]=unicode(atts["preferredSurname"])
        user["email"]=atts["emailAddress"]
        for ap in faculty_positions:
            if atts[ap]=="true":
                user["role"]="faculty"
    if session.get('oauth') and user['oauth'][oauth['provider']]['id']=="":
        oauth=session.get('oauth')
        user["oauth"][oauth['provider']]={"id":oauth['id'],"email": oauth['email'],"access_token":oauth['access_token']}
    user.save()
    session['user']=user['username']
    return {"user":session.get('user')}

@app.route('/account/login',methods=['GET'])
@app.route('/account/login/<providerService>',methods=['GET'])
def apiLogin(providerService="cas"):
    if "user" in session and request.args.get("connect") is None:
        return redirect(url_for('profile'))
    if providerService == "google":
        if get_access_token(): 
            return redirect(url_for('profile',provider=providerService))
        else:
            return provider.authorize(callback=config.APIHOST+config.GOOGLE_REDIRECT_URI)
    else:
        return redirect(cas.login_url(config.APIHOST+config.REDIRECT_URI))

@app.route(config.REDIRECT_URI)
@provider.authorized_handler
def authorized(resp):
    provider=request.args.get("auth","cas")
    if "user" in session and provider=="cas":
        return redirect(url_for('profile',provider=provider))
    if provider=="google":
        if not get_access_token():
            access_token = resp['access_token']
            session['access_token'] = [access_token, '']
    else:
        if "ticket" in request.args:
            user,atts=cas.verify_ticket(request.args.get('ticket'),config.APIHOST+config.REDIRECT_URI)
            if user:
                get_user_from_cas(user,atts)
    return redirect(url_for('profile',provider=provider))

@app.route('/account/profile',methods=['GET'])
@app.route('/account/profile/<provider>',methods=['GET'])
def profile(provider="cas"):
    if provider=="google":
        th=make_token_header()
        if th:
            verification=verify_oauth_access(th)
            if verification:
                user=get_user_from_oauth(provider,verification,get_access_token())
                if user['username']!="":
                    session['user']=user['username']
                elif session.get('user'):
                    get_user_from_cas()
                return jsonify({"user":session.get('user')})       
        return redirect(url_for("apiLogin",providerService=provider))
    return jsonify({"user":session.get('user')})
        
        