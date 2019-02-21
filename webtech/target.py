#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import re
from io import open

# From now on, hacky hack to work on Burp Jython2.7 without external modules
BURP = False
try:
    from requests import get
    from requests.utils import dict_from_cookiejar
    from requests.structures import CaseInsensitiveDict

    # Disable warning about Insecure SSL
    from requests.packages.urllib3 import disable_warnings
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    disable_warnings(InsecureRequestWarning)
except ImportError as e:
    BURP = True
    pass

from . import encoder
from .utils import FileNotFoundException, Format, Tech, caseinsensitive_in, dict_from_caseinsensitivedict
from .parser import WTParser

# Hacky hack to hack ack. Support python2 and python3 without depending on six
if sys.version_info[0] > 2:
    unicode = str


def parse_regex_string(string):
    """
    Parse header string according to wappalizer DB format

    strings follow the below format:
    <string>[\\;version:\\\d][\\;confidence:\d]

    "string" is a mandatory regex string followed by 0 or more parameters (key:value), can be empty
    parameters are divided by a \\; sequence (a backslash followed by a semicolon)

    examples of parameters are:
    "version": indicate wich regex group store the version information
    "confidence": indicate a rate of confidence
    """
    parts = string.split("\;")
    if len(parts) == 1:
        return parts[0], None
    else:
        extra = {}
        for p in parts[1:]:
            extra[p.split(":")[0]] = p.split(":")[1]
        return parts[0], extra


