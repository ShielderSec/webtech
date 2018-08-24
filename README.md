# webtech
Identify technologies used on websites

## Installation

Simply run the following command in your terminal

```
python setup.py install --user
```

It's important to install webtech in a folder where user can write because it will download the signature database in that folder.

## Usage

Scan a website

```
$ webtech -u https://example.com/

Target URL: https://example.com
...

```

Full usage

```
$ webtech -h

Usage: webtech [options]

Options:
  -h, --help            show this help message and exit
  -u URLS, --urls=URLS  url(s) to scan
  --ul=URLS_FILE, --urls-file=URLS_FILE
                        url(s) list file to scan
  --rf=REQUEST_FILES, --request-files=REQUEST_FILES
                        HTTP request file to replay
  --ua=USER_AGENT, --user-agent=USER_AGENT
                        use this user agent
  --rua, --random-user-agent
                        use a random user agent
  --db=DB_FILE, --database-file=DB_FILE
                        custom database file
  --oj, --json          output json-encoded report
  --og, --grep          output grepable report

```


## Resources for database matching

HTTP Headers information - http://netinfo.link/http/headers.html  
Cookie names - https://webcookies.org/top-cookie-names  

## TODO

- review all the code TODOs
- review and fix the database download
- write a decent README.md  :D
