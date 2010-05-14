#! /usr/bin/env python
# vim: set expandtab ts=4 sw=4 filetype=python:

#############################################################################
#
#   sfawesome - A command line interface into salesforce.
#
#   Evan Stern @ 05/14/2010
#
#############################################################################

import os, sys, getopt
import ConfigParser
import clepy

from pyax.connection import Connection
from pyax.sobject.classfactory import ClassFactory


# Exit Codes
ST_SUCCESS = 0
ST_ERROR = 1

def main():

    print config.get('salesforce','username')

    pass


def _print_usage(message=None, status=ST_SUCCESS):

    """
    Prints the usage text and then exits.
    """

    if message is not None:
        print message

    print """
    Usage: %s [Options] [CaseNumber]
    """ % script_basename

    sys.exit(status)


def _parse_config(config_file):

    global config

    config = ConfigParser.RawConfigParser()
    config.read(config_file)

    UNAME = config.get('salesforce', 'username')
    PWORD = config.get('salesforce', 'password') + config.get('salesforce', 'token')


if __name__ == '__main__':

    script_basename = sys.argv[0].split('/')[-1]

    # Make sure the config file exists
    try:
        config_file = os.environ.get('HOME') + '/.sfawesome'
        os.stat(config_file)
    except Exception, ex:
        _print_usage(str(ex), ST_ERROR)

    long_opt_list = [ 'help',

                      'create',
                      'update',
                      'add-note',
                      'get-notes',
                      'list-cases',
                      'get-case',

                      'subject=',
                      'owner=',
                      'release=',
                      'description=',
                      'status=',
                      'priority=',
                      'type=',
                      'case-number='
                      'order-by='
                      'reverse'
                      'grep=' ]

    short_opts = 'h'

    try:
        opts, args = getopt.getopt(sys.argv[1:], short_opts, long_opt_list)
    except Exception, ex:
        _print_usage(str(ex), ST_ERROR)

    for o, a in opts:
        if o in ('-h','--help'):
            _print_usage()

    try:
        _parse_config(config_file)
    except Exception, ex:
        _print_usage(str(ex), ST_ERROR)

    # Lets go!
    main()
