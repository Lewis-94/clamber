# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, SelectMultipleField, FileField, TextAreaField, \
    Field
from wtforms.validators import InputRequired, Email, DataRequired, NumberRange, AnyOf, ValidationError
from wtforms.fields.html5 import DateField
from wtforms.widgets import TextInput
from app.base.models import all_tags, tag_options
from datetime import datetime, time
from app.base.models import  climbtags_db
# -- CONSTS -------
from app.base.constants import all_grade_choices, grade_system_choices, grade_options
from flask_login import current_user

class ClassedWidgetMixin(object):
  """Adds the field's name as a class.

  (when subclassed with any WTForms Field type).
  """

  def __init__(self, *args, **kwargs):
    print('got to classed widget')
    super(ClassedWidgetMixin, self).__init__(*args, **kwargs)

  def __call__(self, field, **kwargs):
    print('got to call')
    c = kwargs.pop('class', '') or kwargs.pop('class_', '')
    # kwargs['class'] = u'%s %s' % (field.name, c)
    kwargs['class'] = u'%s %s' % ('testclass', c)
    return super(ClassedWidgetMixin, self).__call__(field, **kwargs)

class NotValues(object):
    field_flags = ('accepts_bbcode',)

    def __init__(self, not_allowed, message=None):
        self.not_allowed = not_allowed
        if not message:
            message = u'Field must not be any of the following values: {0}.'.format(", ".join(not_allowed))
        self.message = message

    def __call__(self, form, field):
        l = field.data and len(field.data) or 0
        if l in self.not_allowed:
            raise ValidationError(self.message)


class CoordinateField(StringField):

    def __init__(self, label='', validators=None, **kwargs):
        super(CoordinateField, self).__init__(label, validators, **kwargs)

    def _value(self):
        if self.data:
            return '({0}, {1})'.format(*self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            x, y = valuelist[0].replace("(", "").replace(")", "").split(',')
            self.data = list(map(int, (x, y)))
        else:
            self.data = []

    @staticmethod
    def map_tags(valuelist):
        tags = list(map(int, valuelist))
        tag_uids = [climb_tag['uid'] for i, climb_tag in enumerate(all_tags) if i in tags]
        return tag_uids

class DateAndTimeField(DateField):
    def __init__(self, label='', validators=None, **kwargs):
        super(DateAndTimeField, self).__init__(label, validators, **kwargs)

    def _value(self):
        if self.data is not None:
            return self.data.date()
        else:
            return []

    def process_formdata(self, valuelist):
        if len(valuelist) != 0:
            self.data = datetime.combine(datetime.strptime(valuelist[0], '%Y-%m-%d'), time())
        else:
            self.data = None


notvalues = NotValues


class LoginForm(FlaskForm):
    username = StringField ('Username', id='username_login', validators=[DataRequired()])
    password = PasswordField('Password', id='pwd_login', validators=[DataRequired()])


class CreateAccountForm(FlaskForm):
    username = StringField('Username', id='username_create' , validators=[DataRequired()])
    email = StringField('Email', id='email_create', validators=[DataRequired(), Email()])
    password = PasswordField('Password', id='pwd_create', validators=[DataRequired()])


class AddRouteForm(FlaskForm):
    name = StringField('Route Name', id="name_add")
    grade_system = SelectField("Grade System", id="grade_system_select", validators=[], choices=grade_system_choices)
    grade = SelectField("Grade", id="grade_select",
                        validators=[DataRequired("please select a value for Grade")],
                        choices=all_grade_choices)
    date_added = DateAndTimeField("Date Added", id="date_added_add", validators=[DataRequired()])
    tags_list = SelectMultipleField("Tags List", id="tags_list_add", validators=[], choices=tag_options)
    coordinates = CoordinateField('Route Coordinate', id="coordinates", validators=[DataRequired()])
    submit = SubmitField("Create Route")

    def __init__(self, *args, **kwargs):
        super(AddRouteForm, self).__init__(*args, **kwargs)
        if "data" in kwargs:
            self.coordinates.data = (kwargs['data']['x'], kwargs['data']['y'])
            self.date_added.data = kwargs['data']['date_added']
            self.tags_list.data = kwargs['data']['tags_list']

class EditProfileForm(FlaskForm):
    centre_name = StringField('Centre Name', id="centre_name_add")
    address = StringField('Address', id="address_add")
    city = StringField("City", id="city_add")
    country = StringField("Country", id="country_add")
    postcode = StringField("Postcode", id="postcode_add")
    about_the_centre = TextAreaField("About the Centre", id="aboute_the_centre_add")
    grade_system = SelectField("Grade System", id="grade_system_select", validators=[DataRequired()], choices=grade_system_choices)
    profile_picture = FileField("Upload Profile", id="profile_picture")
    floor_plan = FileField("Upload Profile", id="floor_plan")
    submit = SubmitField('Update Profile')