#!/usr/bin/env python
from optparse import OptionParser
from webtech import WebTech
import sys

def split_urls(option, opt_str, value, parser):
    setattr(parser.values, option.dest, value.split(','))

def main():
    """
    Main function when running from command line.
    """
    parser = OptionParser()
    parser.add_option(
        "-u", "--urls", dest="urls",
        help="url(s) to scan", type="string", action="callback", callback=split_urls)
    parser.add_option(
        "--ua", "--user-agent", dest="user_agent",
        help="use this user agent")
    parser.add_option(
        "--rua", "--random-user-agent", action="store_true", dest="random_user_agent",
        help="use a random user agent", default=False)
    parser.add_option(
        "--db", "--database-file", dest="db",
        help="custom database file")

    (options, args) = parser.parse_args(sys.argv)

    if options.urls is None:
        print("No URL(s) given!")
        parser.print_help()
        exit()

    print(options)
    wt = WebTech(options)
    wt.start()

if __name__ == "__main__":
    main()