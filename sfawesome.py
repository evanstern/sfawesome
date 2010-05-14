#! /usr/bin/env python

# vim: set expandtab ts=4 sw=4 filetype=python:

import sys, os
import getopt
from pyax.connection import Connection
from pyax.sobject.classfactory import ClassFactory
import clepy
import ConfigParser

class InvalidOwner(Exception):
    pass

class InvalidStatus(Exception):
    pass

class InvalidType(Exception):
    pass

class InvalidRelease(Exception):
    pass

class InvalidPriority(Exception):
    pass

class TooManyPrimeCommands(Exception):

    def __init__(self, prime_command, extra_prime_command):
        self.prime_command = prime_command
        self.extra_prime_command = extra_prime_command

    def __str__(self):
        return "%s and %s were given as arguments. Only use one." % (repr(self.value),repr(self.extra_prime_command))

class NoPrimeCommand(Exception):

    def __str__(self):
        return "There were no commands given."

class SfConfigParser(ConfigParser.RawConfigParser):
    def get(self, section, option):
        value = ConfigParser.RawConfigParser.get(self,section,option)
        if (value[0] == '[') and (value[-1] == ']'):
            return eval(value)
        else:
            return value

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    BOLDGREEN = '\033[1;32m'
    DGRAY = '\033[0;37m'
    UNDERLINE = '\033[0;04m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    def disable(self):
        self.HEADER = ''
        self.OKBLUE = ''
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''

# GLOBALS
UNAME = None
PWORD = None
owners_lst = None
types_lst = None
releases_lst = None
statuses_lst = None
priorities_lst = None
default_owner = None
default_type = None
default_status = None
default_priority = None
prime_command = ""

def get_case(sfdc, case_number):

    """
    Gets the case object.

    case_number -> the 8 digit long SF case number
    """

    query = """SELECT Id
               FROM Case
               WHERE CaseNumber='%s'""" % case_number

    try:
        query_results = sfdc.query(query)

        case = ClassFactory(sfdc,'Case').retrieve(query_results[0]['Id'])
    except Exception, ex:
        print_usage("Case %s does not exist" % case_number)

    return case


def cases_like(sfdc, search_string):

    """
    Uses a SQL 'LIKE' operator to search for the search_string in
    all the SF case subjects and returns any matches.

    search_string -> A SQL 'LIKE' compatible search string
    """

    query = """SELECT Id, Subject
               FROM Case
               WHERE Subject LIKE '%s'""" % ("%" + search_string + "%")

    try:
        cases = sfdc.query(query)
    except Exception, ex:
        print_usage(str(ex))

    for el in cases.values():
        case = ClassFactory(sfdc,'Case')
        yield case.retrieve(el['Id'])


def create_case(sfdc, case_dict):

    """
    Create a new case based on a case_dict input.
    """

    case = ClassFactory(sfdc,'Case')

    save_results = case.create(case_dict)

    new_case = case.retrieveSaveResult(save_results)

    new_case.update()
    new_case.refresh()

    return new_case


def update_case(sfdc, update_dict, case_number):

    case = get_case(sfdc, case_number)

    final_update_dict = {}

    if 'owner' in update_dict:

        owner = update_dict.get('owner')

#        if owner not in owners_lst:
#            raise InvalidOwner("%s is not a valid owner" % owner)

        final_update_dict['Developer__c'] = owner

    if 'status' in update_dict:

        status = update_dict.get('status')

#        if status not in statuses_lst:
#            raise InvalidStatus("%s is not a valid status" % status)

        final_update_dict['Status'] = status

    if 'type' in update_dict:

        type = update_dict.get('type')

#        if type not in types_lst:
#            raise InvalidType("%s is not a valid type" % type)

        final_update_dict['Type'] = type

    if 'release' in update_dict:

        release = update_dict.get('release')

#        if release not in releases_lst:
#            raise InvalidRelease("%s is not a valid release" % release)

        final_update_dict['Release__c'] = release

    if 'priority' in update_dict:

        priority = update_dict.get('priority')

#        if priority not in priorities_lst:
#            raise InvalidPriority("%s is not a valid priority" % priority)

        final_update_dict['Priority'] = priority


    for field in final_update_dict.keys():

        case[field] = final_update_dict[field]

    case.update()



