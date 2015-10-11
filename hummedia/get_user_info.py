# MOVE ME TO FLASK/hummedia/hummedia TO RUN

from flask import request, Response, jsonify, current_app, session
from flask_oauth import OAuth
from datetime import datetime, timedelta, date
from functools import update_wrapper
from mongokit import cursor
from bson import ObjectId
from models import connection
from config import APIHOST, YT_SERVICE, BYU_WS_ID, BYU_SHARED_SECRET
from urllib2 import Request, urlopen, URLError
import json, byu_ws_sdk, requests, re, os, mimetypes
import time


def getCurrentSem():
    today=datetime.now()
    sem="1"
    if today.month in [5,6]:
        sem="4"
    elif today.month in [7,8]:
        sem="4"
    elif today.month in [9,10,11,12]:
        sem="5"
    return str(today.year)+sem

def get_enrollments(username, userid):
    url="https://ws.byu.edu/rest/v1.0/academic/registration/studentschedule/"+userid+"/"+getCurrentSem()
    headerVal = byu_ws_sdk.get_http_authorization_header(BYU_WS_ID, BYU_SHARED_SECRET, byu_ws_sdk.KEY_TYPE_API,byu_ws_sdk.ENCODING_NONCE,actor=username,url=url,httpMethod=byu_ws_sdk.HTTP_METHOD_GET,actorInHash=True)
    res=requests.get(url, headers={'Authorization': headerVal})
    return res 
