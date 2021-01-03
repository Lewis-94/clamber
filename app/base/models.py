# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""
import requests
from werkzeug.utils import secure_filename

from app import login_manager
import datetime
import threading
import os
from app import cache
from app.base.constants import grade_system_choices, grade_options
from app.base.util import allowed_file, allowed_image_filesize
from hashlib import md5
import tempfile
from flask import request, jsonify, abort
from firebase_admin import firestore, storage
import config

class FirestoreDocCrud:
    def __init__(self, collection, uid, map_func=None):
        self.collection = collection
        self.uid = uid
        self.doc_ref = collection.document(uid)
        self.map_function = map_func
        self.listeners = []

    def __del__(self):
        print (f"deleting listeners for {self.uid}")
        self.detach_doc_listeners()

    def detach_doc_listeners(self):
        for listener in self.listeners:
            listener.detach()

    def attach_doc_listener(self, snapshot_handler):
        assert (callable(snapshot_handler))
        doc_watch = self.doc_ref.on_snapshot(snapshot_handler)
        self.listeners.append(doc_watch)
        return doc_watch

    def _ensure_doc(self):
        print (f"reading {self.uid}")
        return self.doc_ref.get()

    def create_item(self, data):
        print(f"creating {self.uid}")
        self.doc_ref.set(data)
        return {'id': self.uid}

    def read_doc(self):
        doc = self._ensure_doc()
        if self.map_function:
            return self.map_function(uid=doc.id, **doc.to_dict())
        else:
            return doc

    def update_doc(self, data):
        print (f"updating {self.uid}")
        if not self.doc_ref.get().exists:
            return {'success': False}
        self.doc_ref.update(data)
        return {'success': True}

    # TODO this is dangerous as nested documents might not be deleted. options for recursive?
    def delete_doc(self):
        print (f"deleting {self.uid}")
        if self.doc_ref.get().exists:
            self.doc_ref.delete()
            return {'success': True}
        return {'success': True}


class FirestoreCollectionCrud:
    # Create an Event for notifying main thread.
    callback_done = threading.Event()

    def __init__(self, databasename, map_func=None):
        self.db = firestore.client().collection(databasename)
        self.map_function = map_func
        self._watched_queries = []

    def query_snapshot(self, where_tuples, snapshot_handler):

        assert (callable(snapshot_handler))
        col_ref = self.db
        for where_tuple in where_tuples:
            assert len(where_tuple) == 3
            col_ref = col_ref.where(*where_tuple)

        query_watch = col_ref.on_snapshot(snapshot_handler)
        self._watched_queries.append(query_watch)
        return query_watch

    def _ensure_item(self, item_id):
        print (f"reading {item_id}")
        return self.db.document(item_id).get()

    def create_item(self, data, item_id=None):
        print (f"creating {item_id}")
        if item_id is None or item_id == "auto":
            item = self.db.add(data)
            return {'id': item[1].get().id}
        else:
            item = self.db.document(item_id)
            item.set(data)
            return {'id': item.id}

    def read_item(self, item_id):
        doc = self._ensure_item(item_id)
        if self.map_function:
            return self.map_function(uid=doc.id, **doc.to_dict())
        else:
            return doc

    def update_item(self, item_id, data):
        doc = self._ensure_item(item_id)
        if not doc.exists:
            return {'success': False}
        print (f"updating {item_id}")
        self.db.document(item_id).update(data)
        return {'success': True}

    # TODO this is dangerous as nested documents might not be deleted. options for recursive?
    def delete_item(self, item_id):
        doc = self._ensure_item(item_id)
        if doc.exists:
            print(f"deleting {item_id}")
            self.db.document(item_id).delete()
            return {'success': True}

        return {'success': True}

    def get_all(self):
        all_docs = self.db.stream()
        for doc in all_docs:
            if self.map_function:
                yield self.map_function(doc.id, **doc.to_dict())
            else:
                yield doc

    

