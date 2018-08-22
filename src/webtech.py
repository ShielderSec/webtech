from optparse import OptionParser
import requests
from bs4 import BeautifulSoup
import json
import re
from collections import namedtuple

# TODO: change to a local import
import database

# Disable warning about Insecure SSL
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

Tech = namedtuple('Tech', ['name', 'version'])


def parse_header_string(string):
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


class WebTech():
    VERSION = 0.1
    USER_AGENT = "webtech/{}".format(VERSION)
    COMMON_HEADERS = ['Vary', 'Connection', 'Content-Type', 'Link', 'Content-Length', 'Date', 'Content-Encoding',
                      'Set-Cookie', 'Last-Modified', 'Transfer-Encoding', 'Cache-Control', 'Strict-Transport-Security',
                      'Expect-CT', 'X-Content-Type-Options', 'Feature-Policy', 'Referrer-Policy', 'X-Frame-Options',
                      'X-XSS-Protection']
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

    def __init__(self):
        with open(database.DATABASE_FILE) as f:
            self.db = json.load(f)

    def start(self, url):
        """
        Start the engine, fetch an URL and report the findings
        """
        self.header = {'User-Agent': self.USER_AGENT}

        # self.data contains the data fetched from the request
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

        self.scrape_url(url)
        self.whitelist_data()
        self.check_headers()
        self.print_report()

    def scrape_url(self, url):
        """
        Scrape the target URL and collects all the data that will be filtered afterwards
        """
        # By default we don't verify SSL certificates, we are only performing some useless GETs
        response = requests.get(url, headers=self.header, verify=False)
        print("status: {}".format(response.status_code))

        # TODO: switch-case for various response.status_code

        self.data['url'] = url
        self.data['html'] = response.text
        self.data['headers'] = response.headers
        self.data['cookies'] = response.cookies

        #print(data)
        #soup = BeautifulSoup(response.text, 'html.parser')
        #print(soup)

        self.data['meta'] = ''  # html meta tags
        self.data['script'] = ''  # html script-src links

    def whitelist_data(self):
        """
        Whitelist collected data to report the important/uncommon data BEFORE matching with the database

        This function is useful for CMS/technologies that are not in the database
        """
        for header in self.data['headers']:
            # This is pretty stupid and need an alternative approach
            if header.lower() not in self.COMMON_HEADERS:
                self.report['headers'].append(header)

        # Set-Cookie needs a special treatment

    def check_headers(self):
        """
        Check if request headers match some database headers
        """
        # Cycle through all the db entries
        for tech in self.db["apps"]:
            # Get the entry headers
            headers = self.db["apps"][tech].get("headers")
            if not headers:
                continue
            # For every tech header check if there is a match in our target
            for header in headers:
                try:
                    # _store, hacky way to get the original key from a request.structures.CaseInsensitiveDict
                    real_header, content = self.data['headers']._store[header.lower()]
                except KeyError:
                    # tech header not found, go ahead
                    continue
                # Parse the matching regex
                attr, extra = parse_header_string(headers[header])
                matches = re.search(attr, content, re.IGNORECASE)
                # Attr is empty for a "generic" tech header
                if attr is '' or matches is not None:
                    matched_tech = Tech(name=tech, version=None)
                    # Remove the matched header from the Custom Header list
                    try:
                        self.report['headers'].remove(real_header)
                    except ValueError:
                        pass
                    # The version extra data is present
                    if extra and extra['version']:
                        if matches.group(1):
                            matched_tech = matched_tech._replace(version=matches.group(1))
                    self.report['tech'].add(matched_tech)

    def print_report(self):
        print("Target URL: {}".format(self.data['url']))
        print("Detected technologies:")
        for tech in self.report['tech']:
            print("\t- {} {}".format(tech.name, '' if tech.version is None else tech.version))

        if self.report['headers']:
            print("Detected the following interesting custom headers:")
            for header in self.report['headers']:
                print("\t- {}: {}".format(header, self.data['headers'].get(header)))


wt = WebTech()
wt.start("https://www.plesk.com/")
wt.start("https://twentyfourteendemo.wordpress.com/")
