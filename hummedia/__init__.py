from flask import Flask
app = Flask(__name__)

import hummedia.api, hummedia.auth
