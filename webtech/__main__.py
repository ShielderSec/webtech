#!/usr/bin/env python
import sys
from optparse import OptionParser

from .webtech import WebTech


def split_on_comma(option, opt_str, value, parser):
    setattr(parser.values, option.dest, value.split(','))


def main():
    """
    Main function when running from command line.
    """
    parser = OptionParser(prog="webtech")
    parser.add_option(
        "-u", "--urls", dest="urls",
        help="url(s) to scan", type="string", action="callback", callback=split_on_comma)
    parser.add_option(
        "--ul", "--urls-file", dest="urls_file",
        help="url(s) list file to scan", type="string")
    parser.add_option(
        "--ua", "--user-agent", dest="user_agent",
        help="use this user agent")
    parser.add_option(
        "--rua", "--random-user-agent", action="store_true", dest="use_random_user_agent",
        help="use a random user agent", default=False)
    parser.add_option(
        "--db", "--database-file", dest="db_file",
        help="custom database file")
    parser.add_option(
        "--oj", "--json", action="store_true", dest="output_json",
        help="output json-encoded report", default=False)
    parser.add_option(
        "--og", "--grep", action="store_true", dest="output_grep",
        help="output grepable report", default=False)

    (options, args) = parser.parse_args(sys.argv)

    if options.urls is None and options.urls_file is None:
        print("No URL(s) given!")
        parser.print_help()
        exit()

    wt = WebTech(options)
    wt.start()


if __name__ == "__main__":
    main()