def case_comments(sfdc, case_number, order=None, reverse=False, grep=None):

    """
    Returns the case comments for a specific SF case (if any)

    case_number -> The 8 digit SF case number
    order -> The field to order by (eg: 'CreatedDate')
    reverse -> True = Reverse the results
    grep -> Use the 'Like' SQL operator to perform a search and limit the
            results to the matches.
    """

    case = get_case(sfdc, case_number)

    order_by = ''
    if order is not None:

        if reverse == True:
            order = "%s DESC" % order

        order_by = """ORDER BY %s""" % order

    where = """WHERE ParentId='%s'""" % case['Id']

    if grep is not None:
        where += " AND CommentBody LIKE '%s'" % ("%" + grep + "%")

    query = """SELECT Id, CommentBody, CreatedDate
               FROM CaseComment
               %s
               %s""" % (where,order_by)

    try:
        raw = sfdc.query(query)
    except Exception, ex:
        print_usage(str(ex))

    for el in raw:
        yield (el['Id'],el['CreatedDate'],el['CommentBody'])


def get_ids(sfdc, release, status, reverse, order=None, owner_list=None,grep=None):

    """
    Returns a tuple with the case number, subject, created date, developer,
    and status of all issues in SF associated with a specific release.  You
    can pass optional flags to grep through the subject of the cases to narrow
    the list.

    release -> The release to look through
    order -> Which column to order the results on
    owner_list -> A comma separated list of owners to include in the results.
                  by default all owners are included
    grep -> A SQL 'Like' compatible search string to be used on the subject
            to limit results.
    """

    order_by = ''
    if order is not None:
        if reverse == True:
            order = "%s DESC" % order
        order_by = """ORDER BY %s""" % order

    where_construct = ""

    if release is not None:
        where_construct += """ release__c in ('%s') """ % '\',\''.join(release)

    if status is not None:
        if where_construct != "":
            where_construct += "AND "
        where_construct += """ Status in ('%s') """ % '\',\''.join(status)

    if owner_list is not None:
        owner_in = "Developer__c in ('%s')" % '\',\''.join(owner_list)
        if where_construct != "":
            where_construct += "AND "
        where_construct += """%s""" % owner_in

    if grep is not None:
        if where_construct != "":
            where_construct += "AND "
        where_construct += """Subject LIKE '%s'""" % ("%" + grep + "%")

    where = ""
    if where_construct != "":
        where = "WHERE %s" % where_construct

    query = """SELECT Id, CaseNumber, Subject, CreatedDate, Developer__c, Status, Release__c
               FROM Case
               %s
               %s""" % (where,order_by)

    try:
        raw = sfdc.query(query)
    except Exception, ex:
        print_usage(str(ex))

    info_list = []
    for el in raw:
        yield (el['CaseNumber'],el['Subject'],el['CreatedDate'],el['Developer__c'],el['Status'],el['Release__c'])


def _print_ids(sfdc,release,status,reverse,order=None,owner_list=None,grep=None):

    """
    Prints the ids associated with the get_ids method call for these params.

    See: get_ids.
    """

    print_me = ""
    for el in get_ids(sfdc,release,status,reverse,order,owner_list,grep):

        subject = el[1]
        if (el[1] is not None) and (len(el[1]) > 40):
                subject = el[1]

        print_me += "%s%s%s %-8s %-10s %-20s%s%-25s%s   %s\n\n" % (bcolors.BOLDGREEN,el[0],bcolors.ENDC,
                                                 el[3],
                                                 el[5],
                                                 el[4],
                                                 bcolors.UNDERLINE,el[2],bcolors.ENDC,
                                                 subject)
    clepy.send_through_pager(print_me,clepy.figure_out_pager())


def get_details(sfdc, case_number):

    case = get_case(sfdc, case_number)

    status = case['Status']
    subject = case['Subject']
    created_date = case['CreatedDate']
    description = case['Description']
    developer = case['Developer__c']

    message = """
%s -- Created On: %s -- Status: %s  Owner: %s

%s
%s
""" % (case_number, created_date, status, developer, subject, description)

    print message


