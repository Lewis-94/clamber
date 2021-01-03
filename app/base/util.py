# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""
 
import hashlib, binascii, os
import ast
import requests
from requests.exceptions import HTTPError
# Inspiration -> https://www.vitoshacademy.com/hashing-passwords-in-python/
from flask import abort

import config


def ensure_keys(params, keys):
    return_dict = {}
    for key in keys:
        try:
            return_dict[key] = params[key]
        except KeyError:
            abort(404)
    return return_dict


def hash_pass( password ):
    """Hash a password for storing."""
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), 
                                salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash) # return bytes


def verify_pass(provided_password, stored_password):
    """Verify a stored password against one provided by user"""
    stored_password = stored_password.decode('ascii')
    salt = stored_password[:64]
    stored_password = stored_password[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha512', 
                                  provided_password.encode('utf-8'), 
                                  salt.encode('ascii'), 
                                  100000)
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash == stored_password


class PrettyHTTPError(HTTPError):

    def __init__(self, http_error):
        self.e = http_error
        self.messages = {"INVALID_EMAIL": "Error: Invalid email provided",
                         "EMAIL_EXISTS": "Error: Account for this email address already exists",
                         "INVALID_PASSWORD": "Error: Password for this account is invalid",
                         "EMAIL_NOT_FOUND": "Error: This email does not have an account"}

    def __str__(self):
        error_dict = ast.literal_eval(self.e.strerror)
        return self.messages.get(error_dict["error"]["message"],
                                 "Error: Unknown error {}".format(error_dict["error"]["message"]))


def allowed_file(filename, image_cat):
    return '.' in filename and filename.rsplit('.')[-1].upper() in config.Config.ALLOWED_EXTENSIONS[image_cat]


def allowed_image_filesize(filesize):

    if int(filesize) <= config.Config.MAX_IMAGE_FILESIZE:
        return True
    else:
        return False