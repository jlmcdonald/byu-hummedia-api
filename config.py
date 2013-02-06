from flask import Response
import os

host="https://zelda.byu.edu"
apihost=host+"/api/devel"

script_path = os.path.dirname(__file__)
style_path = script_path+"/styles/"

UNSUPPORTED_FORMAT=Response("That format is not currently supported.",status=400,mimetype="text/plain")
NOT_FOUND=Response("That object could not be found.",status=404,mimetype="text/plain")
BAD_REQUEST=Response("The request was malformed in some way.",status=400,mimetype="text/plain")