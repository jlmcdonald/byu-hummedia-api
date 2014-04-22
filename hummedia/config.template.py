from flask import Response
import os

HOST="https://zelda.byu.edu"
APIHOST=HOST+"/api/devel"
REDIRECT_URI="/account/callback"

CROSS_DOMAIN_HOSTS=['http://hlrdev.byu.edu','https://hlrdev.byu.edu','http://ian.byu.edu','https://ian.byu.edu']

UNSUPPORTED_FORMAT=Response("That format is not currently supported.",status=400,mimetype="text/plain")
NOT_FOUND=Response("That object could not be found.",status=404,mimetype="text/plain")
BAD_REQUEST=Response("The request was malformed in some way.",status=400,mimetype="text/plain")
UNAUTHORIZED=Response("You do not have permission to perform that action.",status=401,mimetype="text/plain")

GOOGLE_CLIENT_ID = 'client.id.goes.here'
GOOGLE_CLIENT_SECRET = 'client_secret_goes_here'
GOOGLE_REDIRECT_URI=REDIRECT_URI+"?auth=google"

CAS_SERVER  = "https://cas.byu.edu"
BYU_WS_ID = "byu_ws_id_goes_here"
BYU_SHARED_SECRET = "byu_shared_secret_goes_here"

SECRET_KEY = 'app_secret_goes_here'
COOKIE_NAME = 'hummedia-session'
COOKIE_DOMAIN = ".byu.edu"
APPLICATION_ROOT = "/"

MONGODB_DB = 'hummedia'
MONGODB_HOST = 'localhost'
MONGODB_PORT = 27017

GOOGLE_API_KEY = "GoogleAPIKeyHere"
YT_SERVICE = "https://www.googleapis.com/youtube/v3/videos?part=snippet&key="+GOOGLE_API_KEY

GEARMAN_SERVERS = ['localhost:4730'] # specify host and port

INGEST_DIRECTORY = "/opt/media/video/migrate/" # where ingestable media are found
MEDIA_DIRECTORY = "/opt/media/video/" # where ingested media should be moved to
POSTERS_DIRECTORY = "/opt/media/posters/"
SUBTITLE_DIRECTORY = "/opt/text/"

# For the auth token module in Apache, for restricting access to videos
# These should match whatever is present in your Apache configuration file
AUTH_TOKEN_SECRET      = "secret string"
AUTH_TOKEN_PREFIX      = "/movies/"
AUTH_TOKEN_IP          = True # limits by IP address. requires module v. 1.0.6+
