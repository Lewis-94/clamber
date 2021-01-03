# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask import Flask, url_for, request
import requests
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
import firebase_admin
from importlib import import_module
from logging import basicConfig, DEBUG, getLogger, StreamHandler
from os import path
import os
import pyrebase
from flask_caching import Cache
from config import config_dict
from firebase_admin import credentials


def register_extensions(app):
    login_manager.init_app(app)


def register_blueprints(app):
    for module_name in ('base', 'home'):
        module = import_module('app.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)


def configure_database(app):

    @app.before_first_request
    def initialize_database():
        pass

    @app.teardown_request
    def shutdown_session(exception=None):
        pass

def configure_logs(app):
    # soft logging
    try:
        basicConfig(filename='error.log', level=DEBUG)
        logger = getLogger()
        logger.addHandler(StreamHandler())
    except:
        pass

def apply_themes(app):
    """
    Add support for themes.

    If DEFAULT_THEME is set then all calls to
      url_for('static', filename='')
      will modfify the url to include the theme name

    The theme parameter can be set directly in url_for as well:
      ex. url_for('static', filename='', theme='')

    If the file cannot be found in the /static/<theme>/ location then
      the url will not be modified and the file is expected to be
      in the default /static/ location
    """
    @app.context_processor
    def override_url_for():
        return dict(url_for=_generate_url_for_theme)

    def _generate_url_for_theme(endpoint, **values):
        if endpoint.endswith('static'):
            themename = values.get('theme', None) or \
                app.config.get('DEFAULT_THEME', None)
            if themename:
                theme_file = "{}/{}".format(themename, values.get('filename', ''))
                if path.isfile(path.join(app.static_folder, theme_file)):
                    values['filename'] = theme_file
        return url_for(endpoint, **values)



def build_request(blueprint_url, request_type="get", blueprint_params={}, payload_dict={}, data=None):
    print(request.url_root)
    url = request.url_root + url_for(blueprint_url, **blueprint_params)
    if data is None:
        data = {}

    if request_type == "post":
        res = requests.post(url, params=payload_dict, json=data).json()
    elif request_type == "put":
        res = requests.put(url, params=payload_dict, json=data).json()
    elif request_type == "delete":
        res = requests.delete(url, params=payload_dict).json()
    elif request_type == "get":
        res = requests.get(url, params=payload_dict).json()

    return res


firebaseConfig = {"apiKey": "AIzaSyCR3gZ30J_dNxcmchR2DOf5k9jxESrwYbI",
                  "authDomain": "clamber-7fb70.firebaseapp.com",
                  "databaseURL": "https://clamber-7fb70.firebaseio.com",
                  "projectId": "clamber-7fb70",
                  "storageBucket": "clamber-7fb70.appspot.com",
                  "messagingSenderId": "933891183634",
                  "appId": "1:933891183634:web:4749b939c0758ea182b4cb",
                  "serviceAccount": "clamber-7fb70-firebase-adminsdk-r3amf-5e67e7d348.json"}

login_manager = LoginManager()
firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

if not firebase_admin._apps:
    cred = credentials.Certificate('clamber-7fb70-firebase-adminsdk-r3amf-5e67e7d348.json')
    default_app = firebase_admin.initialize_app(cred)



get_config_mode = os.environ.get('APPSEED_CONFIG_MODE', 'Debug')

try:
    config_mode = config_dict[get_config_mode.capitalize()]
except KeyError:
    exit('Error: Invalid APPSEED_CONFIG_MODE environment variable entry.')

app = Flask(__name__, static_folder='base/static')
app.config.from_object(config_mode)
app.jinja_env.globals.update(build_request=build_request)
cache = Cache(app)
register_extensions(app)
register_blueprints(app)
configure_database(app)
configure_logs(app)
apply_themes(app)