def add_note(sfdc, note, case_number):

    case = get_case(sfdc,case_number)

    # Get the username from the user's home directory and capitalize
    # the first letter of the name.
    # This is because the 'uname' method can be wrong if you are
    # telnetting into the server.
    name =  os.environ.get("HOME").split('/')[-1]
    name = name[0].upper() + name[1:]

    case_comment = ClassFactory(sfdc,'CaseComment')

    note += """
-- %s
""" % name

    comment_dict = {"CommentBody":note,
                    "ParentId":case['Id'],
                    "IsPublished":True}

    case_comment.create(comment_dict)


def print_usage(message=None):

    if message is not None:
        print message

    print """
    Usage: python test.py [Options] [CaseNumber]
    Options:    --add-note=<Note>
                --get-ids=<Release> [--order-by=<Column>] [--reverse] [--owner=<List>]
                --create=<Subject> [--release=<release>] [--owner=<owner>] [--status=<status>] [--priority=<priority>]
                --get-details <CaseNumber>
                --get-comments <Case Number>
                --grep=<Regex>
                -h,--help
"""
    sys.exit(0)
    return


def parse_config():

    config = ConfigParser.RawConfigParser()
    config.read(os.environ.get('HOME') + '/.sfawesome')

    UNAME = config.get('salesforce','username')
    PWORD = config.get('salesforce','password') + config.get('salesforce','token')

    global owners_lst

    owners_lst = config.get('salesforce','owners')
    types_lst = config.get('salesforce','types')
    releases_lst = config.get('salesforce','releases')
    statuses_lst = config.get('salesforce','statuses')
    priorities_lst = config.get('salesforce','priorities')

    try:
        default_owner = config.get('salesforce','default-owner')
    except Exception, ex:
        pass

    try:
        default_type = config.get('salesforce','default-type')
    except Exception, ex:
        pass

    try:
        default_status = config.get('salesforce','default-status')
    except Exception, ex:
        pass

    try:
        default_priority = config.get('salesforce','default-priority')
    except Exception, ex:
        pass

    return Connection.connect(UNAME,PWORD)


def add_prime_command(command):

    if prime_command != "":
        raise TooManyPrimeCommands(prime_command, command)

    return command

def build_command_dict(opts, case_number=None):

    command_dict = {}

    prime_command=""

    for o, a in opts:

        if o == '--add-note':
            prime_command = (add_prime_command('add-note') if prime_command == "" else prime_command)
            command_dict['add-note'] = (a,case_number)

        elif o == '--case-number':
            print "Working with case number: %s" % a

        elif o == '--get-ids':
            prime_command = (add_prime_command('get-ids') if prime_command == "" else prime_command)
            command_dict['get-ids'] = True

        elif o == '--get-details':
            prime_command = (add_prime_command('get-details') if prime_command == "" else prime_command)
            command_dict['get-details'] = True

        elif o == '--get-comments':
            prime_command = (add_prime_command('get-comments') if prime_command == "" else prime_command)
            command_dict['get-comments'] = a

        elif o == '--create':
            prime_command = (add_prime_command('create') if prime_command == "" else prime_command)
            command_dict['create'] = a

        elif o == '--update-case':
            prime_command = (add_prime_command('update-case') if prime_command == "" else prime_command)
            command_dict['update-case'] = case_number

        elif o == '--grep':
            command_dict['grep'] = a

        elif o == '--order-by':
            command_dict['order-by'] = a

        elif o == '--reverse':
            command_dict['reverse'] = True

        elif o == '--owner':
            owner_list = a.split(',')
            command_dict['owner'] = owner_list

        elif o == '--release':
            command_dict['release'] = a

        elif o == '--description':
            command_dict['description'] = a

        elif o == '--status':
            command_dict['status'] = a

        elif o == '--priority':
            command_dict['priority'] = a

        elif o == '--type':
            command_dict['type'] = a

    return prime_command, command_dict


