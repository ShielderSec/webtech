from optparse import OptionParser
import requests
from bs4 import BeautifulSoup
import json
import re

# TODO: change to a local import
import database

# Disable warning about Insecure SSL
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


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
    COMMON_HEADERS = ['Vary', 'Connection', 'Content-Type', 'Link', 'Content-Length', 'Date', 'Content-Encoding', 'Set-Cookie', 'Cookie']

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

        self.data = {}
        self.data['url'] = url

        self.scrape_url()

        self.whitelist_data()

        self.check_headers()

    def scrape_url(self):
        """
        Scrape the target URL and collects all the data that will be filtered afterwards
        """
        # By default we don't verify SSL certificates, we are only performing some useless GETs
        response = requests.get(self.data['url'], headers=self.header, verify=False)
        print("status: {}".format(response.status_code))

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
            if header not in self.COMMON_HEADERS:
                print("Interesting header: {}: {}".format(header, self.data['headers'][header]))

        # Cookie and Set-Cookie need a special treatment

    def check_headers(self):
        """
        Check if request headers match some database headers
        """
        for tech in self.db["apps"]:
            headers = self.db["apps"][tech].get("headers")
            if not headers:
                continue
            for header in headers:
                content = self.data['headers'].get(header)
                if not content:
                    continue
                attr, extra = parse_header_string(headers[header])
                matches = re.search(attr, content, re.IGNORECASE)
                if matches is not None:
                    print("Matched tech: {}".format(matches.group(0)))
                    if extra and extra['version']:
                        if matches.group(1):
                            print("Matched tech version: {}".format(matches.group(1)))


wt = WebTech()
wt.start("https://www.plesk.com/")
wt.start("https://twentyfourteendemo.wordpress.com/")