class Target():
    """
    This class represents a single Target (from scraping a page, from a response file, from a replayed request or from a JSON request-response exchange)

    The only self attribues MUST be self.data that contains the fetched data and self.report that contains the results from various checks.response

    Every function MUST do only 1 action since we are need to parallelize this and all the data must be source-independent
    """
    def __init__(self):
        # self.data contains the data fetched from the request
        # this object SHOULD be append-only and immutable after the scraping/whitelist process
        self.data = {
            'url': None,
            'html': None,
            'headers': None,
            'cookies': None,
            'meta': None,
            'script': None
        }

        # self.report contains the information about the technologies detected
        self.report = {
            'tech': set(),
            'headers': [],
        }

    def scrape_url(self, url, headers={}, cookies={}):
        """
        Scrape the target URL and collects all the data that will be filtered afterwards
        """
        if BURP:
            # Burp flag is set when requests is not installed.
            # When using Burp we shouldn't end up in this function so we are in a Python CLI env without requests
            raise ImportError("Missing Requests module")
        # By default we don't verify SSL certificates, we are only performing some useless GETs
        response = get(url, headers=headers, cookies=cookies, verify=False, allow_redirects=True)
        # print("status: {}".format(response.status_code))

        # TODO: switch-case for various response.status_code

        self.data['url'] = url
        self.data['html'] = response.text
        self.data['headers'] = dict_from_caseinsensitivedict(response.headers)
        self.data['cookies'] = dict_from_cookiejar(response.cookies)
        self.parse_html_page()

    def parse_http_file(self, url):
        """
        Receives an HTTP request/response file and redirect to request/response parsing
        """
        try:
            path = url.replace('file://', '')
            data = open(path, encoding="ISO-8859-1").read()
        except FileNotFoundException:
            # it's an URL without schema, not a file
            return self.scrape_url("https://" + path, headers={'User-Agent': self.USER_AGENT}, cookies={})

        # e.g. HTTP/1.1 200 OK -> that's a response!
        # does not check HTTP/1 since it might be HTTP/2 :)
        if data.startswith("HTTP/"):
            # BUG: path is not a reliable information. url matching will always fail
            self.data['url'] = path
            return self.parse_http_response(data)
        return self.parse_http_request(data)

    def parse_http_response(self, response):
        """
        Parse an HTTP response file and collects all the data that will be filtered afterwards

        TODO: find a better way to do this :(
        """
        response = response.replace('\r', '')
        headers_raw = response.split('\n\n', 1)[0]
        parsed_headers = {}

        self.data['cookies'] = {}
        for header in headers_raw.split('\n'):
            # might be first row: HTTP/1.1 200
            if ":" not in header:
                continue
            if "set-cookie:" in header.lower():
                # 'Set-Cookie: dr=gonzo; path=/trmon' -> "dr"
                cookie_name = header.split('=', 1)[0].split(':')[1].strip()
                # 'Set-Cookie: dr=gonzo; domain=jolla.it;' -> "gonzo"
                cookie_value = header.split('=', 1)[1].split(';', 1)[0].strip()
                # BUG: if there are cookies for different domains with the same name
                # they are going to be overwritten (last occurrence will last)...
                # ¯\_(ツ)_/¯
                self.data['cookies'][cookie_name] = cookie_value
            else:
                header_name = header.split(':', 1)[0].strip()
                header_value = header.split(':', 1)[1].strip()
                parsed_headers[header_name.lower()] = (header_value, header_name)
        self.data['headers'] = parsed_headers

        self.data['html'] = response.split('\n\n', 1)[1]

        self.parse_html_page()

    def parse_http_request(self, request, replay=True):
        """
        Parse an HTTP request file and collects all the headers

        TODO: find a better way to do this :(
        TODO: should we support POST request?
        """
        # GET / HTTP/1.1 -> /
        request = request.replace('\r', '')
        replay_uri = request.split('\n', 1)[0].split(" ")[1]
        replay_headers = {}
        replay_cookies = {}

        headers_raw = request.split('\n\n', 1)[0]
        for header in headers_raw.split('\n'):
            # might be first row: HTTP/1.1 200
            if ":" not in header:
                continue
            if "cookie" not in header.lower():
                if "host" in header.lower():
                    host = header.split(':', 1)[1].strip()
                else:
                    header_name = header.split(':', 1)[0].strip()
                    header_value = header.split(':', 1)[1].strip()
                    replay_headers[header_name] = header_value
            else:
                # 'Cookie: dr=gonzo; mamm=ta; trmo=n'
                cookie_value = header.split(":", 1)[1]
                cookies = cookie_value.split(';')
                for cookie in cookies:
                    cookie_name = cookie.split("=", 1)[0].strip()
                    cookie_value = cookie.split("=", 1)[1].strip()
                    # BUG: if there are cookies for different domains with the same name
                    # they are going to be overwritten (last occurrence will last)...
                    # ¯\_(ツ)_/¯
                    replay_cookies[cookie_name] = cookie_value

        # BUG: we don't know for sure if it's through HTTP or HTTPS
        replay_url = "https://" + host + replay_uri
        if replay:
            self.scrape_url(replay_url, headers=replay_headers, cookies=replay_cookies)
        else:
            # The URL is the only usefull information when parsing a request without replaying it
            self.data['url'] = replay_url

    def parse_html_page(self):
        """
        Parse HTML content to get meta tag and script-src
        """
        p = WTParser()
        p.feed(self.data['html'])
        self.data['meta'] = p.meta
        self.data['script'] = p.scripts
        p.close()

    def whitelist_data(self, common_headers):
        """
        Whitelist collected data to report the important/uncommon data BEFORE matching with the database

        This function is useful for CMS/technologies that are not in the database
        """
        for key, value in self.data['headers'].items():
            if key not in common_headers:
                # In value[1] it's stored the original header name
                self.report['headers'].append({"name": value[1], "value": value[0]})

    def check_html(self, tech, html):
        """
        Check if request html contains some database matches
        """
        if isinstance(html, str) or isinstance(html, unicode):
            html = [html]

        for source in html:
            matches = re.search(source, self.data['html'], re.IGNORECASE)
            if matches is not None:
                matched_tech = Tech(name=tech, version=None)
                self.report['tech'].add(matched_tech)
                # this tech is matched, GOTO next
                return

    def check_headers(self, tech, headers):
        """
        Check if request headers match some database headers
        """
        if not isinstance(headers, dict):
            raise ValueError('Invalid headers data in database: {}'.format(headers))

        # For every tech header check if there is a match in our target
        for header in headers:
            content = self.data['headers'].get(header.lower())
            if content is None:
                # Tech not found
                return
            else:
                # Get the real content
                content = content[0]
            # Parse the matching regex
            attr, extra = parse_regex_string(headers[header])
            matches = re.search(attr, content, re.IGNORECASE)
            # Attr is empty for a "generic" tech header
            if attr is '' or matches is not None:
                matched_tech = Tech(name=tech, version=None)
                # The version extra data is present
                if extra and extra['version']:
                    if matches.group(1):
                        matched_tech = matched_tech._replace(version=matches.group(1))
                self.report['tech'].add(matched_tech)
                # remove ALL the tech headers from the Custom Header list
                # first make a list of tech headers
                tech_headers = list(map(str, headers.keys()))
                # then filter them in target headers case insensitively
                self.report['headers'] = list(filter(lambda h: not caseinsensitive_in(str(h['name']), tech_headers), self.report['headers']))
                # this tech is matched, GOTO next
                return

    def check_meta(self, tech, meta):
        """
        Check if request meta from page's HTML contains some database matches
        """
        for m in meta:
            content = self.data['meta'].get(m)
            # filter not-available meta
            if content is None:
                continue
            attr, extra = parse_regex_string(meta[m])
            matches = re.search(attr, content, re.IGNORECASE)
            # Attr is empty for a "generic" tech meta
            if attr is '' or matches is not None:
                matched_tech = Tech(name=tech, version=None)
                # The version extra data is present
                if extra and extra['version']:
                    if matches.group(1):
                        matched_tech = matched_tech._replace(version=matches.group(1))
                self.report['tech'].add(matched_tech)
                # this tech is matched, GOTO next
                return

    def check_script(self, tech, script):
        """
        Check if request script src from page's HTML contains some database matches
        """
        # FIX repair to some database inconsistencies
        if isinstance(script, str) or isinstance(script, unicode):
            script = [script]

        for source in script:
            attr, extra = parse_regex_string(source)
            for src in self.data['script']:
                matches = re.search(attr, src, re.IGNORECASE)
                # Attr is empty for a "generic" tech meta
                if attr is '' or matches is not None:
                    matched_tech = Tech(name=tech, version=None)
                    # The version extra data is present
                    if extra and extra['version']:
                        if matches.group(1):
                            matched_tech = matched_tech._replace(version=matches.group(1))
                    self.report['tech'].add(matched_tech)
                    # this tech is matched, GOTO next
                    return

    def check_cookies(self, tech, cookies):
        """
        Check if request cookies match some database cookies
        """
        for cookie in cookies:
            # cookies in db are regexes so we must test them all
            cookie = cookie.replace("*","") # FIX for "Fe26.2**" hapi.js cookie in the database
            for biscuit in self.data['cookies'].keys():
                matches = re.search(cookie, biscuit, re.IGNORECASE)
                if matches is not None:
                    if cookies[cookie] != '':
                        # Let's check the cookie content
                        content = self.data['cookies'][biscuit]
                        matches = re.search(cookies[cookie], content, re.IGNORECASE)
                        if matches is None:
                            # No match, exit
                            return
                    matched_tech = Tech(name=tech, version=None)
                    self.report['tech'].add(matched_tech)
                    # this tech is matched, GOTO next
                    return

    def check_url(self, tech, url):
        """
        Check if request url match some database url rules
        """
        if isinstance(url, str) or isinstance(url, unicode):
            url = [url]

        for source in url:
            matches = re.search(source, self.data['url'], re.IGNORECASE)
            if matches is not None:
                matched_tech = Tech(name=tech, version=None)
                self.report['tech'].add(matched_tech)
                # this tech is matched, GOTO next
                return

    def generate_report(self, output_format):
        """
        Generate a report
        """
        if output_format == Format['grep']:
            techs = ""
            for tech in self.report['tech']:
                if len(techs): techs += "//"
                techs += "{}".format(tech.name + "/" + 'unknown' if tech.version is None else tech.version)

            headers = ""
            for header in self.report['headers']:
                if len(headers): headers += "//"
                headers += "{}".format(header["name"] + ":" + header["value"])

            return "Url>{}\tTechs>{}\tHeaders>{}".format(self.data['url'], techs, headers)
        elif output_format == Format['json']:
            # TODO: find a better way to run the encoder and return a JSON Object instead of encoding and decoding again
            return json.loads(json.dumps(self.report, cls=encoder.Encoder))
        else:
            retval = ""
            retval += "Target URL: {}\n".format(self.data['url'])
            if self.report['tech']:
                retval += "Detected technologies:\n"
                for tech in self.report['tech']:
                    retval += "\t- {} {}\n".format(tech.name, '' if tech.version is None else tech.version)
            if self.report['headers']:
                retval += "Detected the following interesting custom headers:\n"
                for header in self.report['headers']:
                    retval += "\t- {}: {}\n".format(header["name"], header["value"])
            return retval
