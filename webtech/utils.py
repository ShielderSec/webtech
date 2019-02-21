#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import namedtuple

try:
    FileNotFoundException = FileNotFoundError
except NameError:
    FileNotFoundException = IOError

Format = {
    'text': 0,
    'grep': 1,
    'json': 2
}

Tech = namedtuple('Tech', ['name', 'version'])


def caseinsensitive_in(element, elist):
    """
    Given a list and an element, return true if the element is present in the list
    in a case-insensitive flavor
    """
    return element.lower() in map(str.lower, elist)

def dict_from_caseinsensitivedict(cidict):
    # This is pretty bad, but in Python2 we don't have CaseInsensitiveDict and with Burp we cannot use requests's implementation
    d = {}
    for key, value in cidict.items():
        d[key.lower()] = (value, key)
    return d