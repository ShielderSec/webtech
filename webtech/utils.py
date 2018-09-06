#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import namedtuple
from enum import Enum

try:
    FileNotFoundException = FileNotFoundError
except NameError:
    FileNotFoundException = IOError


class Format(Enum):
    # sadly auto() is only supported since Python 3.6
    text = 0
    grep = 1
    json = 2


Tech = namedtuple('Tech', ['name', 'version'])


def caseinsensitive_in(element, elist):
    """
    Given a list and an element, return true if the element is present in the list
    in a case-insensitive flavor
    """
    return element.lower() in map(str.lower, elist)
