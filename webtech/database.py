#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path
import time
try:
    from urllib.request import urlopen
except ImportError as e:
    from urllib2 import urlopen


INSTALLATION_DIR = os.path.realpath(os.path.dirname(__file__))
DATABASE_FILE = os.path.join(INSTALLATION_DIR, "webtech.json")
WAPPALYZER_DATABASE_FILE = os.path.join(INSTALLATION_DIR, "apps.json")
WAPPALYZER_DATABASE_URL = "https://raw.githubusercontent.com/AliasIO/Wappalyzer/master/src/apps.json"
WEBTECH_DATABASE_URL = "https://raw.githubusercontent.com/ShielderSec/webtech/blob/master/webtech/webtech.json" 
DAYS = 60 * 60 * 24


def download_database_file(url, target_file):
    """
    Download the database file from the WAPPPALIZER repository
    """
    print("Updating database...")
    response = urlopen(url)
    with open(target_file, 'wb') as out_file:
        out_file.write(response.read())
    print("Database updated successfully!")


def update_database(args=None):
    """
    Update the database if it's not present or too old
    """
    # TODO: option to force the DB update

    now = int(time.time())
    
    if not os.path.isfile(WAPPALYZER_DATABASE_FILE):
        print("Database file not present.")
        download_database_file(WAPPALYZER_DATABASE_URL)
        # set timestamp in filename
    else:
        last_update = int(os.path.getmtime(WAPPALYZER_DATABASE_FILE))
        if last_update < now - 30 * DAYS:
            print("Database file is older than 30 days.")
            os.remove(WAPPALYZER_DATABASE_FILE)
            download_database_file(WAPPALYZER_DATABASE_URL, WAPPALYZER_DATABASE_FILE)

    last_update = int(os.path.getmtime(DATABASE_FILE))
    if last_update < now - 30 * DAYS:
        print("WebTech Database file is older than 30 days.")
        os.remove(DATABASE_FILE)
        download_database_file(WEBTECH_DATABASE_URL, DATABASE_FILE)


def merge_databases(db1, db2):
    """
    This helper function merge elements from two databases without overrding its elements
    This function is not generic and *follow the Wappalyzer db scheme*
    """
    # Wappalyzer DB format must have an apps object
    db1 = db1['apps']
    db2 = db2['apps']

    merged_db = db1

    for prop in db2:
        if merged_db.get(prop) is None:
            # if the element appears only in db2, add it to db1
            # TODO: Validate type of db2[prop]
            merged_db[prop] = db2[prop]
        else:
            # both db contains the same property, merge its children
            element = merged_db[prop]
            for key, value in db2[prop].items():
                if merged_db[prop].get(key) is None:
                    # db1's prop doesn't have this key, add it freely
                    if type(value) in [str, list, dict]:
                        element[key] = value
                    else:
                        raise ValueError('Wrong type in database: only "dict", "list" or "str" are permitted - element of type {}'.format(type(value).__name__))
                else:
                    # both db's prop have the same key, pretty disappointing :(
                    element[key] = merge_elements(merged_db[prop][key], value)
            merged_db[prop] = element

    return {'apps': merged_db}


def merge_elements(el1, el2):
    """
    Helper function to merge 2 element of different types
    Note: el2 has priority over el1 and can override it

    The possible cases are:
    dict & dict -> merge keys and values
    list & list -> merge arrays and remove duplicates
    list & str  -> add str to array and remove duplicates
    str & str   -> make a list and remove duplicates

    all other cases will raise a ValueError exception
    """
    if isinstance(el1, dict):
        if isinstance(el2, dict):
            # merge keys and value
            el1.update(el2)
            return el1
        else:
            raise ValueError('Incompatible types when merging databases: element1 of type {}, element2 of type {}'.format(type(el1).__name__, type(el2).__name__))
    elif isinstance(el1, list):
        if isinstance(el2, list):
            # merge arrays and remove duplicates
            el1.extend(el2)
            return list(set(el1))
        elif isinstance(el2, str):
            # add string to array and remove duplicates
            el1.append(el2)
            return list(set(el1))
        else:
            raise ValueError('Incompatible types when merging databases: element1 of type {}, element2 of type {}'.format(type(el1).__name__, type(el2).__name__))
    elif isinstance(el1, str):
        if isinstance(el2, str):
            # make a list and remove duplicates
            return list(set([el1, el2]))
        else:
            return merge_elements(el2, el1)
    raise ValueError('Wrong type in database: only "dict", "list" or "str" are permitted - element of type {}'.format(type(el1).__name__))