def main():

    long_opt_list = ['add-note=',
                     'case-number=',
                     'help',
                     'get-ids',
                     'get-details',
                     'get-comments',
                     'order-by=',
                     'owner=',
                     'reverse',
                     'grep=',
                     'create=',
                     'release=',
                     'description=',
                     'status=',
                     'priority=',
                     'type=',
                     'update-case']


    opt_list = 'h'

    try:
        opts,args = getopt.getopt(sys.argv[1:], opt_list,long_opt_list)
    except Exception, ex:
        print_usage(str(ex))

    case_number = None
    if len(args) != 0:
        case_number = args[0]

    # If the -h or --help flag was given, print usage and exit
    for o, a in opts:
        if o in ('-h','--help'):
            print_usage()

    # Parse the config and get the connection object
    sfdc = parse_config()

    # Build a command dictionary out of the options passed in
    prime_command, command_dict = build_command_dict(opts,case_number)

    if not prime_command:
        prime_command = 'get-ids'

    command_keys = command_dict.keys()
    if prime_command == 'update-case':

        update_dict = {}

        if 'status' in command_dict:
            update_dict['status'] = command_dict.get('status')

        if 'owner' in command_dict:
            update_dict['owner'] = command_dict.get('owner')[0]

        if 'release' in command_dict:
            update_dict['release'] = command_dict.get('release')

        if 'type' in command_dict:
            update_dict['type'] = command_dict.get('type')

        if 'priority' in command_dict:
            update_dict['priority'] = command_dict.get('priority')

        try:
            update_case(sfdc, update_dict, command_dict.get('update-case'))
            print "Case %s Updated" % case_number
        except Exception, ex:
            print_usage(str(ex))

    elif prime_command == 'add-note':

        note,sf_case_num = command_dict.get('add-note')

        add_note(sfdc,note,sf_case_num)

    elif prime_command == 'get-ids':
        order = command_dict.get('order-by',None)
        reverse = command_dict.get('reverse',False)
        owner_list = command_dict.get('owner',None)
        grep = command_dict.get('grep',None)
        release_list = command_dict.get('release',None)
        status_list = command_dict.get('status',None)

        if release_list:
            release_list = release_list.split(',')

        if status_list:
            status_list = status_list.split(',')

        if order in ('Developer','developer','dev','Dev','owner','Owner','Developer__c'):
            order = 'Developer__c'

        elif order in ('Date','date','Created','created','CreatedDate'):
            order = 'CreatedDate'

        elif order in ('subject','Subject'):
            order = 'Subject'

        elif order in ('Release','release','Rel','rel'):
            order = 'Release__c'

        _print_ids(sfdc,release_list,status_list,reverse,order,owner_list,grep)

    elif prime_command == 'get-comments':

        order = command_dict.get('order-by',None)
        reverse = command_dict.get('reverse',False)
        grep = command_dict.get('grep',None)

        if order in ('Date','date','Created','created','CreatedDate'):
            order = 'CreatedDate'

        print_me = ""
        for el in case_comments(sfdc,case_number,order,reverse,grep):
            print_me += """
%s%s%s : %s
%s
""" % (bcolors.OKGREEN,el[0],bcolors.ENDC,el[1],el[2])
        clepy.send_through_pager(print_me,clepy.figure_out_pager())

    elif prime_command == 'create':

        subject = command_dict.get('create')
        owner = command_dict.get('owner')
        release = command_dict.get('release')
        description = command_dict.get('description')
        status = command_dict.get('status')
        priority = command_dict.get('priority')
        type = command_dict.get('type')

        case_dict = {}

        if owner:
            owner_str = owner[0]
#            if owner_str not in owners_lst:
#                print_usage("%s is not a valid owner" % owner_str)

            case_dict['Developer__c'] = owner_str

#        if type:
#            if type not in types_lst:
#                print_usage("%s is not a valid case type" % type)

            case_dict['Type'] = type

        if release:
            case_dict['Release__c'] = release

        if description:
            case_dict['Description'] = description

        if not status:
            status = 'New'

        if not priority:
            priority = 'Low'

        case_dict['Subject'] = subject
        case_dict['Origin'] = 'Web'
        case_dict['Priority'] = priority
        case_dict['Status'] = status

        case = create_case(sfdc, case_dict)

        print "%s created" % case['CaseNumber']

    elif prime_command == 'get-details':

        get_details(sfdc,case_number)

    else:

        raise NoPrimeCommand()


if __name__ == '__main__':
    main()