users_db = FirestoreCollectionCrud('users')
centres_db = FirestoreCollectionCrud('centres')
climbtags_db = FirestoreCollectionCrud('climbtags')
bucket = storage.bucket("clamber-7fb70.appspot.com")

all_tags = [{"uid": climb_tag.id, **climb_tag.to_dict()} for climb_tag in climbtags_db.get_all()]
tag_options = [(climb_tag['uid'], climb_tag['tag']) for climb_tag in all_tags]

class FireStoreUser:
    # Create an Event for notifying main thread.
    callback_done = threading.Event()

    def __init__(self, collection, uid, additional_defaults, **kwargs):

        self.doc_crud = FirestoreDocCrud(collection, uid)

        default_dict = {"email": "", "is_authenticated": False, "is_active": False, "is_anonymous": True, "name": ""}
        start_dict = {**default_dict, **additional_defaults}

        user_data = self.doc_crud.read_doc()
        if user_data.exists:
            user_dict = user_data.to_dict()
            if user_dict.get("is_anonymous", True):
                kwargs["is_anonymous"] = False

            if len(kwargs.keys()) > 0:
                return_dict = self.doc_crud.update_doc(kwargs)
                if not return_dict['success']:
                    raise Exception
            user_dict = {**user_dict, **kwargs}

        else:  # create new anonymous user
            user_dict = {**start_dict, **kwargs}
            self.doc_crud.create_item(user_dict)

        self.data = user_dict
        self.uid = uid
        self.is_authenticated = self.data["is_authenticated"]
        self.is_active = self.data["is_active"]
        self.is_anonymous = self.data["is_anonymous"]
        #self.doc_crud.attach_doc_listener(self.on_snapshot)

    def get_id(self):
        try:
            return self.uid
        except AttributeError:
            return None

    def update_user(self, data):
        self.doc_crud.update_doc(data)
        self.data = {**self.data, **data}

    def refresh_user(self):
        data = self.doc_crud.read_doc()
        self.data = {**self.data, **data}
        self.is_authenticated = self.data["is_authenticated"]
        self.is_active = self.data["is_active"]
        self.is_anonymous = self.data["is_anonymous"]

    def on_snapshot(self, doc_snapshot, changes, readtime):
        assert len(doc_snapshot) == 1
        for change in changes:
            if change.type.name == 'ADDED':
                print(f'added user: {change.document.id}')
            elif change.type.name == 'MODIFIED':
                print(f'modified user: {change.document.id}')
            elif change.type.name == 'REMOVED':
                print(f'removed user: {change.document.id}')
            elif change.type.name == 'CHANGED':
                print(f'changed user: {change.document.id}')

        for doc in doc_snapshot:
            data = doc.to_dict()
            self.data = {**self.data, **data}
            self.is_authenticated = self.data["is_authenticated"]
            self.is_active = self.data["is_active"]
            self.is_anonymous = self.data["is_anonymous"]
        self.callback_done.set()

class Route(object):
    def __init__(self, uid=None, name="", difficulty=-1, date_added=datetime.datetime.now(), tags=[],
                 floorplan_x=0, floorplan_y=0, **kwargs):
        self.uid = uid
        self.name = name
        self.difficulty = difficulty
        self.date_added = date_added
        self.tags = tags
        self.floorplan_x = floorplan_x
        self.floorplan_y = floorplan_y
        self._nondefault_params = kwargs.keys()

        for key in kwargs:
            setattr(self, key, kwargs[key])

    @property
    def tags_str(self):
        return ", ".join(self.tags)

    def grade(self, grade_type="font"):

        key = [k1 for k1, k2 in grade_system_choices if k1 == grade_type]
        return grade_options[key[0]][self.difficulty]


    def format_date(self, date_str=None):
        if date_str:
            try:
                assert isinstance(date_str,str)
                return self.date_added.strftime(date_str)
            except AssertionError:
                return self.date_added.strftime("%d/%m/%Y")
        else:
            return self.date_added.strftime("%d/%m/%Y")

    def to_dict(self):
        default_dict = {"name": self.name, "difficulty": self.difficulty, "date_added": self.date_added,
                        "tags": self.tags, "floorplan_x": self.floorplan_x, "floorplan_y": self.floorplan_y}
        non_default_dict = {key: getattr(self, key) for key in self._nondefault_params}
        return {**default_dict, **non_default_dict}

    def to_serialisable(self):
        default_dict = {"name": self.name, "difficulty": self.difficulty, "date_added": self.format_date(),
                        "tags": self.tags, "floorplan_x": self.floorplan_x, "floorplan_y": self.floorplan_y}
        # Note it is assumed all non default attributes are already serialisable
        non_default_dict = {key: getattr(self, key) for key in self._nondefault_params}
        return {**default_dict, **non_default_dict}

    def __repr__(self):
        return


