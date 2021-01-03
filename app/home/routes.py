# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from app.home import blueprint
from flask import request, render_template, redirect, url_for, jsonify, session
from flask_login import login_required, current_user
import requests
from app import login_manager
from jinja2 import TemplateNotFound
from app.base.models import FirestoreCollectionCrud, Route
import firebase_admin
from app.base.models import all_tags
from app.base.constants import grade_options
from app.base.forms import AddRouteForm, EditProfileForm
from app.base.jinja_classes import StatsCard
import json
from datetime import datetime, time
import json


@blueprint.route('/index')
@login_required
def index():
    
    if not current_user.is_authenticated:
       return redirect(url_for('base_blueprint.login'))

    routes = FirestoreCollectionCrud('centres/' + session['centre_name'] + '/routes', Route).get_all()
    routes = [route for route in routes]

    number_of_routes = len(routes)
    number_of_sessions = "Not yet implemented"
    number_of_people = "Not yet implemented"

    stat_cards = [StatsCard(number_of_routes, big_icon="timeline", title="Number of Current Routes",
                        card_type="primary", footer_type="primary", footer_icon="timeline", footer_href="",
                        footer_text="nothing"),
                  StatsCard(number_of_sessions, big_icon="timeline", title="Number of sessions last week",
                            card_type="primary", footer_type="primary", footer_icon="timeline", footer_href="",
                            footer_text="nothing"),
                  StatsCard(number_of_people, big_icon="timeline", title="Number of people who attended last week",
                        card_type="primary", footer_type="primary", footer_icon="timeline", footer_href="",
                        footer_text="nothing")]

    return render_template('index.html', stat_cards=stat_cards)

@blueprint.route('/<template>')
@login_required
def route_template(template):

    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    try:

        return render_template(template + '.html')

    except TemplateNotFound:
        return render_template('page-404.html'), 404
    
    except:
        return render_template('page-500.html'), 500


@blueprint.route('/<user_type>/<template>', methods=["GET", "POST"])
@login_required
def route_centre_template(user_type, template):
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))


    if "upload_profile" in request.form:
        current_user.upload_profile(request.files["image"])
    print(current_user.floorplan)
    if current_user.data['account_type'] == 'centre':

        if not 'centre_name' in session:
            session['centre_name'] =current_user.data['name']

        routes = FirestoreCollectionCrud('centres/' + session['centre_name'] + '/routes', Route).get_all()
        routes = [route for route in routes]
        routes_json = json.dumps([route.to_serialisable() for route in routes])
        return render_template(template + '.html', routes=routes, routes_json=routes_json)

        try:
            a=1
        except TemplateNotFound:
            return render_template('page-404.html'), 404
        except:
            return render_template('page-500.html'), 500

    else:
        return render_template('page-403.html'), 403

@blueprint.route('/centre/centre-profile', methods=["GET", "POST"])
@login_required
def centre_profile():
    notifications = []
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))
    else:
        form = EditProfileForm()
        if request.method == "GET":
            form.about_the_centre.data = current_user.data.get('about', "")
            form.centre_name.data = current_user.data.get('name', "")
            form.address.data = current_user.data.get('address', "")
            form.country.data = current_user.data.get('country', "")
            form.city.data = current_user.data.get('city', "")
            form.postcode.data = current_user.data.get('postcode', "")
            form.grade_system.data = current_user.data.get('default_grade_system', "")

            return render_template('centre-profile.html', form=form, notifications=notifications)
        else:
            print(f"grade system data: {form.grade_system.data}")
            if form.validate_on_submit():

                data = {"about": form.about_the_centre.data, "name": form.centre_name.data,
                        "default_grade_system": form.grade_system.data, "address": form.address.data,
                        "country": form.country.data, "city": form.city.data, "postcode": form.postcode.data}
                for pic in ["profile_picture", "floor_plan"]:
                    file = request.files[pic]
                    if file.filename != '':
                        print(file.filename)
                        notifications.append(current_user.upload_image(file, pic))

                current_user.update_user(data)
            notifications += [("danger", "Error!", error) for error in form.errors]
            return render_template('centre-profile.html', form=form, notifications=notifications)


@blueprint.route('/_get_grades_list/')
def _get_grades_list():
    grade_system = request.args.get('grade_system', type=str)
    grades_list = [(str(i), grade) for i, grade in enumerate(grade_options[grade_system])]
    return jsonify(grades_list)


@blueprint.route('/get_floorplan/', methods=["GET"])
def _get_floor_plan():
    floorplan = current_user.floorplan
    return floorplan


@blueprint.route('/delete_route_<uid>', methods=["GET", "POST"])
@login_required
def delete_route(uid):
    return jsonify(FirestoreCollectionCrud('centres/' + session['centre_name'] + '/routes', Route).delete_item(uid))


@blueprint.route('/edit_route_<uid>', methods=["GET", "POST"])
@login_required
def edit_route(uid):

    routes_crud = FirestoreCollectionCrud('centres/' + session['centre_name'] + '/routes', Route)
    route = routes_crud.read_item(uid)

    route_form_data = {'uid': route.uid, 'name': route.name, 'grade': str(route.difficulty), 'date_added': route.date_added,
                       'tags_list': route.tags, 'x': route.floorplan_x, 'y': route.floorplan_y, 'grade_system': '0'}

    edit_route_form = AddRouteForm(request.form, data=route_form_data, obj=route)
    if edit_route_form.validate_on_submit():
        new_route = create_route_from_form(request.form).to_dict()
        routes_crud.update_item(uid, new_route)

        return redirect(url_for('home_blueprint.route_centre_template', user_type=current_user.data['account_type'],
                                template="manage-routes"))
    else:
        print(edit_route_form.errors)

    return render_template('create_route.html', form=edit_route_form, existing_route=route_form_data)


@blueprint.route("/centre/create_route", methods=["GET", "POST"])
@login_required
def create_route():
    create_route_form = AddRouteForm(request.form)
    print(create_route_form.grade.data)
    if create_route_form.validate_on_submit():
        route = create_route_from_form(request.form)
        FirestoreCollectionCrud('centres/' + session['centre_name'] + '/routes', Route).create_item(route.to_dict(), item_id="auto")

        return redirect(url_for('home_blueprint.route_centre_template', user_type=current_user.data['account_type'], template="manage-routes"))

    else:
        print(create_route_form.errors)

    return render_template('create_route.html', form=create_route_form)


def create_route_from_form2(form):
    tag_ids = form.tags_list.data
    difficulty_str = form.grade.data
    date_added = form.date_added.data
    name = form.name.data
    floorplan_x, floorplan_y = form.coordinates.data
    route = Route(name=name, difficulty=int(difficulty_str), tags=tag_ids, date_added=date_added,
                  floorplan_x=floorplan_x, floorplan_y=floorplan_y)

    return route


def create_route_from_form(form):

    tag_ids = form.getlist('tags_list')
    grade_str = request.form.getlist('grade')[0]
    date_added = datetime.combine(datetime.strptime(form.getlist('date_added')[0], '%Y-%m-%d'), time())
    name = form.getlist('name')[0]
    floorplan_x, floorplan_y = map(int, form.getlist('coordinates')[0].replace("(", "").replace(")", "").split(','))
    route = Route(name=name, difficulty=int(grade_str) - 1, tags=tag_ids, date_added=date_added,
                  floorplan_x=floorplan_x, floorplan_y=floorplan_y)

    return route