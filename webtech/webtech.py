#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import json
import random
try:
    from urlparse import urlparse
except ImportError:  # For Python 3
    from urllib.parse import urlparse

from . import database
from .utils import Format, FileNotFoundException
from .target import Target


def get_random_user_agent():
    """
    Get a random user agent from a file
    """

    ua_file = os.path.join(os.path.realpath(os.path.dirname(__file__)), "ua.txt")
    try:
        with open(ua_file) as f:
            agents = f.readlines()
            return random.choice(agents).strip()
    except FileNotFoundException as e:
        print(e)
        print('Please: Reinstall webtech correctly or provide a valid User-Agent list')
        exit(-1)


class WebTech():
    """
    Main class. The orchestrator that decides what to do.

    This class is the bridge between the tech's database and the Targets' data
    """
    VERSION = 1.2.1
    USER_AGENT = "webtech/{}".format(VERSION)
    COMMON_HEADERS = ['Accept-Ranges', 'Access-Control-Allow-Methods', 'Access-Control-Allow-Origin', 'Age', 'Cache-Control', 'Connection',
                      'Content-Encoding', 'Content-Language', 'Content-Length', 'Content-Security-Policy', 'Content-Type', 'Date', 'ETag', 'Expect-CT', 'Expires',
                      'Feature-Policy', 'Keep-Alive', 'Last-Modified', 'Link', 'Location', 'P3P', 'Pragma', 'Referrer-Policy', 'Set-Cookie',
                      'Strict-Transport-Security', 'Transfer-Encoding', 'Vary', 'X-Accel-Buffering', 'X-Cache', 'X-Cache-Hits', 'X-Content-Security-Policy',
                      'X-Content-Type-Options', 'X-Frame-Options', 'X-Timer', 'X-WebKit-CSP', 'X-XSS-Protection']
    COMMON_HEADERS = [ch.lower() for ch in COMMON_HEADERS]

    # 'cats' tech categories
    # 'implies' website is using also this tech
    # 'excludes' exclude this tech
    # 'website' website for this tech
    # 'icon' icon for this tech (useless)

    # 'headers' check this patter in headers
    # 'html' check this regex in html
    # 'meta' check this patter in meta
    # 'js' check this expression in javascript context
    # 'cookies' check this patter in cookies
    # 'script' check this pattern in scripts src
    # 'url' check this patter in url

    def __init__(self, options=None):
        database.update_database()

        with open(database.WAPPALYZER_DATABASE_FILE) as f:
            self.db = json.load(f)
        with open(database.DATABASE_FILE) as f:
            self.db = database.merge_databases(self.db, json.load(f))

        # Output text only
        self.output_format = Format['text']

        if options is None:
            return

        if options.db_file is not None:
            try:
                with open(options.db_file) as f:
                    self.db = database.merge_databases(self.db, json.load(f))
            except FileNotFoundException as e:
                print(e)
                exit(-1)
            except ValueError as e:
                print(e)
                exit(-1)

        if options.urls is not None:
            self.urls = options.urls
        else:
            self.urls = []
        if options.urls_file is not None:
            try:
                with open(options.urls_file) as f:
                    self.urls = f.readlines()
            except FileNotFoundException as e:
                print(e)
                exit(-1)

        if options.user_agent is not None:
            self.USER_AGENT = options.user_agent
        if options.use_random_user_agent:
            self.USER_AGENT = get_random_user_agent()

        if options.output_grep:
            # Greppable output
            self.output_format = Format['grep']
        elif options.output_json:
            # JSON output
            self.output_format = Format['json']

    def start(self):
        """
        Start the engine, fetch an URL and report the findings
        """
        self.output = {}
        for url in self.urls:
            temp_output = self.start_from_url(url, output_format=self.output_format)
            if self.output_format == Format['text']:
                print(temp_output)
            else:
                self.output[url] = temp_output

        if self.output_format == Format['json']:
            print(json.dumps(self.output, sort_keys=True, indent=4))
        else:
            for url in self.output:
                print(self.output[url])

    def start_from_url(self, url, output_format=None, headers={}):
        """
        Start webtech on a single URL/target

        Returns the report for that specific target
        """
        target = Target()

        parsed_url = urlparse(url)
        if "http" in parsed_url.scheme:
            # Scrape the URL by making a request
            h = {'User-Agent': self.USER_AGENT}
            h.update(headers)
            target.scrape_url(url, headers=h, cookies={})
        elif "file" in parsed_url.scheme:
            # Load the file and read it
            target.parse_http_file(url)
        else:
            raise ValueError("Invalid scheme {} for URL {}. Only 'http', 'https' and 'file' are supported".format(parsed_url.scheme, url))

        return self.perform(target, output_format)

    def start_from_json(self, exchange, output_format=None):
        """
        Start webtech on a single target from a HTTP request-response exchange as JSON serialized string

        This function is the entry point for the Burp extension
        """
        return self.start_from_exchange(json.loads(exchange))

    def start_from_exchange(self, exchange, output_format=None):
        """
        Start webtech on a single target from a HTTP request-response exchange as Object
        """
        target = Target()

        request = exchange['request']
        response = exchange['response']

        target.parse_http_response(response)
        target.parse_http_request(request, replay=False)

        return self.perform(target, output_format)

    def perform(self, target, output_format):
        """
        Performs all the checks on the current target received as argument

        This function can be executed on multiple threads since "it doesn't access on shared data"
        """
        if output_format is None:
            output_format = Format['json']
        else:
            output_format = Format.get(output_format, 0)

        target.whitelist_data(self.COMMON_HEADERS)

        # Cycle through all the db technologies and do all the checks
        # It's more efficent cycling all technologies and match against the target once for tech
        # instead of cycling each target feature against every technology
        for tech in self.db["apps"]:
            t = self.db["apps"][tech]
            headers = t.get("headers")
            html = t.get("html")
            meta = t.get("meta")
            cookies = t.get("cookies")
            script = t.get("script")
            url = t.get("url")
            if headers:
                target.check_headers(tech, headers)
            if html:
                target.check_html(tech, html)
            if meta:
                target.check_meta(tech, meta)
            if cookies:
                target.check_cookies(tech, cookies)
            if script:
                target.check_script(tech, script)
            if url:
                target.check_url(tech, url)

        return target.generate_report(output_format)
