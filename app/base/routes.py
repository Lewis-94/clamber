# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask import jsonify, render_template, redirect, request, url_for, abort, session
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user
)
from werkzeug.urls import url_parse

from app import auth
from app.base import blueprint
from app.base.forms import LoginForm, CreateAccountForm
from app.base.models import User
from app.base.util import verify_pass, PrettyHTTPError, ensure_keys
from app.base.models import users_db, make_user, load_user
from requests.exceptions import HTTPError

@blueprint.route('/')
def route_default():
    return redirect(url_for('base_blueprint.login'))

@blueprint.route('/error-<error>')
def route_errors(error):
    return render_template('errors/{}.html'.format(error))

## Login & Registration


@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)
    if 'login' in request.form:

        # read form data
        email = request.form['username']
        password = request.form['password']

        try:

            firebase_user = auth.sign_in_with_email_and_password(email, password)
            uid = firebase_user['localId']
            account_info = auth.get_account_info(firebase_user['idToken'])
            user = load_user(uid, is_authenticated=account_info['users'][0]['emailVerified'], is_active=True,
                             is_anonymous=False)

            custom_token = auth.create_custom_token(uid,  {"centre_account": True if
                                                    user.data['account_type'] == "centre" else False})

            firebase_user = auth.sign_in_with_custom_token(custom_token)

            user.data['token'] = custom_token
            print(f"logging in user {user.get_id()}")
            login_user(user)

        except HTTPError as e:
            return render_template('login/login.html', msg=PrettyHTTPError(e), form=login_form)

    if current_user:
        if current_user.is_authenticated:
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('home_blueprint.index')
            return redirect(next_page)
        elif not current_user.is_anonymous:
            return render_template('login/login.html', verify=True, form=login_form)

    return render_template('login/login.html', form=login_form)


@blueprint.route('/verify_account', methods=['POST'])
def verify_account():
    try:
        auth.send_email_verification(auth.current_user['idToken'])
        return jsonify({"msg": "Verification Email sent"})
    except HTTPError as e:
        return jsonify({"msg": PrettyHTTPError(e)})


@blueprint.route('/create_account/<user_type>', methods=['GET', 'POST'])
def create_account(user_type):
    create_account_form = CreateAccountForm(request.form)
    if 'register' in request.form:

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        try:
            firebase_user = auth.create_user_with_email_and_password(email, password)
            uid = firebase_user['localId']
            # create flask user
            make_user(uid, user_type, email=firebase_user['email'], name=username, token=firebase_user['idToken'])

            msg = 'verification email sent to email {0} \n User created please <a href="/login">login</a>'.format(email)
            auth.send_email_verification(firebase_user['idToken'])
            return render_template('login/register.html', msg=msg, form=create_account_form)

        except HTTPError as e:
            return render_template('login/register.html', msg=PrettyHTTPError(e), form=create_account_form)
    else:
        return render_template( 'login/register.html', form=create_account_form)

@blueprint.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('base_blueprint.login'))

@blueprint.route('/shutdown')
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

## Errors

#@login_manager.unauthorized_handler
#def unauthorized_handler():
#    return render_template('errors/403.html'), 403

@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('errors/403.html'), 403

@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500



@blueprint.route('/users', methods=['POST'])
def add_user():
    user_id = ensure_keys(request.args, "id")
    db_data = {}
    data = request.json
    try:
        db_data = users_db.create_item(data, user_id=user_id["id"])
    except KeyError:
        abort(404)
    return jsonify(db_data)


@blueprint.route('/users')
def read_user():
    user_id = ensure_keys(request.args, "id")
    db_data = {}
    try:
        db_data = users_db.read_item(user_id["id"])
    except KeyError:
        abort(404)
    return jsonify(db_data)


@blueprint.route('/users', methods=['PUT'])
def update_user():
    user_id = ensure_keys(request.args, "id")
    db_data = {}
    req = request.json
    try:
        db_data = users_db.update_item(user_id["id"], req)
    except KeyError:
        abort(404)
    return jsonify(db_data)


@blueprint.route('/users', methods=['DELETE'])
def delete_user():
    user_id = ensure_keys(request.args, "id")
    db_data = {}
    try:
        db_data = users_db.delete_item(user_id["id"])
    except KeyError:
        abort(404)
    return jsonify(db_data)