class User(FireStoreUser):

    def __init__(self, uid, account_type=None, **firestore_data):
        print("user object initialised")

        additional_defaults = {}
        if account_type == "user":
            additional_defaults = {"account_type": account_type, "numberOfSessions": 0, "numberOfClimbs": 0,
                                   "bestClimb": 0, "bestFlash": 0}
        elif account_type =="centre":
            additional_defaults = {"account_type": account_type}
            self.subcollections = {"routes": FirestoreCollectionCrud(u"users/" + uid + "/routes", Route)}

        super(User, self).__init__(users_db.db, uid, additional_defaults, **firestore_data)

    @property
    def avatar(self):
        if self.data.get('profile_picture', None) is None:
            digest = md5(self.data['email'].lower().encode('utf-8')).hexdigest()
            return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
                digest, 128)  # 128 is pixel ize
        else:
            firestore_file_name = self.data['profile_picture']
            blob = bucket.blob(firestore_file_name)
            return blob.generate_signed_url(datetime.timedelta(seconds=300), method='GET')

    @property
    def floorplan(self):
        if self.data.get('floor_plan', None) is None:
            return None
        else:
            firestore_file_name = self.data['floor_plan']
            blob = bucket.blob(firestore_file_name)
            signed_url = blob.generate_signed_url(datetime.timedelta(seconds=300), method='GET')
            floorplan_request = requests.get(signed_url)
            svg_bytes = floorplan_request.content

            return svg_bytes

    def upload_image(self, image, image_cat):

        assert image_cat in ["profile_picture", "floor_plan"]
        if not allowed_file(image.filename, image_cat):
            return ("danger", "Error!", "file must have one of the following extensions: {}".format(", ".join(
                config.Config.ALLOWED_EXTENSIONS[image_cat])))
        if not allowed_image_filesize(request.cookies[image_cat + "_filesize"]):
            return ("danger", "Error!", "file size has exceeded maximum limit of 1Mb")

        filename = secure_filename(image.filename)

        bucket = storage.bucket("clamber-7fb70.appspot.com")
        firestore_file_name = f"{self.uid}_{image_cat}.{filename.rsplit('.')[-1].upper()}"
        blob = bucket.blob(firestore_file_name)
        temp = tempfile.NamedTemporaryFile(delete=False)
        image.save(temp.name)

        t = threading.Thread(target=lambda blob, r: blob.upload_from_file(r), name=firestore_file_name, args=(blob, temp))
        t.start()
        t.join()

        self.update_user({image_cat: firestore_file_name})
        # Clean-up temp images
        temp.close()
        os.remove(temp.name)

        return ("success", "Success!", "Profile picture has been successfully uploaded")



def make_user(uid, account_type, **kwargs):
    User(uid, account_type, **kwargs)
    if account_type == "centre":
        centres_db.create_item({"email": kwargs['email'], "name": kwargs['name']}, kwargs['name'])


@login_manager.user_loader
def load_user(user_id, **kwargs):   # TODO this function could be improved to query user database less
        print(f"flask login call {user_id}")
        return User(user_id, **kwargs)


